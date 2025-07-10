from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

# Schemas espelhando a saída do Collector Service para os dados relevantes para políticas

# --- S3 Schemas ---
class S3BucketACLGrantee(BaseModel):
    type: Optional[str] = None
    display_name: Optional[str] = None
    uri: Optional[str] = None
    id: Optional[str] = None

class S3BucketACLGrant(BaseModel):
    grantee: Optional[S3BucketACLGrantee] = None # Tornando opcional para resiliência
    permission: Optional[str] = None

class S3BucketACLDetails(BaseModel):
    owner_display_name: Optional[str] = None
    owner_id: Optional[str] = None
    grants: List[S3BucketACLGrant] = []
    is_public: Optional[bool] = False # No collector é `is_public`
    public_details: List[str] = []

class S3BucketVersioning(BaseModel):
    status: Optional[str] = None
    mfa_delete: Optional[str] = None

class S3BucketPublicAccessBlock(BaseModel):
    block_public_acls: Optional[bool] = Field(None, alias="BlockPublicAcls")
    ignore_public_acls: Optional[bool] = Field(None, alias="IgnorePublicAcls")
    block_public_policy: Optional[bool] = Field(None, alias="BlockPublicPolicy")
    restrict_public_buckets: Optional[bool] = Field(None, alias="RestrictPublicBuckets")
    class Config:
        populate_by_name = True

class S3BucketLogging(BaseModel):
    enabled: Optional[bool] = False # Tornando opcional
    target_bucket: Optional[str] = None
    target_prefix: Optional[str] = None

class S3BucketDataInput(BaseModel): # Renomeado de S3BucketData para evitar conflito com collector
    name: str
    creation_date: Optional[datetime] = None
    region: str
    acl: Optional[S3BucketACLDetails] = None
    policy: Optional[Dict[str, Any]] = None
    policy_is_public: Optional[bool] = None
    versioning: Optional[S3BucketVersioning] = None
    public_access_block: Optional[S3BucketPublicAccessBlock] = None
    logging: Optional[S3BucketLogging] = None
    error_details: Optional[str] = None


# --- EC2 Schemas ---
class EC2InstanceState(BaseModel):
    code: Optional[int] = None
    name: Optional[str] = None

class EC2IpPermission(BaseModel):
    from_port: Optional[int] = Field(None, alias="FromPort")
    to_port: Optional[int] = Field(None, alias="ToPort")
    ip_protocol: Optional[str] = Field(None, alias="IpProtocol")
    ip_ranges: Optional[List[Dict[str, Any]]] = Field(None, alias="IpRanges")
    ipv6_ranges: Optional[List[Dict[str, Any]]] = Field(None, alias="Ipv6Ranges")
    prefix_list_ids: Optional[List[Dict[str, Any]]] = Field(None, alias="PrefixListIds")
    user_id_group_pairs: Optional[List[Dict[str, Any]]] = Field(None, alias="UserIdGroupPairs")
    class Config:
        populate_by_name = True

class EC2SecurityGroupDataInput(BaseModel):
    group_id: str = Field(alias="GroupId")
    group_name: Optional[str] = Field(None, alias="GroupName")
    description: Optional[str] = Field(None, alias="Description")
    vpc_id: Optional[str] = Field(None, alias="VpcId")
    owner_id: Optional[str] = Field(None, alias="OwnerId")
    ip_permissions: List[EC2IpPermission] = Field([], alias="IpPermissions")
    ip_permissions_egress: List[EC2IpPermission] = Field([], alias="IpPermissionsEgress")
    tags: Optional[List[Dict[str, str]]] = Field(None, alias="Tags")
    region: str = Field(description="AWS region where the Security Group is located.")

    class Config:
        populate_by_name = True

