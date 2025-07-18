from sqlalchemy import Column, Integer, String, DateTime, func, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()

class RemediationStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class RemediationRequest(Base):
    __tablename__ = "remediation_requests"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=False)
    status = Column(SQLEnum(RemediationStatusEnum), nullable=False, default=RemediationStatusEnum.PENDING)

    requested_by_user_id = Column(Integer, nullable=False)
    approved_by_user_id = Column(Integer, nullable=True)

    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    alert = relationship("AlertModel")
