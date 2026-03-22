from fastapi import APIRouter
from datetime import datetime, timedelta
from typing import List
import random

router = APIRouter()


@router.get("/timeseries")
async def get_timeseries(hours: int = 24):
    """Returns per-hour threat counts for the chart."""
    from app.api.threats import _threats

    now = datetime.utcnow()
    buckets = {}

    for i in range(hours):
        hour = (now - timedelta(hours=hours - i)).replace(minute=0, second=0, microsecond=0)
        buckets[hour.isoformat()] = {"time": hour.isoformat(), "critical": 0, "high": 0, "medium": 0, "low": 0}

    for t in _threats:
        ts = t.get("created_at", now)
        bucket_key = ts.replace(minute=0, second=0, microsecond=0).isoformat()
        if bucket_key in buckets:
            sev = t.get("severity", "low")
            buckets[bucket_key][sev] = buckets[bucket_key].get(sev, 0) + 1

    return list(buckets.values())


@router.get("/model-performance")
async def get_model_performance():
    """Returns per-model score distribution from recent threats."""
    from app.api.threats import _threats

    recent = _threats[:200]
    if not recent:
        return {"isolation_forest": 0, "lstm": 0, "graph": 0}

    totals = {"isolation_forest": 0.0, "lstm": 0.0, "graph": 0.0}
    for t in recent:
        scores = t.get("model_scores", {})
        for k in totals:
            totals[k] += scores.get(k, 0)

    n = len(recent)
    return {k: round(v / n, 3) for k, v in totals.items()}