from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import datetime

# Referência da API: https://developers.google.com/admin-sdk/reports/v1/reference/activities/list

class GWSAuditLogActor(BaseModel):
    caller_type: Optional[str] = Field(None, alias="callerType", description="Type of actor (USER or APPLICATION).")
    email: Optional[str] = Field(None, description="Email address of the actor.")
    profile_id: Optional[str] = Field(None, alias="profileId", description="Unique G Suite profile ID of the actor.")
    key: Optional[str] = Field(None, description="For OAuth 2LO API requests, the G Suite an OAUth 2LO API
        requests, the G Suite Admin Console domain key of the actor.") # Este campo parece ser menos comum.

class GWSAuditLogEventParameter(BaseModel):
    name: Optional[str] = None
    value: Optional[str] = None # Simples valor string
    multi_value: Optional[List[str]] = Field(None, alias="multiValue")
    message_value: Optional[Dict[str, Any]] = Field(None, alias="messageValue", description="Nested message value.")
    # bool_value: Optional[bool] = Field(None, alias="boolValue") # A API parece retornar tudo como string ou messageValue

    class Config:
        populate_by_name = True

class GWSAuditLogEvent(BaseModel):
    type: Optional[str] = None # Type of event.
    name: Optional[str] = None # Name of the event.
    parameters: Optional[List[GWSAuditLogEventParameter]] = Field(default_factory=list)

class GWSAuditLogItem(BaseModel):
    kind: Optional[str] = None # Identifies the resource as an Admin SDK Report Activity. Value: admin#reports#activity.
    id_time: datetime.datetime = Field(..., alias="id.time", description="Timestamp of the activity.")
    id_unique_qualifier: Optional[str] = Field(None, alias="id.uniqueQualifier", description="Unique qualifier if multiple events have the same time.")
    id_application_name: str = Field(..., alias="id.applicationName", description="Application name to which the event is related.")
    id_customer_id: Optional[str] = Field(None, alias="id.customerId", description="Obfuscated customer ID of G Suite account.")

    actor: Optional[GWSAuditLogActor] = None
    ip_address: Optional[str] = Field(None, alias="ipAddress", description="IP address of the actor.")
    # owner_domain: Optional[str] = Field(None, alias="ownerDomain") # Menos comum

    events: Optional[List[GWSAuditLogEvent]] = Field(default_factory=list)

    # Para erros de coleta específicos deste log item
    collection_error_details: Optional[str] = None

    class Config:
        populate_by_name = True
        extra = 'ignore'

class GWSAuditLogCollection(BaseModel):
    kind: Optional[str] = None # admin#reports#activities
    next_page_token: Optional[str] = Field(None, alias="nextPageToken")
    items: List[GWSAuditLogItem] = Field(default_factory=list)

    # Campos adicionados pelo coletor
    application_name_queried: Optional[str] = None
    start_time_queried: Optional[datetime.datetime] = None
    end_time_queried: Optional[datetime.datetime] = None
    error_message: Optional[str] = None # Para erros globais na coleta

    class Config:
        populate_by_name = True
        extra = 'ignore'

# Application Names Comuns para Auditoria:
# - admin: Admin console actions
# - login: User logins
# - drive: Google Drive activity
# - token: Third-party OAuth token activity
# - groups: Google Groups activity
# - calendar: Google Calendar activity
# - chat: Google Chat activity
# - meet: Google Meet activity
# - mobile: Mobile device management activity
# - user_accounts: User account changes
# - access_transparency: Access Transparency logs
```
