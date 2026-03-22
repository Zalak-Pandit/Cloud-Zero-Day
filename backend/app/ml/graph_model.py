import numpy as np
import logging
from typing import Dict, Any, List, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)

try:
    from torch_geometric.nn import GCNConv
    PYGEOMETRIC_AVAILABLE = True
except (ImportError, Exception):
    PYGEOMETRIC_AVAILABLE = False


class AdjacencyAnomalyDetector:
    def __init__(self, decay: float = 0.99):
        self.decay = decay
        self.host_index: Dict[str, int] = {}
        self.adjacency: np.ndarray = np.zeros((256, 256), dtype=np.float32)
        self.connection_counts: Dict[Tuple[str, str], int] = defaultdict(int)
        self.is_fitted = False

    def _get_idx(self, host: str) -> int:
        if host not in self.host_index:
            idx = len(self.host_index) % 256
            self.host_index[host] = idx
        return self.host_index[host]

    def record(self, src: str, dst: str):
        i, j = self._get_idx(src), self._get_idx(dst)
        self.adjacency[i][j] = self.adjacency[i][j] * self.decay + 1.0
        self.connection_counts[(src, dst)] += 1

    def fit(self, events: List[Dict[str, Any]]):
        for e in events:
            src = e.get("source_ip", "")
            dst = e.get("dest_ip", "")
            if src and dst:
                self.record(src, dst)
        self.is_fitted = True

    def score_connection(self, src: str, dst: str) -> float:
        count = self.connection_counts.get((src, dst), 0)
        if count == 0:
            return 0.85
        return float(np.clip(1.0 - (np.log1p(count) / np.log1p(100)), 0, 1))

    def score(self, event: Dict[str, Any]) -> float:
        src = event.get("source_ip", "")
        dst = event.get("dest_ip", "")
        if not src or not dst:
            return 0.0
        return self.score_connection(src, dst)


class GraphThreatDetector:
    def __init__(self):
        self.detector = AdjacencyAnomalyDetector()
        self.is_fitted = False

    def fit(self, events: List[Dict[str, Any]]):
        self.detector.fit(events)
        self.is_fitted = True
        logger.info("GraphThreatDetector fitted")

    def score(self, event: Dict[str, Any]) -> float:
        if not self.is_fitted:
            return 0.5
        return self.detector.score(event)

    def record(self, src: str, dst: str):
        self.detector.record(src, dst)

    def save(self, path: str):
        import joblib
        joblib.dump(self.detector, path)

    def load(self, path: str):
        import joblib
        self.detector = joblib.load(path)
        self.is_fitted = True