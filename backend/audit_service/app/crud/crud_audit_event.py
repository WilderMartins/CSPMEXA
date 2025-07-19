from sqlalchemy.orm import Session
from app.models.audit_event_model import AuditEvent
from app.schemas.audit_event_schema import AuditEventCreate

def create_audit_event(db: Session, event: AuditEventCreate) -> AuditEvent:
    db_event = AuditEvent(**event.dict())
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event

def get_audit_events(db: Session, skip: int = 0, limit: int = 100) -> list[AuditEvent]:
    return db.query(AuditEvent).offset(skip).limit(limit).all()
