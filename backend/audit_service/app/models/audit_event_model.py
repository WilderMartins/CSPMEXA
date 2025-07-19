from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.sql import func
from app.db.session import Base

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    actor = Column(String, index=True)
    action = Column(String, index=True)
    resource = Column(String, nullable=True, index=True)
    details = Column(JSON, nullable=True)
