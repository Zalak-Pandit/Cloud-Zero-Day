"""
Threats API — CRUD endpoints for threats.
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
from datetime import datetime, timedelta
import uuid

from app.models.threat import (
    ThreatCreate, ThreatResponse, ThreatListResponse,
    ThreatStats, ThreatStatus, ThreatSeverity
)

router = APIRouter()

# In-memory store for hackathon demo (replace with DB in production)
_threats: List[dict] = []


async def persist_threat(threat: ThreatCreate) -> ThreatResponse:
    """Save a detected threat. Returns the full ThreatResponse."""
    now = datetime.utcnow()
    data = {
        **threat.model_dump(),
        "id": str(uuid.uuid4()),
        "status": ThreatStatus.OPEN,
        "created_at": now,
        "updated_at": now,
        "auto_contained": False,
        "alert_sent": False,
    }
    _threats.insert(0, data)
    # Keep last 10,000 threats in memory
    if len(_threats) > 10_000:
        _threats.pop()
    return ThreatResponse(**data)


@router.get("", response_model=ThreatListResponse)
async def list_threats(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    severity: Optional[ThreatSeverity] = None,
    status: Optional[ThreatStatus] = None,
    threat_type: Optional[str] = None,
    since_hours: Optional[int] = Query(None, description="Filter to last N hours"),
):
    filtered = _threats

    if severity:
        filtered = [t for t in filtered if t["severity"] == severity]
    if status:
        filtered = [t for t in filtered if t["status"] == status]
    if threat_type:
        filtered = [t for t in filtered if t["threat_type"] == threat_type]
    if since_hours:
        cutoff = datetime.utcnow() - timedelta(hours=since_hours)
        filtered = [t for t in filtered if t["created_at"] >= cutoff]

    total = len(filtered)
    start = (page - 1) * page_size
    page_items = filtered[start: start + page_size]

    return ThreatListResponse(
        threats=[ThreatResponse(**t) for t in page_items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=ThreatStats)
async def get_stats():
    now = datetime.utcnow()
    cutoff_24h = now - timedelta(hours=24)

    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    type_counts: dict = {}
    scores = []
    auto_contained = 0
    open_count = 0
    last_24h = 0

    for t in _threats:
        sev = t.get("severity", "low")
        counts[sev] = counts.get(sev, 0) + 1
        tt = t.get("threat_type", "unknown")
        type_counts[tt] = type_counts.get(tt, 0) + 1
        scores.append(t.get("confidence_score", 0))
        if t.get("auto_contained"):
            auto_contained += 1
        if t.get("status") == "open":
            open_count += 1
        if t.get("created_at", datetime.min) >= cutoff_24h:
            last_24h += 1

    top_types = sorted(
        [{"type": k, "count": v} for k, v in type_counts.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:5]

    return ThreatStats(
        total_threats=len(_threats),
        critical=counts["critical"],
        high=counts["high"],
        medium=counts["medium"],
        low=counts["low"],
        auto_contained=auto_contained,
        open=open_count,
        threats_last_24h=last_24h,
        avg_confidence=sum(scores) / len(scores) if scores else 0.0,
        top_threat_types=top_types,
    )


@router.get("/{threat_id}", response_model=ThreatResponse)
async def get_threat(threat_id: str):
    for t in _threats:
        if t["id"] == threat_id:
            return ThreatResponse(**t)
    raise HTTPException(status_code=404, detail="Threat not found")


@router.patch("/{threat_id}/status")
async def update_status(threat_id: str, status: ThreatStatus):
    for t in _threats:
        if t["id"] == threat_id:
            t["status"] = status
            t["updated_at"] = datetime.utcnow()
            return ThreatResponse(**t)
    raise HTTPException(status_code=404, detail="Threat not found")


@router.post("/simulate")
async def simulate_threat():
    """
    Demo endpoint — injects a synthetic threat for dashboard demos.
    """
    import random
    from app.models.threat import ThreatType

    types = list(ThreatType)
    severities = ["low", "medium", "high", "critical"]
    weights = [0.35, 0.35, 0.20, 0.10]

    sev = random.choices(severities, weights=weights)[0]
    score = {"low": 0.55, "medium": 0.70, "high": 0.83, "critical": 0.94}[sev]
    score += random.uniform(-0.05, 0.05)

    fake = ThreatCreate(
        threat_type=random.choice(types),
        severity=sev,
        confidence_score=min(max(score, 0.5), 0.99),
        description=f"Simulated {sev} threat for demo purposes",
        source_ip=f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
        target_resource=f"i-{uuid.uuid4().hex[:16]}",
        indicators=random.sample(["statistical_outlier", "behavioral_deviation", "unusual_network_path"], k=2),
        model_scores={
            "isolation_forest": round(random.uniform(0.4, 0.95), 3),
            "lstm": round(random.uniform(0.4, 0.95), 3),
            "graph": round(random.uniform(0.4, 0.95), 3),
        },
        region=random.choice(["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"]),
    )

    saved = await persist_threat(fake)

    from app.api.websocket import broadcast_event
    await broadcast_event({
        "type": "new_threat",
        "threat": {
            "id": saved.id,
            "severity": saved.severity,
            "threat_type": saved.threat_type,
            "confidence_score": saved.confidence_score,
            "source_ip": saved.source_ip,
            "description": saved.description,
            "created_at": saved.created_at.isoformat(),
        },
    })

    return saved