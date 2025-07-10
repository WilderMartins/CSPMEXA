# Cópia de backend/collector_service/app/schemas/huawei_iam.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class HuaweiIAMUserLoginProtect(BaseModel):
    enabled: bool
    verification_method: Optional[str] = None

class HuaweiIAMUserAccessKey(BaseModel):
    access_key: str = Field(alias="access")
    status: str
    create_time: Optional[datetime] = Field(None, alias="create_time_format")
    description: Optional[str] = None
    class Config: populate_by_name = True

class HuaweiIAMUserMfaDevice(BaseModel):
    serial_number: str
    type: str

class HuaweiIAMUserData(BaseModel):
    id: str
    name: str
    domain_id: str
    enabled: bool
    email: Optional[str] = None
    phone: Optional[str] = Field(None, alias="areacode_mobile")
    login_protect: Optional[HuaweiIAMUserLoginProtect] = Field(None, alias="login_protect")
    access_keys: Optional[List[HuaweiIAMUserAccessKey]] = None
    mfa_devices: Optional[List[HuaweiIAMUserMfaDevice]] = None
    error_details: Optional[str] = None
    class Config: populate_by_name = True
