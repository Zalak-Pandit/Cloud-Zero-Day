"""
Log parsers — normalize raw events from different sources
into unified dicts the ML models can consume.
"""
from datetime import datetime
from typing import Any, Dict


def _parse_ts(raw: Dict[str, Any]) -> datetime:
    ts = raw.get("timestamp", raw.get("time", raw.get("@timestamp")))
    if isinstance(ts, datetime):
        return ts
    if isinstance(ts, (int, float)):
        return datetime.utcfromtimestamp(ts)
    if isinstance(ts, str):
        for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(ts, fmt)
            except ValueError:
                continue
    return datetime.utcnow()


def parse_network_event(raw: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "timestamp": _parse_ts(raw),
        "source_ip": raw.get("srcAddr", raw.get("source_ip", "")),
        "dest_ip": raw.get("dstAddr", raw.get("dest_ip", "")),
        "source_port": int(raw.get("srcPort", raw.get("source_port", 0))),
        "dest_port": int(raw.get("dstPort", raw.get("dest_port", 0))),
        "protocol": raw.get("protocol", "TCP"),
        "bytes_sent": int(raw.get("bytes", raw.get("bytes_sent", 0))),
        "bytes_recv": int(raw.get("bytes_recv", 0)),
        "duration_ms": float(raw.get("end", 0)) - float(raw.get("start", 0)) or float(raw.get("duration_ms", 0)),
        "flags": raw.get("tcpFlags", raw.get("flags", [])),
        "region": raw.get("region", "us-east-1"),
        "vpc_id": raw.get("vpcId"),
    }


def parse_log_event(raw: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "timestamp": _parse_ts(raw),
        "host": raw.get("hostname", raw.get("host", "unknown")),
        "service": raw.get("service", raw.get("program", "unknown")),
        "level": raw.get("level", raw.get("severity", "INFO")),
        "message": raw.get("message", raw.get("msg", "")),
        "user": raw.get("user", raw.get("uid", raw.get("username"))),
        "pid": raw.get("pid"),
        "syscall": raw.get("syscall"),
        "source_ip": raw.get("source_ip", raw.get("remote_addr", "")),
        "extra": {k: v for k, v in raw.items() if k not in ("timestamp", "host", "message", "level")},
    }


def parse_api_event(raw: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "timestamp": _parse_ts(raw),
        "endpoint": raw.get("path", raw.get("endpoint", "/")),
        "method": raw.get("method", raw.get("httpMethod", "GET")),
        "status_code": int(raw.get("status", raw.get("status_code", 200))),
        "latency_ms": float(raw.get("latency", raw.get("latency_ms", raw.get("responseTime", 0)))),
        "source_ip": raw.get("sourceIPAddress", raw.get("source_ip", raw.get("remoteAddr", ""))),
        "user_agent": raw.get("userAgent", raw.get("user_agent", "")),
        "user_id": raw.get("userIdentity", {}).get("arn") or raw.get("user_id"),
        "request_size": int(raw.get("requestContentLength", raw.get("request_size", 0))),
        "response_size": int(raw.get("responseContentLength", raw.get("response_size", 0))),
        "params": raw.get("requestParameters", raw.get("params", {})),
    }