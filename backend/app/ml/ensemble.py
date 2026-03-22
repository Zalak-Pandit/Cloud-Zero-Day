"""
Ensemble Threat Scorer
Combines Isolation Forest + LSTM + GNN scores with weighted voting.
Classifies threats by type and severity.
"""
import numpy as np
import os
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from app.ml.isolation_forest import NetworkAnomalyDetector, LogAnomalyDetector, APIAnomalyDetector
from app.ml.lstm_model import SequenceAnomalyDetector
from app.ml.graph_model import GraphThreatDetector
from app.models.threat import ThreatCreate, ThreatType, ThreatSeverity
from app.config import settings

logger = logging.getLogger(__name__)

# Model weights — tuned from validation experiments
WEIGHTS = {
    "isolation_forest": 0.35,
    "lstm": 0.40,
    "graph": 0.25,
}


def classify_severity(score: float) -> ThreatSeverity:
    if score >= 0.90:
        return ThreatSeverity.CRITICAL
    elif score >= 0.75:
        return ThreatSeverity.HIGH
    elif score >= 0.55:
        return ThreatSeverity.MEDIUM
    return ThreatSeverity.LOW


def infer_threat_type(event: Dict[str, Any], scores: Dict[str, float]) -> ThreatType:
    """Heuristic threat-type inference from event features and model scores."""
    dest_port = event.get("dest_port", 0)
    bytes_sent = event.get("bytes_sent", 0)
    syscall = event.get("syscall", "")
    status = event.get("status_code", 200)
    message = event.get("message", "").lower()

    # Graph score high → lateral movement
    if scores.get("graph", 0) > 0.80:
        return ThreatType.LATERAL_MOVEMENT

    # Root/admin with unusual syscall
    if event.get("user") in ("root", "admin") and syscall:
        return ThreatType.PRIVILEGE_ESCALATION

    # Large outbound transfer
    if bytes_sent > 50_000_000:
        return ThreatType.DATA_EXFILTRATION

    # API with injection-like params
    params = str(event.get("params", ""))
    injection_chars = sum(params.count(c) for c in ["'", '"', ";", "--", "UNION", "SELECT", "<script", "$("])
    if injection_chars > 2:
        return ThreatType.COMMAND_INJECTION

    # Unusual API pattern
    if status >= 400 and scores.get("isolation_forest", 0) > 0.7:
        return ThreatType.UNUSUAL_API_PATTERN

    # LSTM score high + isolation forest → novel behavior
    if scores.get("lstm", 0) > 0.85:
        return ThreatType.ZERO_DAY_EXPLOIT

    # Memory/process anomaly keywords in logs
    if any(k in message for k in ["segfault", "heap", "stack overflow", "buffer", "corruption"]):
        return ThreatType.MEMORY_CORRUPTION

    return ThreatType.ANOMALOUS_BEHAVIOR


def build_description(event: Dict[str, Any], threat_type: ThreatType, score: float) -> str:
    src = event.get("source_ip", "unknown")
    target = event.get("dest_ip", event.get("host", "unknown"))
    return (
        f"{threat_type.value.replace('_', ' ').title()} detected from {src} "
        f"targeting {target}. Ensemble confidence: {score:.2f}."
    )


class EnsembleThreatScorer:
    def __init__(self):
        self.net_if = NetworkAnomalyDetector()
        self.log_if = LogAnomalyDetector()
        self.api_if = APIAnomalyDetector()
        self.lstm = SequenceAnomalyDetector()
        self.graph = GraphThreatDetector()

    def load_models(self, model_dir: str):
        """Load pre-trained models from disk. Silently skips missing files."""
        loaders = [
            (self.net_if, "net_if.joblib", "load"),
            (self.log_if, "log_if.joblib", "load"),
            (self.api_if, "api_if.joblib", "load"),
            (self.lstm, "lstm.pt", "load"),
            (self.graph, "graph.joblib", "load"),
        ]
        for model, filename, method in loaders:
            path = os.path.join(model_dir, filename)
            if os.path.exists(path):
                try:
                    getattr(model, method)(path)
                    logger.info(f"Loaded {filename}")
                except Exception as e:
                    logger.warning(f"Could not load {filename}: {e}")
            else:
                logger.warning(f"Model file not found: {path} — using untrained model")

    def save_models(self, model_dir: str):
        os.makedirs(model_dir, exist_ok=True)
        self.net_if.save(os.path.join(model_dir, "net_if.joblib"))
        self.log_if.save(os.path.join(model_dir, "log_if.joblib"))
        self.api_if.save(os.path.join(model_dir, "api_if.joblib"))
        self.lstm.save(os.path.join(model_dir, "lstm.pt"))
        self.graph.save(os.path.join(model_dir, "graph.joblib"))

    def score_event(self, event: Dict[str, Any]) -> Tuple[float, Dict[str, float]]:
        """
        Compute ensemble threat score for an incoming event.
        Returns (final_score, per-model scores dict).
        """
        event_type = event.get("_type", "network")   # injected by kafka consumer
        host = event.get("source_ip", event.get("host", "unknown"))

        # Per-model scores
        if event_type == "network":
            if_score = self.net_if.score(event)
        elif event_type == "log":
            if_score = self.log_if.score(event)
        else:
            if_score = self.api_if.score(event)

        self.lstm.push_event(host, event)
        lstm_score = self.lstm.score(host)
        graph_score = self.graph.score(event)

        # Update graph adjacency (online learning)
        src = event.get("source_ip", "")
        dst = event.get("dest_ip", "")
        if src and dst:
            self.graph.record(src, dst)

        per_model = {
            "isolation_forest": if_score,
            "lstm": lstm_score,
            "graph": graph_score,
        }

        # Weighted ensemble
        final = (
            WEIGHTS["isolation_forest"] * if_score
            + WEIGHTS["lstm"] * lstm_score
            + WEIGHTS["graph"] * graph_score
        )

        return float(np.clip(final, 0, 1)), per_model

    def evaluate(self, event: Dict[str, Any]) -> Optional[ThreatCreate]:
        """
        Full evaluation pipeline. Returns ThreatCreate if score >= threshold, else None.
        """
        score, model_scores = self.score_event(event)

        if score < settings.ANOMALY_THRESHOLD:
            return None

        threat_type = infer_threat_type(event, model_scores)
        severity = classify_severity(score)

        indicators = []
        if model_scores["isolation_forest"] > 0.7:
            indicators.append("statistical_outlier")
        if model_scores["lstm"] > 0.7:
            indicators.append("behavioral_deviation")
        if model_scores["graph"] > 0.7:
            indicators.append("unusual_network_path")

        return ThreatCreate(
            threat_type=threat_type,
            severity=severity,
            confidence_score=score,
            description=build_description(event, threat_type, score),
            source_ip=event.get("source_ip"),
            target_resource=event.get("dest_ip", event.get("host")),
            indicators=indicators,
            raw_events=[event],
            model_scores=model_scores,
            region=event.get("region", "us-east-1"),
        )