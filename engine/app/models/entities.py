from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TargetEntity(Base):
    __tablename__ = "targets"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    target_type = Column(String, default="web") # web, api, app
    url = Column(String, nullable=True)
    calibration_config = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now)

class ScanEntity(Base):
    __tablename__ = "scans"
    id = Column(String, primary_key=True)
    target_id = Column(String, ForeignKey("targets.id"), nullable=False)
    status = Column(String, default="QUEUED") # QUEUED, RUNNING, COMPLETED, STOPPED, FAILED
    category = Column(String, default="LLM07")
    budget = Column(Integer, default=10)
    current_attempt = Column(Integer, default=0)
    created_at = Column(DateTime, default=utc_now)
    completed_at = Column(DateTime, nullable=True)

class ScanTurnEntity(Base):
    __tablename__ = "scan_turns"
    id = Column(String, primary_key=True)
    scan_id = Column(String, ForeignKey("scans.id"), nullable=False)
    turn_index = Column(Integer, nullable=False)
    prompt = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    latency_ms = Column(Integer, default=0)
    strategy = Column(String, nullable=True)
    verdict = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now)

class FindingEntity(Base):
    __tablename__ = "findings"
    id = Column(String, primary_key=True)
    scan_id = Column(String, ForeignKey("scans.id"), nullable=False)
    turn_id = Column(String, ForeignKey("scan_turns.id"), nullable=False)
    category = Column(String, nullable=False)
    severity = Column(String, nullable=False) # CRITICAL, HIGH, MEDIUM, LOW, INFO
    confidence = Column(Float, default=1.0)
    description = Column(Text, nullable=False)
    remediation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

