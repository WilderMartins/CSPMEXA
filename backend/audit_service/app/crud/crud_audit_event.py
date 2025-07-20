from sqlalchemy.orm import Session
from app.models.audit_event_model import AuditEvent
from app.schemas.audit_event_schema import AuditEventCreate
from typing import Optional

def create_audit_event(db: Session, event: AuditEventCreate) -> AuditEvent:
    db_event = AuditEvent(**event.dict())
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event

def get_audit_events(
    db: Session,
    actor: Optional[str] = None,
    action: Optional[str] = None,
    resource: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> list[AuditEvent]:
    query = db.query(AuditEvent)
    if actor:
        query = query.filter(AuditEvent.actor.ilike(f"%{actor}%"))
    if action:
        query = query.filter(AuditEvent.action.ilike(f"%{action}%"))
    if resource:
        query = query.filter(AuditEvent.resource.ilike(f"%{resource}%"))
    return query.offset(skip).limit(limit).all()