class EC2InstanceDataInput(BaseModel):
    instance_id: str = Field(alias="InstanceId")
    instance_type: Optional[str] = Field(None, alias="InstanceType")
    image_id: Optional[str] = Field(None, alias="ImageId")
    launch_time: Optional[datetime] = Field(None, alias="LaunchTime")
    platform: Optional[str] = Field(None, alias="PlatformDetails")
    private_ip_address: Optional[str] = Field(None, alias="PrivateIpAddress")
    public_ip_address: Optional[str] = Field(None, alias="PublicIpAddress")
    state: Optional[EC2InstanceState] = Field(None, alias="State")
    subnet_id: Optional[str] = Field(None, alias="SubnetId")
    vpc_id: Optional[str] = Field(None, alias="VpcId")
    iam_instance_profile_arn: Optional[str] = Field(None, alias="IamInstanceProfileArn") # Ajustado para corresponder ao schema do collector
    security_groups: Optional[List[Dict[str, str]]] = Field(None, alias="SecurityGroups")
    tags: Optional[List[Dict[str, str]]] = Field(None, alias="Tags")
    region: str # Adicionado no collector
    error_details: Optional[str] = None
    class Config:
        populate_by_name = True


# --- IAM Schemas ---
class IAMUserAccessKeyMetadataInput(BaseModel):
    access_key_id: str = Field(alias="AccessKeyId")
    status: str = Field(alias="Status")
    create_date: datetime = Field(alias="CreateDate")
    last_used_date: Optional[datetime] = None
    class Config:
        populate_by_name = True

class IAMUserMFADeviceInput(BaseModel):
    user_name: str = Field(alias="UserName") # No collector, UserName é adicionado ao montar o objeto MFADevice
    serial_number: str = Field(alias="SerialNumber")
    enable_date: datetime = Field(alias="EnableDate")
    class Config:
        populate_by_name = True

class IAMPolicyAttachmentInput(BaseModel):
    policy_arn: Optional[str] = Field(None, alias="PolicyArn")
    policy_name: Optional[str] = Field(None, alias="PolicyName")
    class Config:
        populate_by_name = True

class IAMUserPolicyInput(BaseModel): # Para políticas inline
    policy_name: str = Field(alias="PolicyName")
    policy_document: Optional[Dict[str, Any]] = None
    class Config:
        populate_by_name = True

class IAMUserDataInput(BaseModel):
    user_id: str = Field(alias="UserId")
    user_name: str = Field(alias="UserName")
    arn: str = Field(alias="Arn")
    create_date: datetime = Field(alias="CreateDate")
    password_last_used: Optional[datetime] = Field(None, alias="PasswordLastUsed")
    attached_policies: Optional[List[IAMPolicyAttachmentInput]] = None
    inline_policies: Optional[List[IAMUserPolicyInput]] = None
    mfa_devices: Optional[List[IAMUserMFADeviceInput]] = None
    access_keys: Optional[List[IAMUserAccessKeyMetadataInput]] = None
    tags: Optional[List[Dict[str, str]]] = Field(None, alias="Tags")
    error_details: Optional[str] = None
    class Config:
        populate_by_name = True

# Adicionar IAMRoleDataInput e IAMPolicyDataInput similarmente se forem ser analisados.
# Por agora, vamos focar nas políticas acima.


# Schema genérico para a requisição de análise
# O campo 'data' pode conter uma lista de qualquer um dos tipos de dados acima.
# O controller precisará fazer o parsing correto baseado no valor de 'service'.
SupportedDataTypes = Union[
    List[S3BucketDataInput],
    List[EC2InstanceDataInput],
    List[EC2SecurityGroupDataInput],
    List[IAMUserDataInput]
    # Adicionar List[IAMRoleDataInput], List[IAMPolicyDataInput] quando prontos
]

class AnalysisRequest(BaseModel):
    provider: str = Field(default="aws", description="Cloud provider name, e.g., 'aws'.")
    service: str = Field(description="Service name, e.g., 's3', 'ec2_instances', 'iam_users'.")
    # data: List[Dict[str, Any]] # Alterado para ser mais específico com Union
    data: SupportedDataTypes
    account_id: Optional[str] = Field(None, description="AWS Account ID, if available.")
    # region: Optional[str] = Field(None, description="AWS Region, if the data is region-specific and not included in each item.")
    # No nosso caso, EC2InstanceDataInput já tem 'region'. S3 tem 'region'. IAM é global.
    # Este campo 'region' de nível superior pode não ser necessário se os dados já forem contextualizados.

    class Config:
        # Exemplo para Pydantic v2, se necessário para validação de discriminador
        # model_config = {
        #     "discriminator": "service",
        # }
        pass
