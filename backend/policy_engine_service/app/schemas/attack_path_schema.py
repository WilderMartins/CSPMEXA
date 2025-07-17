from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import datetime
from app.models.attack_path_model import AttackPathSeverityEnum

class AttackPathNode(BaseModel):
    asset_id: int
    asset_type: str
    name: str

class AttackPathBase(BaseModel):
    path_id: str
    description: str
    severity: AttackPathSeverityEnum
    nodes: List[AttackPathNode]

class AttackPathCreate(AttackPathBase):
    pass

class AttackPathSchema(AttackPathBase):
    id: int
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True
