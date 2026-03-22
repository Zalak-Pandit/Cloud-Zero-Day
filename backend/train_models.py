"""
train_models.py — Generate synthetic training data and fit all ML models.
Run this once before starting the backend:

    python train_models.py --output ./models --samples 5000
"""
import argparse
import os
import random
import numpy as np
from datetime import datetime, timedelta


def generate_synthetic_events(n: int = 5000):
    """Generate synthetic cloud events that represent 'normal' baseline behavior."""
    events = []
    base_time = datetime.utcnow()

    for i in range(n):
        ts = base_time - timedelta(seconds=i * 2)
        event_type = random.choices(["network", "log", "api"], weights=[0.5, 0.3, 0.2])[0]

        if event_type == "network":
            events.append({
                "_type": "network",
                "timestamp": ts,
                "source_ip": f"10.0.{random.randint(0, 10)}.{random.randint(1, 50)}",
                "dest_ip": f"10.0.{random.randint(0, 10)}.{random.randint(1, 50)}",
                "source_port": random.randint(1024, 65535),
                "dest_port": random.choice([80, 443, 8080, 8443, 3306, 5432]),
                "bytes_sent": int(np.random.lognormal(10, 2)),
                "bytes_recv": int(np.random.lognormal(12, 2)),
                "duration_ms": float(np.random.exponential(200)),
                "flags": [],
                "region": "us-east-1",
            })
        elif event_type == "log":
            events.append({
                "_type": "log",
                "timestamp": ts,
                "host": f"web-{random.randint(1, 20)}",
                "service": random.choice(["nginx", "app", "auth", "worker"]),
                "level": random.choices(["INFO", "WARN", "ERROR"], weights=[0.9, 0.08, 0.02])[0],
                "message": random.choice([
                    "Request processed", "User login", "Cache miss",
                    "DB query executed", "Session created",
                ]),
                "user": random.choice(["app", "worker", "deploy", None]),
                "syscall": None,
                "source_ip": f"10.0.{random.randint(0, 10)}.{random.randint(1, 50)}",
            })
        else:
            events.append({
                "_type": "api",
                "timestamp": ts,
                "endpoint": random.choice(["/api/users", "/api/products", "/api/orders", "/health"]),
                "method": random.choices(["GET", "POST", "PUT"], weights=[0.6, 0.3, 0.1])[0],
                "status_code": random.choices([200, 201, 400, 404, 500], weights=[0.85, 0.05, 0.05, 0.04, 0.01])[0],
                "latency_ms": float(np.random.lognormal(4, 1)),
                "source_ip": f"203.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}",
                "user_agent": "Mozilla/5.0",
                "request_size": random.randint(100, 2000),
                "response_size": random.randint(200, 50000),
                "params": {},
            })

    return events


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="./models")
    parser.add_argument("--samples", type=int, default=5000)
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)
    print(f"Generating {args.samples} synthetic training events...")
    events = generate_synthetic_events(args.samples)

    net_events = [e for e in events if e["_type"] == "network"]
    log_events = [e for e in events if e["_type"] == "log"]
    api_events = [e for e in events if e["_type"] == "api"]

    print(f"  Network: {len(net_events)}, Log: {len(log_events)}, API: {len(api_events)}")

    # ── Isolation Forest models ──────────────────────────────────────────────
    print("Training Isolation Forest (network)...")
    from app.ml.isolation_forest import NetworkAnomalyDetector, LogAnomalyDetector, APIAnomalyDetector
    net_det = NetworkAnomalyDetector()
    net_det.fit(net_events)
    net_det.save(os.path.join(args.output, "net_if.joblib"))

    print("Training Isolation Forest (log)...")
    log_det = LogAnomalyDetector()
    log_det.fit(log_events)
    log_det.save(os.path.join(args.output, "log_if.joblib"))

    print("Training Isolation Forest (API)...")
    api_det = APIAnomalyDetector()
    api_det.fit(api_events)
    api_det.save(os.path.join(args.output, "api_if.joblib"))

    # ── LSTM ────────────────────────────────────────────────────────────────
    print("Training LSTM autoencoder...")
    from app.ml.lstm_model import SequenceAnomalyDetector
    lstm = SequenceAnomalyDetector()
    lstm.fit(events, epochs=20)
    lstm.save(os.path.join(args.output, "lstm.pt"))

    # ── Graph ────────────────────────────────────────────────────────────────
    print("Fitting graph adjacency model...")
    from app.ml.graph_model import GraphThreatDetector
    graph = GraphThreatDetector()
    graph.fit(net_events)
    graph.save(os.path.join(args.output, "graph.joblib"))

    print(f"\n✅ All models saved to {args.output}/")
    print("   net_if.joblib  — Network Isolation Forest")
    print("   log_if.joblib  — Log Isolation Forest")
    print("   api_if.joblib  — API Isolation Forest")
    print("   lstm.pt        — LSTM Autoencoder")
    print("   graph.joblib   — Graph Adjacency Model")


if __name__ == "__main__":
    main()