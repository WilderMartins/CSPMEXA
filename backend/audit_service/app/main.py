from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db, engine
from app.models import audit_event_model
from app.schemas import audit_event_schema
from app.crud import crud_audit_event

audit_event_model.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Audit Service",
    description="Service for logging audit trails.",
    version="0.1.0",
)

@app.post("/events/", response_model=audit_event_schema.AuditEvent)
def create_event(
    event: audit_event_schema.AuditEventCreate, db: Session = Depends(get_db)
):
    return crud_audit_event.create_audit_event(db=db, event=event)

from typing import Optional

@app.get("/events/", response_model=list[audit_event_schema.AuditEvent])
def read_events(
    actor: Optional[str] = None,
    action: Optional[str] = None,
    resource: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    events = crud_audit_event.get_audit_events(
        db, actor=actor, action=action, resource=resource, skip=skip, limit=limit
    )
    return events

@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "ok", "service_name": "Audit Service"}
