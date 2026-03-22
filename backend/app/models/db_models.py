from sqlalchemy import Column, String, Float, Boolean, DateTime, JSON, Text, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


def gen_uuid():
    return str(uuid.uuid4())


class Threat(Base):
    __tablename__ = "threats"

    id = Column(String, primary_key=True, default=gen_uuid)
    threat_type = Column(String, nullable=False, index=True)
    severity = Column(String, nullable=False, index=True)
    status = Column(String, default="open", index=True)
    confidence_score = Column(Float, nullable=False)
    description = Column(Text)
    source_ip = Column(String, index=True)
    target_resource = Column(String)
    indicators = Column(JSON, default=list)
    raw_events = Column(JSON, default=list)
    model_scores = Column(JSON, default=dict)
    region = Column(String)
    auto_contained = Column(Boolean, default=False)
    alert_sent = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class ThreatMetric(Base):
    __tablename__ = "threat_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bucket = Column(DateTime(timezone=True), index=True)   # 1-min buckets
    threat_count = Column(Integer, default=0)
    critical_count = Column(Integer, default=0)
    avg_score = Column(Float, default=0.0)
    events_processed = Column(Integer, default=0)
    region = Column(String)