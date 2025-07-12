from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import datetime

# Espelha collector_service/app/schemas/huawei/huawei_cts_schemas.py

class CTSUserIdentity(BaseModel):
    type: Optional[str] = None
    principal_id: Optional[str] = Field(None, alias="principalId")
    user_name: Optional[str] = Field(None, alias="userName")
    domain_name: Optional[str] = Field(None, alias="domainName")
    access_key_id: Optional[str] = Field(None, alias="accessKeyId")

    class Config:
        populate_by_name = True
        extra = 'ignore'

class CTSTrace(BaseModel):
    trace_id: str = Field(..., alias="traceId")
    trace_name: str = Field(..., alias="traceName")
    trace_rating: Optional[str] = Field(None, alias="traceRating")
    event_source: Optional[str] = Field(None, alias="eventSource")
    event_time: datetime.datetime = Field(..., alias="eventTime")
    event_name: Optional[str] = Field(None, alias="eventName")
    user_identity: Optional[CTSUserIdentity] = Field(None, alias="userIdentity")
    source_ip_address: Optional[str] = Field(None, alias="sourceIPAddress")
    request_parameters: Optional[Dict[str, Any]] = Field(None, alias="requestParameters")
    response_elements: Optional[Dict[str, Any]] = Field(None, alias="responseElements")
    resource_type: Optional[str] = Field(None, alias="resourceType")
    resource_name: Optional[str] = Field(None, alias="resourceName")
    region_id: Optional[str] = Field(None, alias="regionId")
    error_code: Optional[str] = Field(None, alias="errorCode")
    error_message: Optional[str] = Field(None, alias="errorMessage")
    api_version: Optional[str] = Field(None, alias="apiVersion")
    read_only: Optional[bool] = Field(None, alias="readOnly")
    tracker_name: Optional[str] = Field(None, alias="trackerName")
    domain_id: Optional[str] = Field(None, alias="domainId")
    collection_error_details: Optional[str] = None

    class Config:
        populate_by_name = True
        extra = 'ignore'
        arbitrary_types_allowed = True

class CTSTraceCollection(BaseModel):
    traces: List[CTSTrace] = Field(default_factory=list)
    next_marker: Optional[str] = Field(None, alias="nextMarker")
    total_count: Optional[int] = Field(None, alias="totalCount")
    error_message: Optional[str] = None

    class Config:
        populate_by_name = True
        extra = 'ignore'
