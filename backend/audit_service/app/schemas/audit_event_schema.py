from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class AuditEventCreate(BaseModel):
    actor: str
    action: str
    resource: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class AuditEvent(AuditEventCreate):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True
