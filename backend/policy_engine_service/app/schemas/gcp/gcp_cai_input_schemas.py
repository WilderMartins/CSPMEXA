from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import datetime

# Espelha collector_service/app/schemas/gcp/gcp_cai_schemas.py

class GCPAssetInput(BaseModel):
    name: str
    asset_type: str = Field(..., alias="assetType")
    resource: Optional[Dict[str, Any]] = None # Onde esperamos encontrar 'labels' ou 'tags'
    iam_policy: Optional[Dict[str, Any]] = Field(None, alias="iamPolicy")

    project_id: Optional[str] = None
    location: Optional[str] = None
    display_name: Optional[str] = None
    create_time: Optional[datetime.datetime] = Field(None, alias="createTime")
    update_time: Optional[datetime.datetime] = Field(None, alias="updateTime")
    collection_error_details: Optional[str] = None

    class Config:
        populate_by_name = True
        extra = 'ignore'
        arbitrary_types_allowed = True

class GCPAssetCollectionInput(BaseModel):
    assets: List[GCPAssetInput] = Field(default_factory=list)
    scope_queried: Optional[str] = None
    asset_types_queried: Optional[List[str]] = None
    content_type_queried: Optional[str] = None
    error_message: Optional[str] = None

    class Config:
        populate_by_name = True
        extra = 'ignore'
```
