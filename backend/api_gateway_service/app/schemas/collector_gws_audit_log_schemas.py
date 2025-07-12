from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import datetime

# Espelha collector_service/app/schemas/google_workspace/gws_audit_log_schemas.py

class GWSAuditLogActor(BaseModel):
    caller_type: Optional[str] = Field(None, alias="callerType")
    email: Optional[str] = None
    profile_id: Optional[str] = Field(None, alias="profileId")
    key: Optional[str] = None

    class Config:
        populate_by_name = True
        extra = 'ignore'

class GWSAuditLogEventParameter(BaseModel):
    name: Optional[str] = None
    value: Optional[str] = None
    multi_value: Optional[List[str]] = Field(None, alias="multiValue")
    message_value: Optional[Dict[str, Any]] = Field(None, alias="messageValue")

    class Config:
        populate_by_name = True
        extra = 'ignore'

class GWSAuditLogEvent(BaseModel):
    type: Optional[str] = None
    name: Optional[str] = None
    parameters: Optional[List[GWSAuditLogEventParameter]] = Field(default_factory=list)

    class Config:
        extra = 'ignore'

class GWSAuditLogItem(BaseModel):
    kind: Optional[str] = None
    id_time: datetime.datetime = Field(..., alias="id.time")
    id_unique_qualifier: Optional[str] = Field(None, alias="id.uniqueQualifier")
    id_application_name: str = Field(..., alias="id.applicationName")
    id_customer_id: Optional[str] = Field(None, alias="id.customerId")
    actor: Optional[GWSAuditLogActor] = None
    ip_address: Optional[str] = Field(None, alias="ipAddress")
    events: Optional[List[GWSAuditLogEvent]] = Field(default_factory=list)
    collection_error_details: Optional[str] = None

    class Config:
        populate_by_name = True
        extra = 'ignore'
        arbitrary_types_allowed = True

class GWSAuditLogCollection(BaseModel):
    kind: Optional[str] = None
    next_page_token: Optional[str] = Field(None, alias="nextPageToken")
    items: List[GWSAuditLogItem] = Field(default_factory=list)
    application_name_queried: Optional[str] = None
    start_time_queried: Optional[datetime.datetime] = None
    end_time_queried: Optional[datetime.datetime] = None
    error_message: Optional[str] = None

    class Config:
        populate_by_name = True
        extra = 'ignore'
