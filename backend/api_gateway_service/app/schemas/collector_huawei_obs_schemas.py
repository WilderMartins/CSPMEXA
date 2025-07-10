# Cópia de backend/collector_service/app/schemas/huawei_obs.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class HuaweiOBSBucketPolicyStatementCondition(BaseModel):
    condition_operator: str
    condition_key: str
    condition_values: List[str]

class HuaweiOBSBucketPolicyStatement(BaseModel):
    sid: Optional[str] = Field(None, alias="Sid")
    effect: str = Field(alias="Effect")
    principal: Dict[str, Any] = Field(alias="Principal")
    action: List[str] = Field(alias="Action")
    resource: List[str] = Field(alias="Resource")
    condition: Optional[Dict[str, Dict[str, List[str]]]] = Field(None, alias="Condition")
    class Config: populate_by_name = True

class HuaweiOBSBucketPolicy(BaseModel):
    version: Optional[str] = Field(None, alias="Version")
    statement: List[HuaweiOBSBucketPolicyStatement] = Field(alias="Statement")
    class Config: populate_by_name = True

class HuaweiOBSGrantee(BaseModel):
    id: Optional[str] = Field(None, alias="ID")
    uri: Optional[str] = Field(None, alias="URI")
    class Config: populate_by_name = True

class HuaweiOBSGrant(BaseModel):
    grantee: HuaweiOBSGrantee = Field(alias="Grantee")
    permission: str = Field(alias="Permission")
    class Config: populate_by_name = True

class HuaweiOBSOwner(BaseModel):
    id: str = Field(alias="ID")
    class Config: populate_by_name = True

class HuaweiOBSBucketACL(BaseModel):
    owner: HuaweiOBSOwner = Field(alias="Owner")
    grants: List[HuaweiOBSGrant] = Field([], alias="Grant")
    class Config: populate_by_name = True

class HuaweiOBSBucketVersioning(BaseModel):
    status: Optional[str] = Field(None)

class HuaweiOBSBucketLogging(BaseModel):
    enabled: bool = False
    target_bucket: Optional[str] = Field(None)
    target_prefix: Optional[str] = Field(None)

class HuaweiOBSBucketData(BaseModel):
    name: str
    creation_date: Optional[datetime] = None
    location: Optional[str] = None
    storage_class: Optional[str] = None
    bucket_policy: Optional[HuaweiOBSBucketPolicy] = None
    acl: Optional[HuaweiOBSBucketACL] = None
    versioning: Optional[HuaweiOBSBucketVersioning] = None
    logging: Optional[HuaweiOBSBucketLogging] = None
    is_public_by_policy: Optional[bool] = None
    public_policy_details: List[str] = []
    is_public_by_acl: Optional[bool] = None
    public_acl_details: List[str] = []
    error_details: Optional[str] = None
    class Config: pass
