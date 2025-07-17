from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import datetime
from app.models.asset_model import CloudProviderEnum

class AssetBase(BaseModel):
    asset_id: str
    asset_type: str
    name: Optional[str] = None
    provider: CloudProviderEnum
    account_id: str
    region: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None

class AssetCreate(AssetBase):
    pass

class AssetSchema(AssetBase):
    id: int
    first_seen_at: datetime.datetime
    last_seen_at: datetime.datetime

    class Config:
        from_attributes = True
