from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import datetime

# Espelha collector_service/app/schemas/gcp/gcp_cloud_audit_log_schemas.py

class GCPLogEntryOperation(BaseModel):
    id: Optional[str] = None
    producer: Optional[str] = None
    first: Optional[bool] = None
    last: Optional[bool] = None
    class Config: extra = 'ignore'

class GCPLogEntrySourceLocation(BaseModel):
    file: Optional[str] = None
    line: Optional[str] = None
    function: Optional[str] = None
    class Config: extra = 'ignore'

class GCPLogEntry(BaseModel):
    log_name: str = Field(..., alias="logName")
    resource: Dict[str, Any]
    timestamp: datetime.datetime
    receive_timestamp: Optional[datetime.datetime] = Field(None, alias="receiveTimestamp")
    severity: Optional[str] = None
    insert_id: Optional[str] = Field(None, alias="insertId")
    http_request: Optional[Dict[str, Any]] = Field(None, alias="httpRequest")
    labels: Optional[Dict[str, str]] = None
    operation: Optional[GCPLogEntryOperation] = None
    trace: Optional[str] = None
    span_id: Optional[str] = Field(None, alias="spanId")
    trace_sampled: Optional[bool] = Field(None, alias="traceSampled")
    source_location: Optional[GCPLogEntrySourceLocation] = Field(None, alias="sourceLocation")
    text_payload: Optional[str] = Field(None, alias="textPayload")
    json_payload: Optional[Dict[str, Any]] = Field(None, alias="jsonPayload")
    proto_payload: Optional[Dict[str, Any]] = Field(None, alias="protoPayload")
    audit_log_service_name: Optional[str] = None
    audit_log_method_name: Optional[str] = None
    audit_log_resource_name: Optional[str] = None
    audit_log_principal_email: Optional[str] = None
    audit_log_caller_ip: Optional[str] = None
    collection_error_details: Optional[str] = None

    class Config:
        populate_by_name = True
        extra = 'ignore'
        arbitrary_types_allowed = True

class GCPCloudAuditLogCollection(BaseModel):
    entries: List[GCPLogEntry] = Field(default_factory=list)
    next_page_token: Optional[str] = Field(None, alias="nextPageToken")
    filter_used: Optional[str] = None
    projects_queried: Optional[List[str]] = None
    error_message: Optional[str] = None

    class Config:
        populate_by_name = True
        extra = 'ignore'
```
