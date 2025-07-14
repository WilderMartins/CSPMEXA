from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import datetime

# Espelha collector_service/app/schemas/google_workspace/gws_audit_log_schemas.py

class GWSAuditLogActorInput(BaseModel):
    caller_type: Optional[str] = Field(None, alias="callerType")
    email: Optional[str] = None
    profile_id: Optional[str] = Field(None, alias="profileId")
    key: Optional[str] = None

    class Config:
        populate_by_name = True
        extra = 'ignore'

class GWSAuditLogEventParameterInput(BaseModel):
    name: Optional[str] = None
    value: Optional[str] = None
    multi_value: Optional[List[str]] = Field(None, alias="multiValue")
    message_value: Optional[Dict[str, Any]] = Field(None, alias="messageValue")

    class Config:
        populate_by_name = True
        extra = 'ignore'

class GWSAuditLogEventInput(BaseModel):
    type: Optional[str] = None
    name: Optional[str] = None # Ex: "login_failure", "download", "create_user"
    parameters: Optional[List[GWSAuditLogEventParameterInput]] = Field(default_factory=list)

    class Config:
        extra = 'ignore'

class GWSAuditLogItemInput(BaseModel):
    # kind: Optional[str] = None # Não essencial para políticas
    id_time: datetime.datetime = Field(..., alias="id.time")
    # id_unique_qualifier: Optional[str] = Field(None, alias="id.uniqueQualifier")
    id_application_name: str = Field(..., alias="id.applicationName") # "login", "drive", "admin", etc.
    # id_customer_id: Optional[str] = Field(None, alias="id.customerId") # account_id global será usado
    actor: Optional[GWSAuditLogActorInput] = None
    ip_address: Optional[str] = Field(None, alias="ipAddress")
    events: Optional[List[GWSAuditLogEventInput]] = Field(default_factory=list)
    collection_error_details: Optional[str] = None

    class Config:
        populate_by_name = True
        extra = 'ignore'
        arbitrary_types_allowed = True

class GWSAuditLogCollectionInput(BaseModel):
    items: List[GWSAuditLogItemInput] = Field(default_factory=list)
    application_name_queried: Optional[str] = None # Para contexto
    error_message: Optional[str] = None

    class Config:
        populate_by_name = True
        extra = 'ignore'
