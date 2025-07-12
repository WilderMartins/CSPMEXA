from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import datetime

# Referência: https://cloud.google.com/logging/docs/reference/v2/rest/v2/LogEntry

class GCPLogEntryOperation(BaseModel):
    id: Optional[str] = None
    producer: Optional[str] = None
    first: Optional[bool] = None
    last: Optional[bool] = None

class GCPLogEntrySourceLocation(BaseModel):
    file: Optional[str] = None
    line: Optional[str] = None # Geralmente string, mesmo que seja número
    function: Optional[str] = None

class GCPLogEntry(BaseModel):
    log_name: str = Field(..., alias="logName")
    resource: Dict[str, Any] # MonitoredResource, https://cloud.google.com/logging/docs/reference/v2/rest/v2/MonitoredResource
    timestamp: datetime.datetime
    receive_timestamp: Optional[datetime.datetime] = Field(None, alias="receiveTimestamp")
    severity: Optional[str] = None # DEBUG, INFO, NOTICE, WARNING, ERROR, CRITICAL, ALERT, EMERGENCY
    insert_id: Optional[str] = Field(None, alias="insertId")
    http_request: Optional[Dict[str, Any]] = Field(None, alias="httpRequest") # HttpRequest, https://cloud.google.com/logging/docs/reference/v2/rest/v2/LogEntry#HttpRequest
    labels: Optional[Dict[str, str]] = None
    operation: Optional[GCPLogEntryOperation] = None
    trace: Optional[str] = None # Formato: "projects/{project_id}/traces/{trace_id}"
    span_id: Optional[str] = Field(None, alias="spanId")
    trace_sampled: Optional[bool] = Field(None, alias="traceSampled")
    source_location: Optional[GCPLogEntrySourceLocation] = Field(None, alias="sourceLocation")

    # Payload principal: pode ser textPayload, jsonPayload, protoPayload
    text_payload: Optional[str] = Field(None, alias="textPayload")
    json_payload: Optional[Dict[str, Any]] = Field(None, alias="jsonPayload") # Struct
    proto_payload: Optional[Dict[str, Any]] = Field(None, alias="protoPayload") # Any - Contém o AuditLog

    # Campos extraídos/processados pelo coletor
    # Especialmente do protoPayload.AuditLog
    audit_log_service_name: Optional[str] = None
    audit_log_method_name: Optional[str] = None
    audit_log_resource_name: Optional[str] = None
    audit_log_principal_email: Optional[str] = None
    audit_log_caller_ip: Optional[str] = None
    # Adicionar mais campos extraídos do AuditLog conforme necessário para políticas

    collection_error_details: Optional[str] = None

    class Config:
        populate_by_name = True
        extra = 'ignore'
        arbitrary_types_allowed = True

class GCPCloudAuditLogCollection(BaseModel):
    entries: List[GCPLogEntry] = Field(default_factory=list)
    next_page_token: Optional[str] = Field(None, alias="nextPageToken")

    # Contexto da coleta
    filter_used: Optional[str] = None
    projects_queried: Optional[List[str]] = None # Se a consulta for a nível de organização/pasta
    error_message: Optional[str] = None

    class Config:
        populate_by_name = True
        extra = 'ignore'

# Estrutura esperada dentro de protoPayload para AuditLogs:
# "protoPayload": {
#  "@type": "type.googleapis.com/google.cloud.audit.AuditLog",
#  "status": { ... },
#  "authenticationInfo": { "principalEmail": "user@example.com", ... },
#  "requestMetadata": { "callerIp": "1.2.3.4", ... },
#  "serviceName": "compute.googleapis.com",
#  "methodName": "v1.compute.instances.delete",
#  "resourceName": "projects/p/zones/z/instances/i",
#  "request": { ... }, // Struct
#  "response": { ... } // Struct
# }
```
