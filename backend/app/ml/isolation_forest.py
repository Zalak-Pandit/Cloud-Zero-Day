"""
Isolation Forest — detects anomalous events by isolating outliers
in the feature space of network/log/API behavior.
"""
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib
import os
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Feature extractors
NETWORK_FEATURES = [
    "bytes_sent", "bytes_recv", "duration_ms", "dest_port",
    "bytes_ratio", "packet_rate", "port_category"
]
LOG_FEATURES = [
    "hour_of_day", "is_privileged_user", "syscall_frequency",
    "error_rate", "unique_commands"
]
API_FEATURES = [
    "requests_per_min", "error_rate", "avg_latency",
    "unique_endpoints", "param_entropy", "hour_of_day"
]


def port_category(port: int) -> int:
    """Encode port into category: 0=well-known, 1=registered, 2=dynamic."""
    if port < 1024:
        return 0
    elif port < 49152:
        return 1
    return 2


class NetworkAnomalyDetector:
    def __init__(self, contamination: float = 0.05):
        self.model = IsolationForest(
            n_estimators=200,
            contamination=contamination,
            max_samples="auto",
            random_state=42,
            n_jobs=-1
        )
        self.scaler = StandardScaler()
        self.is_fitted = False

    def extract_features(self, event: Dict[str, Any]) -> np.ndarray:
        bytes_sent = event.get("bytes_sent", 0)
        bytes_recv = event.get("bytes_recv", 0)
        duration = max(event.get("duration_ms", 1), 1)
        dest_port = event.get("dest_port", 0)

        return np.array([
            np.log1p(bytes_sent),
            np.log1p(bytes_recv),
            np.log1p(duration),
            dest_port,
            bytes_sent / max(bytes_recv, 1),            # ratio
            (bytes_sent + bytes_recv) / duration,       # packet rate
            port_category(dest_port)
        ])

    def fit(self, events: list):
        features = np.array([self.extract_features(e) for e in events])
        features_scaled = self.scaler.fit_transform(features)
        self.model.fit(features_scaled)
        self.is_fitted = True
        logger.info(f"NetworkAnomalyDetector fitted on {len(events)} events")

    def score(self, event: Dict[str, Any]) -> float:
        """Return anomaly score 0-1. Higher = more anomalous."""
        if not self.is_fitted:
            return 0.5
        features = self.extract_features(event).reshape(1, -1)
        features_scaled = self.scaler.transform(features)
        # IsolationForest: score_samples returns negative anomaly scores
        raw = self.model.score_samples(features_scaled)[0]
        # Normalise to 0-1 where 1 = most anomalous
        return float(np.clip(1 - (raw + 0.5), 0, 1))

    def save(self, path: str):
        joblib.dump({"model": self.model, "scaler": self.scaler}, path)

    def load(self, path: str):
        data = joblib.load(path)
        self.model = data["model"]
        self.scaler = data["scaler"]
        self.is_fitted = True


class LogAnomalyDetector:
    """Detects anomalous system log patterns — unusual syscalls, privilege use, etc."""

    def __init__(self, contamination: float = 0.03):
        self.model = IsolationForest(
            n_estimators=150,
            contamination=contamination,
            random_state=42,
            n_jobs=-1
        )
        self.scaler = StandardScaler()
        self.is_fitted = False
        self._baseline: Dict[str, float] = {}

    def extract_features(self, event: Dict[str, Any]) -> np.ndarray:
        import hashlib

        ts = event.get("timestamp")
        hour = ts.hour if hasattr(ts, "hour") else 12
        user = event.get("user", "")
        syscall = event.get("syscall", "")
        message = event.get("message", "")

        privileged = 1.0 if user in ("root", "admin", "sudo") else 0.0
        # Entropy of message as proxy for unusual content
        msg_hash = hashlib.md5(message.encode()).hexdigest()
        entropy = sum(int(c, 16) for c in msg_hash) / (len(msg_hash) * 15)

        return np.array([
            hour,
            privileged,
            len(syscall) if syscall else 0,
            entropy,
            len(message) if message else 0,
        ])

    def fit(self, events: list):
        features = np.array([self.extract_features(e) for e in events])
        features_scaled = self.scaler.fit_transform(features)
        self.model.fit(features_scaled)
        self.is_fitted = True

    def score(self, event: Dict[str, Any]) -> float:
        if not self.is_fitted:
            return 0.5
        features = self.extract_features(event).reshape(1, -1)
        features_scaled = self.scaler.transform(features)
        raw = self.model.score_samples(features_scaled)[0]
        return float(np.clip(1 - (raw + 0.5), 0, 1))

    def save(self, path: str):
        joblib.dump({"model": self.model, "scaler": self.scaler}, path)

    def load(self, path: str):
        data = joblib.load(path)
        self.model = data["model"]
        self.scaler = data["scaler"]
        self.is_fitted = True


class APIAnomalyDetector:
    """Detects anomalous API usage patterns — rate anomalies, unusual endpoints."""

    def __init__(self, contamination: float = 0.04):
        self.model = IsolationForest(
            n_estimators=100,
            contamination=contamination,
            random_state=42,
        )
        self.scaler = StandardScaler()
        self.is_fitted = False

    def extract_features(self, event: Dict[str, Any]) -> np.ndarray:
        import math
        ts = event.get("timestamp")
        hour = ts.hour if hasattr(ts, "hour") else 12

        # Entropy of request params as indicator of fuzzing/injection attempts
        params = str(event.get("params", {}))
        char_freq = {}
        for c in params:
            char_freq[c] = char_freq.get(c, 0) + 1
        total = len(params) or 1
        entropy = -sum((f / total) * math.log2(f / total) for f in char_freq.values()) if char_freq else 0

        return np.array([
            event.get("latency_ms", 0),
            event.get("status_code", 200),
            event.get("request_size", 0),
            event.get("response_size", 0),
            hour,
            entropy,
        ])

    def fit(self, events: list):
        features = np.array([self.extract_features(e) for e in events])
        features_scaled = self.scaler.fit_transform(features)
        self.model.fit(features_scaled)
        self.is_fitted = True

    def score(self, event: Dict[str, Any]) -> float:
        if not self.is_fitted:
            return 0.5
        features = self.extract_features(event).reshape(1, -1)
        features_scaled = self.scaler.transform(features)
        raw = self.model.score_samples(features_scaled)[0]
        return float(np.clip(1 - (raw + 0.5), 0, 1))

    def save(self, path: str):
        joblib.dump({"model": self.model, "scaler": self.scaler}, path)

    def load(self, path: str):
        data = joblib.load(path)
        self.model = data["model"]
        self.scaler = data["scaler"]
        self.is_fitted = True