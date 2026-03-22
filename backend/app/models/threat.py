from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ThreatSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatStatus(str, Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    CONTAINED = "contained"
    RESOLVED = "resolved"


class ThreatType(str, Enum):
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"
    LATERAL_MOVEMENT = "lateral_movement"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXFILTRATION = "data_exfiltration"
    ZERO_DAY_EXPLOIT = "zero_day_exploit"
    COMMAND_INJECTION = "command_injection"
    UNUSUAL_API_PATTERN = "unusual_api_pattern"
    MEMORY_CORRUPTION = "memory_corruption"


class ThreatCreate(BaseModel):
    threat_type: ThreatType
    severity: ThreatSeverity
    confidence_score: float = Field(ge=0.0, le=1.0)
    description: str
    source_ip: Optional[str] = None
    target_resource: Optional[str] = None
    indicators: List[str] = []
    raw_events: List[Dict[str, Any]] = []
    model_scores: Dict[str, float] = {}
    region: Optional[str] = None


class ThreatResponse(ThreatCreate):
    id: str
    status: ThreatStatus = ThreatStatus.OPEN
    created_at: datetime
    updated_at: datetime
    auto_contained: bool = False
    alert_sent: bool = False

    class Config:
        from_attributes = True


class ThreatListResponse(BaseModel):
    threats: List[ThreatResponse]
    total: int
    page: int
    page_size: int


class ThreatStats(BaseModel):
    total_threats: int
    critical: int
    high: int
    medium: int
    low: int
    auto_contained: int
    open: int
    threats_last_24h: int
    avg_confidence: float
    top_threat_types: List[Dict[str, Any]]