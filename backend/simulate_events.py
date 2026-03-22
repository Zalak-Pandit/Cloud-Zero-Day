"""
simulate_events.py — Pumps synthetic cloud events into Kafka topics.
Run this alongside the backend to demo the live detection pipeline:

    python simulate_events.py --rate 5 --anomaly-rate 0.08
"""
import argparse
import json
import random
import time
import uuid
from datetime import datetime
import numpy as np

from kafka import KafkaProducer

NORMAL_IPS = [f"10.0.{r}.{h}" for r in range(0, 5) for h in range(1, 20)]
EXTERNAL_IPS = [f"203.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}" for _ in range(20)]
COMMON_PORTS = [80, 443, 8080, 8443, 3306, 5432, 6379, 22]


def make_normal_network():
    src = random.choice(NORMAL_IPS)
    dst = random.choice(NORMAL_IPS)
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "srcAddr": src, "dstAddr": dst,
        "srcPort": random.randint(1024, 65535),
        "dstPort": random.choice(COMMON_PORTS),
        "protocol": "TCP",
        "bytes": int(np.random.lognormal(10, 2)),
        "bytes_recv": int(np.random.lognormal(12, 2)),
        "duration_ms": float(np.random.exponential(200)),
        "region": "us-east-1",
    }


def make_anomalous_network():
    """Simulate lateral movement or data exfiltration."""
    attack_type = random.choice(["lateral", "exfil", "portscan"])
    if attack_type == "lateral":
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "srcAddr": random.choice(NORMAL_IPS),
            "dstAddr": f"10.0.{random.randint(10, 20)}.{random.randint(1, 254)}",  # new subnet
            "srcPort": random.randint(1024, 65535),
            "dstPort": random.choice([22, 3389, 445, 135]),  # admin ports
            "protocol": "TCP", "bytes": 5000, "bytes_recv": 1000,
            "duration_ms": 5000, "region": "us-east-1",
        }
    elif attack_type == "exfil":
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "srcAddr": random.choice(NORMAL_IPS),
            "dstAddr": random.choice(EXTERNAL_IPS),
            "srcPort": random.randint(1024, 65535),
            "dstPort": 443,
            "protocol": "TCP",
            "bytes": int(np.random.lognormal(18, 1)),   # huge outbound
            "bytes_recv": 1000, "duration_ms": 120000, "region": "us-east-1",
        }
    else:  # portscan
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "srcAddr": random.choice(EXTERNAL_IPS),
            "dstAddr": random.choice(NORMAL_IPS),
            "srcPort": random.randint(1024, 65535),
            "dstPort": random.randint(1, 1024),
            "protocol": "TCP", "bytes": 64, "bytes_recv": 0,
            "duration_ms": 10, "region": "us-east-1",
        }


def make_normal_log():
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "hostname": f"web-{random.randint(1, 20)}",
        "service": random.choice(["nginx", "app", "auth"]),
        "level": "INFO",
        "message": random.choice(["Request processed", "Cache hit", "Session created"]),
        "user": random.choice(["app", "worker", "deploy"]),
    }


def make_anomalous_log():
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "hostname": f"web-{random.randint(1, 20)}",
        "service": "kernel",
        "level": "CRITICAL",
        "message": random.choice([
            "segfault at address 0x0 - heap corruption detected",
            "buffer overflow in process 1337",
            "unauthorized sudo attempt by uid=1001",
        ]),
        "user": "root",
        "syscall": random.choice(["execve", "ptrace", "mmap"]),
        "source_ip": random.choice(EXTERNAL_IPS),
    }


def make_normal_api():
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "path": random.choice(["/api/users", "/api/products", "/health"]),
        "method": "GET",
        "status": 200,
        "latency": float(np.random.lognormal(4, 1)),
        "sourceIPAddress": random.choice(EXTERNAL_IPS),
        "userAgent": "Mozilla/5.0",
        "requestContentLength": random.randint(0, 500),
        "responseContentLength": random.randint(200, 5000),
    }


def make_anomalous_api():
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "path": "/api/users",
        "method": "GET",
        "status": 500,
        "latency": float(np.random.lognormal(9, 1)),   # extreme latency
        "sourceIPAddress": random.choice(EXTERNAL_IPS),
        "userAgent": "sqlmap/1.7",
        "requestContentLength": 8000,
        "responseContentLength": 0,
        "requestParameters": {
            "q": "' OR 1=1 UNION SELECT * FROM users --",
            "id": "$(cat /etc/passwd)",
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap", default="localhost:9092")
    parser.add_argument("--rate", type=float, default=5.0, help="Events per second")
    parser.add_argument("--anomaly-rate", type=float, default=0.05)
    args = parser.parse_args()

    producer = KafkaProducer(
        bootstrap_servers=args.bootstrap,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

    TOPIC_NETWORK = "cloud-logs"      # reuse same topic names as config
    TOPIC_LOG     = "cloud-logs"
    TOPIC_API     = "api-events"

    print(f"Sending events at {args.rate}/s  anomaly_rate={args.anomaly_rate:.0%}")
    interval = 1.0 / args.rate

    while True:
        is_anomaly = random.random() < args.anomaly_rate
        event_type = random.choices(["network", "log", "api"], weights=[0.5, 0.3, 0.2])[0]

        if event_type == "network":
            event = make_anomalous_network() if is_anomaly else make_normal_network()
            producer.send("network-events", event)
        elif event_type == "log":
            event = make_anomalous_log() if is_anomaly else make_normal_log()
            producer.send(TOPIC_LOG, event)
        else:
            event = make_anomalous_api() if is_anomaly else make_normal_api()
            producer.send(TOPIC_API, event)

        if is_anomaly:
            print(f"  [ANOMALY] {event_type}: {json.dumps(event)[:80]}...")

        time.sleep(interval)


if __name__ == "__main__":
    main()