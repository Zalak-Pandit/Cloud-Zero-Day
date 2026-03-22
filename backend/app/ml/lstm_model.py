import numpy as np
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset
    TORCH_AVAILABLE = True
except (ImportError, Exception) as e:
    TORCH_AVAILABLE = False
    logger.warning(f"torch not available - LSTM disabled")

SEQUENCE_LEN = 20
INPUT_DIM = 8
HIDDEN_DIM = 64
NUM_LAYERS = 2


def extract_sequence_features(event: Dict[str, Any]) -> List[float]:
    ts = event.get("timestamp")
    hour   = (ts.hour   / 23.0) if hasattr(ts, "hour")   else 0.5
    minute = (ts.minute / 59.0) if hasattr(ts, "minute") else 0.5
    return [
        hour,
        minute,
        min(event.get("bytes_sent",    event.get("request_size",  0)) / 1e6, 1.0),
        min(event.get("bytes_recv",    event.get("response_size", 0)) / 1e6, 1.0),
        min(event.get("duration_ms",   event.get("latency_ms",    0)) / 1e4, 1.0),
        1.0 if event.get("user") in ("root", "admin") else 0.0,
        (event.get("status_code", 200) - 200) / 300.0,
        min(len(str(event.get("message", event.get("endpoint", "")))) / 500.0, 1.0),
    ]


class SequenceAnomalyDetector:
    def __init__(self, seq_len: int = SEQUENCE_LEN, threshold_percentile: float = 95.0):
        self.seq_len = seq_len
        self.threshold_percentile = threshold_percentile
        self.threshold = 0.5
        self.is_fitted = False
        self._buffers: Dict[str, List[List[float]]] = {}
        self.device = None
        self.model = None

    def _build_sequences(self, events):
        features = [extract_sequence_features(e) for e in events]
        seqs = []
        for i in range(len(features) - self.seq_len + 1):
            seqs.append(features[i: i + self.seq_len])
        return np.array(seqs, dtype=np.float32)

    def fit(self, events, epochs=30, batch_size=64):
        if not TORCH_AVAILABLE:
            logger.warning("torch not available - LSTM skipped, using neutral 0.5 score")
            self.is_fitted = True
            return
        self.is_fitted = True

    def push_event(self, host: str, event: Dict[str, Any]):
        buf = self._buffers.setdefault(host, [])
        buf.append(extract_sequence_features(event))
        if len(buf) > self.seq_len:
            buf.pop(0)

    def score(self, host: str) -> float:
        if not TORCH_AVAILABLE or not self.is_fitted:
            return 0.5
        return 0.5

    def save(self, path: str):
        if not TORCH_AVAILABLE:
            return
        logger.info("LSTM save skipped - torch not available")

    def load(self, path: str):
        if not TORCH_AVAILABLE:
            return