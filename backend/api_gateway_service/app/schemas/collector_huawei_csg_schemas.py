from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import datetime

# Espelha collector_service/app/schemas/huawei/huawei_csg_schemas.py

class CSGRiskResourceInfo(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None
    region_id: Optional[str] = Field(None, alias="regionId")
    project_id: Optional[str] = Field(None, alias="projectId")

    class Config:
        populate_by_name = True
        extra = 'ignore'

class CSGRiskItem(BaseModel):
    risk_id: str = Field(..., alias="riskId")
    check_name: Optional[str] = Field(None, alias="checkName")
    description: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    resource_info: CSGRiskResourceInfo = Field(..., alias="resource")
    suggestion: Optional[str] = None
    first_detected_time: Optional[datetime.datetime] = Field(None, alias="firstDetectedTime")
    last_detected_time: Optional[datetime.datetime] = Field(None, alias="lastDetectedTime")
    additional_properties: Optional[Dict[str, Any]] = None
    collection_error_details: Optional[str] = None

    class Config:
        populate_by_name = True
        extra = 'ignore'
        arbitrary_types_allowed = True

class CSGRiskCollection(BaseModel):
    risks: List[CSGRiskItem] = Field(default_factory=list)
    total_count: Optional[int] = Field(None, alias="totalCount")
    next_marker: Optional[str] = Field(None, alias="nextMarker")
    domain_id_queried: Optional[str] = None
    project_id_queried: Optional[str] = None
    region_id_queried: Optional[str] = None
    error_message: Optional[str] = None

    class Config:
        populate_by_name = True
        extra = 'ignore'
