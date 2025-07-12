from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import datetime

# Espelha collector_service/app/schemas/gcp/gcp_scc_schemas.py

class GCPFindingSourcePropertiesInput(BaseModel):
    additional_properties: Optional[Dict[str, Any]] = None
    class Config:
        extra = 'allow'

class GCPFindingInput(BaseModel):
    name: str
    parent: str
    resource_name: str = Field(..., alias="resourceName")
    state: str
    category: str
    external_uri: Optional[str] = Field(None, alias="externalUri")
    source_properties: Optional[GCPFindingSourcePropertiesInput] = Field(None, alias="sourceProperties")
    event_time: datetime.datetime = Field(..., alias="eventTime")
    create_time: datetime.datetime = Field(..., alias="createTime")
    update_time: Optional[datetime.datetime] = Field(None, alias="updateTime")
    severity: str # CRITICAL, HIGH, MEDIUM, LOW, SEVERITY_UNSPECIFIED
    canonical_name: Optional[str] = Field(None, alias="canonicalName")
    description: Optional[str] = None

    project_id: Optional[str] = None
    organization_id: Optional[str] = None
    source_id: Optional[str] = None
    finding_id: Optional[str] = None
    collection_error_details: Optional[str] = None

    class Config:
        populate_by_name = True
        extra = 'ignore'
        arbitrary_types_allowed = True

class GCPSCCFindingCollectionInput(BaseModel):
    findings: List[GCPFindingInput] = Field(default_factory=list)
    parent_resource_queried: Optional[str] = None
    filter_used: Optional[str] = None
    error_message: Optional[str] = None

    class Config:
        populate_by_name = True
        extra = 'ignore'

```
