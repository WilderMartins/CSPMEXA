from pydantic import BaseModel, Field
from typing import Optional
import datetime
from app.models.remediation_request_model import RemediationStatusEnum
from .alert_schema import AlertSchema

class RemediationRequestBase(BaseModel):
    alert_id: int

class RemediationRequestCreate(RemediationRequestBase):
    requested_by_user_id: int

class RemediationRequestUpdate(BaseModel):
    status: RemediationStatusEnum
    approved_by_user_id: Optional[int] = None

class RemediationRequestSchema(RemediationRequestBase):
    id: int
    status: RemediationStatusEnum
    requested_by_user_id: int
    approved_by_user_id: Optional[int] = None
    requested_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None
    alert: AlertSchema

    class Config:
        from_attributes = True
