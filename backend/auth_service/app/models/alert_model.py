from sqlalchemy import Column, String, DateTime, JSON, Text, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from ..db.base_class import Base
import enum

class AlertSeverityEnum(enum.Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    INFORMATIONAL = "Informational"

class AlertStatusEnum(enum.Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    IGNORED = "IGNORED"

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource_id = Column(String, nullable=False, index=True)
    resource_type = Column(String, nullable=False)
    account_id = Column(String, nullable=True, default="N/A", index=True)
    region = Column(String, nullable=True, default="N/A")
    provider = Column(String, nullable=False, default="aws", index=True)

    severity = Column(SAEnum(AlertSeverityEnum, name="alert_severity_enum"), nullable=False, default=AlertSeverityEnum.MEDIUM)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    policy_id = Column(String, nullable=False, index=True)
    status = Column(SAEnum(AlertStatusEnum, name="alert_status_enum"), nullable=False, default=AlertStatusEnum.OPEN, index=True)

    details = Column(JSON, nullable=True)
    recommendation = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Alert(id={self.id}, title='{self.title}', resource_id='{self.resource_id}')>"
