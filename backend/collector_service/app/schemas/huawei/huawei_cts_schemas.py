from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import datetime

class CTSUserIdentity(BaseModel):
    type: Optional[str] = None # e.g., "Account", "IAMUser", "AssumedRole"
    principal_id: Optional[str] = Field(None, alias="principalId") # ID do usuário ou conta
    user_name: Optional[str] = Field(None, alias="userName") # Nome do usuário IAM
    domain_name: Optional[str] = Field(None, alias="domainName") # Nome do domínio/conta
    access_key_id: Optional[str] = Field(None, alias="accessKeyId")

class CTSRequestParameters(BaseModel):
    # Este campo pode variar muito dependendo do evento. Usar Dict[str, Any] é flexível.
    # Para políticas específicas, pode ser necessário modelar subconjuntos.
    additional_properties: Optional[Dict[str, Any]] = Field(None, alias="additionalProperties")

    class Config:
        extra = 'allow' # Permite campos não definidos explicitamente

class CTSResponseElements(BaseModel):
    # Similar ao requestParameters, muito variável.
    additional_properties: Optional[Dict[str, Any]] = Field(None, alias="additionalProperties")

    class Config:
        extra = 'allow'

class CTSTrace(BaseModel):
    trace_id: str = Field(..., alias="traceId", description="Unique ID of the trace event.")
    trace_name: str = Field(..., alias="traceName", description="Name of the event/operation.")
    trace_rating: Optional[str] = Field(None, alias="traceRating", description="Severity or rating (e.g., 'normal', 'warning', 'incident').") # Pode não existir, depende da API

    event_source: Optional[str] = Field(None, alias="eventSource", description="Service that originated the event (e.g., 'obs.huawei.com').")
    event_time: datetime.datetime = Field(..., alias="eventTime", description="Timestamp of when the event occurred.")
    event_name: Optional[str] = Field(None, alias="eventName", description="Specific name of the API call or event.") # Pode ser redundante com traceName

    user_identity: Optional[CTSUserIdentity] = Field(None, alias="userIdentity")
    source_ip_address: Optional[str] = Field(None, alias="sourceIPAddress")

    request_parameters: Optional[Dict[str, Any]] = Field(None, alias="requestParameters") # Ou usar o modelo CTSRequestParameters
    response_elements: Optional[Dict[str, Any]] = Field(None, alias="responseElements") # Ou usar o modelo CTSResponseElements

    resource_type: Optional[str] = Field(None, alias="resourceType", description="Type of the resource affected.")
    resource_name: Optional[str] = Field(None, alias="resourceName", description="Name/ID of the resource affected.")
    region_id: Optional[str] = Field(None, alias="regionId", description="Region where the event occurred.") # Pode estar no trace ou no recurso

    error_code: Optional[str] = Field(None, alias="errorCode")
    error_message: Optional[str] = Field(None, alias="errorMessage")

    api_version: Optional[str] = Field(None, alias="apiVersion")
    read_only: Optional[bool] = Field(None, alias="readOnly", description="Whether the event was a read-only operation.")

    # Campos específicos do CTS
    tracker_name: Optional[str] = Field(None, alias="trackerName", description="Name of the CTS tracker that recorded the event.")
    domain_id: Optional[str] = Field(None, alias="domainId", description="Domain ID associated with the event.") # Pode ser o mesmo que account_id

    # Para erros de coleta específicos deste trace
    collection_error_details: Optional[str] = None

    class Config:
        populate_by_name = True # Permite que 'traceId' no JSON mapeie para trace_id
        extra = 'ignore' # Ignora campos extras do JSON que não estão no modelo
        arbitrary_types_allowed = True # Para datetime

class CTSTraceCollection(BaseModel):
    traces: List[CTSTrace] = Field(default_factory=list)
    next_marker: Optional[str] = Field(None, alias="nextMarker", description="Marker for pagination if results are truncated.")
    total_count: Optional[int] = Field(None, alias="totalCount", description="Total count of traces if available from API.")
    error_message: Optional[str] = None # Para erros globais na coleta de traces

    class Config:
        populate_by_name = True
        extra = 'ignore'

# Exemplo de como os campos requestParameters e responseElements podem ser usados:
# Se soubermos que um evento CreateBucket tem certos parâmetros, podemos criar um schema específico.
# class CreateBucketRequestParams(CTSRequestParameters):
#     Bucket: str
#     ACL: Optional[str] = None
# ... e assim por diante.
# Mas para um coletor genérico, Dict[str, Any] é mais flexível.
```
