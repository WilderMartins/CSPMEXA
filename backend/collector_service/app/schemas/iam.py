from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class IAMUserAccessKeyMetadata(BaseModel):
    access_key_id: str = Field(alias="AccessKeyId")
    status: str = Field(alias="Status") # Active | Inactive
    create_date: datetime = Field(alias="CreateDate")
    # LastUsedDate não está sempre disponível diretamente em list_access_keys,
    # mas pode ser obtido com get_access_key_last_used. Para MVP, podemos omitir ou buscar separadamente.
    last_used_date: Optional[datetime] = Field(None)
    last_used_service: Optional[str] = Field(None)
    last_used_region: Optional[str] = Field(None)


class IAMUserMFADevice(BaseModel):
    user_name: str = Field(alias="UserName")
    serial_number: str = Field(alias="SerialNumber")
    enable_date: datetime = Field(alias="EnableDate")


class IAMPolicyAttachment(BaseModel):
    policy_arn: Optional[str] = Field(None, alias="PolicyArn")
    policy_name: Optional[str] = Field(None, alias="PolicyName") # Extraído do ARN ou de list_policies

class IAMUserPolicy(BaseModel): # Para políticas inline
    policy_name: str = Field(alias="PolicyName")
    policy_document: Optional[Dict[str, Any]] = Field(None) # Opcional, pode ser grande


class IAMUserData(BaseModel):
    user_id: str = Field(alias="UserId")
    user_name: str = Field(alias="UserName")
    arn: str = Field(alias="Arn")
    create_date: datetime = Field(alias="CreateDate")
    password_last_used: Optional[datetime] = Field(None, alias="PasswordLastUsed")

    attached_policies: Optional[List[IAMPolicyAttachment]] = Field(None)
    inline_policies: Optional[List[IAMUserPolicy]] = Field(None) # Lista de nomes de políticas inline

    mfa_devices: Optional[List[IAMUserMFADevice]] = Field(None, description="List of MFA devices associated with the user.")
    access_keys: Optional[List[IAMUserAccessKeyMetadata]] = Field(None, description="Metadata for user's access keys.")

    tags: Optional[List[Dict[str, str]]] = Field(None, alias="Tags")
    error_details: Optional[str] = Field(None, description="Details of any error encountered while fetching data for this user.")
    account_summary: Optional[Dict[str, Any]] = Field(None, description="Account summary map, attached to the first user in the list.")

    class Config:
        populate_by_name = True


class IAMRoleLastUsed(BaseModel):
    last_used_date: Optional[datetime] = Field(None, alias="LastUsedDate")
    region: Optional[str] = Field(None, alias="Region")

class IAMRoleData(BaseModel):
    role_id: str = Field(alias="RoleId")
    role_name: str = Field(alias="RoleName")
    arn: str = Field(alias="Arn")
    create_date: datetime = Field(alias="CreateDate")
    description: Optional[str] = Field(None, alias="Description")
    assume_role_policy_document: Optional[Dict[str, Any]] = Field(None, alias="AssumeRolePolicyDocument")

    attached_policies: Optional[List[IAMPolicyAttachment]] = Field(None)
    inline_policies: Optional[List[IAMUserPolicy]] = Field(None) # Reutilizando IAMUserPolicy para políticas inline de roles

    role_last_used: Optional[IAMRoleLastUsed] = Field(None, alias="RoleLastUsed")
    tags: Optional[List[Dict[str, str]]] = Field(None, alias="Tags")
    error_details: Optional[str] = Field(None, description="Details of any error encountered while fetching data for this role.")

    class Config:
        populate_by_name = True


class IAMPolicyData(BaseModel):
    policy_name: str = Field(alias="PolicyName")
    policy_id: str = Field(alias="PolicyId")
    arn: str = Field(alias="Arn")
    path: Optional[str] = Field(None, alias="Path")
    default_version_id: Optional[str] = Field(None, alias="DefaultVersionId")
    attachment_count: Optional[int] = Field(None, alias="AttachmentCount")
    permissions_boundary_usage_count: Optional[int] = Field(None, alias="PermissionsBoundaryUsageCount")
    is_attachable: bool = Field(True, alias="IsAttachable")
    description: Optional[str] = Field(None, alias="Description")
    create_date: datetime = Field(alias="CreateDate")
    update_date: datetime = Field(alias="UpdateDate")
    policy_document: Optional[Dict[str, Any]] = Field(None) # O documento da versão padrão
    tags: Optional[List[Dict[str, str]]] = Field(None, alias="Tags") # Policies can have tags too
    error_details: Optional[str] = Field(None)

    class Config:
        populate_by_name = True


IAMUsersCollectionResponse = List[IAMUserData]
IAMRolesCollectionResponse = List[IAMRoleData]
IAMPoliciesCollectionResponse = List[IAMPolicyData]

class IAMCollectionError(BaseModel):
    error: str = Field(description="Error message detailing why IAM data collection failed globally.")
