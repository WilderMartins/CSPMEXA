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
    List[IAMUserDataInput],
    # Adicionar List[IAMRoleDataInput], List[IAMPolicyDataInput] quando prontos para AWS

    # Tipos de Dados GCP
    List['GCPStorageBucketDataInput'],
    List['GCPComputeInstanceDataInput'],
    List['GCPFirewallDataInput'],
    Optional['GCPProjectIAMPolicyDataInput'] # IAM de projeto é um objeto único, não uma lista
]

# --- GCP Schemas (devem espelhar os do collector_service/app/schemas/gcp_*.py) ---

# GCP Storage
class GCPBucketIAMBindingInput(BaseModel):
    role: str
    members: List[str]
    condition: Optional[Dict[str, Any]] = None

class GCPBucketIAMPolicyInput(BaseModel):
    version: Optional[int] = None
    bindings: List[GCPBucketIAMBindingInput] = []
    etag: Optional[str] = None

class GCPBucketVersioningInput(BaseModel):
    enabled: bool

class GCPBucketLoggingInput(BaseModel):
    log_bucket: Optional[str] = None
    log_object_prefix: Optional[str] = None

class GCPBucketWebsiteInput(BaseModel):
    main_page_suffix: Optional[str] = None
    not_found_page: Optional[str] = None

class GCPBucketRetentionPolicyInput(BaseModel):
    retention_period: Optional[int] = None
    effective_time: Optional[datetime] = None
    is_locked: Optional[bool] = None

class GCPStorageBucketDataInput(BaseModel):
    id: str
    name: str
    project_number: Optional[str] = None
    location: str
    storage_class: str = Field(alias="storageClass")
    time_created: datetime = Field(alias="timeCreated")
    updated: datetime
    iam_policy: Optional[GCPBucketIAMPolicyInput] = None
    versioning: Optional[GCPBucketVersioningInput] = None
    logging: Optional[GCPBucketLoggingInput] = None
    website_configuration: Optional[GCPBucketWebsiteInput] = Field(None, alias="website")
    retention_policy: Optional[GCPBucketRetentionPolicyInput] = Field(None, alias="retentionPolicy")
    is_public_by_iam: Optional[bool] = None
    public_iam_details: List[str] = []
    labels: Optional[Dict[str, str]] = None
    error_details: Optional[str] = None
    class Config:
        populate_by_name = True

# GCP Compute Instances
class GCPComputeNetworkInterfaceAccessConfigInput(BaseModel):
    type: Optional[str] = None
    name: Optional[str] = None
    nat_ip: Optional[str] = Field(None, alias="natIP")
    class Config:
        populate_by_name = True

class GCPComputeNetworkInterfaceInput(BaseModel):
    name: Optional[str] = None
    network: Optional[str] = None
    subnetwork: Optional[str] = None
    network_ip: Optional[str] = Field(None, alias="networkIP")
    access_configs: Optional[List[GCPComputeNetworkInterfaceAccessConfigInput]] = Field(None, alias="accessConfigs")
    class Config:
        populate_by_name = True

class GCPComputeAttachedDiskInitializeParamsInput(BaseModel):
    disk_name: Optional[str] = Field(None, alias="diskName")
    disk_size_gb: Optional[str] = Field(None, alias="diskSizeGb")
    disk_type: Optional[str] = Field(None, alias="diskType")
    source_image: Optional[str] = Field(None, alias="sourceImage")
    class Config:
        populate_by_name = True

class GCPComputeAttachedDiskInput(BaseModel):
    type: Optional[str] = None
    mode: Optional[str] = None
    source: Optional[str] = None
    device_name: Optional[str] = Field(None, alias="deviceName")
    boot: Optional[bool] = None
    auto_delete: Optional[bool] = Field(None, alias="autoDelete")
    initialize_params: Optional[GCPComputeAttachedDiskInitializeParamsInput] = Field(None, alias="initializeParams")
    class Config:
        populate_by_name = True

class GCPComputeServiceAccountInput(BaseModel):
    email: Optional[str] = None
    scopes: Optional[List[str]] = None

class GCPComputeSchedulingInput(BaseModel):
    on_host_maintenance: Optional[str] = Field(None, alias="onHostMaintenance")
    automatic_restart: Optional[bool] = Field(None, alias="automaticRestart")
    preemptible: Optional[bool] = None
    class Config:
        populate_by_name = True

class GCPComputeInstanceDataInput(BaseModel):
    id: str
    name: str
    zone: str # No collector é a URL completa, aqui esperamos o nome extraído.
    machine_type: str = Field(alias="machineType") # No collector é a URL, aqui esperamos o nome extraído.
    status: str
    creation_timestamp: datetime = Field(alias="creationTimestamp")
    can_ip_forward: Optional[bool] = Field(None, alias="canIpForward")
    deletion_protection: Optional[bool] = Field(None, alias="deletionProtection")
    network_interfaces: Optional[List[GCPComputeNetworkInterfaceInput]] = Field(None, alias="networkInterfaces")
    disks: Optional[List[GCPComputeAttachedDiskInput]] = None
    service_accounts: Optional[List[GCPComputeServiceAccountInput]] = Field(None, alias="serviceAccounts")
    scheduling: Optional[GCPComputeSchedulingInput] = None
    tags_items: Optional[List[str]] = None # No collector é tags_items
    labels: Optional[Dict[str, str]] = None
    project_id: str
    # Campos que o collector extrai e adiciona:
    extracted_zone: str
    extracted_machine_type: str
    public_ip_addresses: List[str] = []
    private_ip_addresses: List[str] = []
    error_details: Optional[str] = None
    class Config:
        populate_by_name = True

# GCP Compute Firewalls
class GCPFirewallAllowedRuleInput(BaseModel):
    ip_protocol: str = Field(alias="IPProtocol")
    ports: Optional[List[str]] = None
    class Config:
        populate_by_name = True

class GCPFirewallDeniedRuleInput(BaseModel):
    ip_protocol: str = Field(alias="IPProtocol")
    ports: Optional[List[str]] = None
    class Config:
        populate_by_name = True

class GCPFirewallLogConfigInput(BaseModel):
    enable: bool
    metadata: Optional[str] = None

class GCPFirewallDataInput(BaseModel):
    id: str
    name: str
    network: str # No collector é a URL, aqui esperamos o nome extraído.
    priority: int
    direction: str
    allowed: Optional[List[GCPFirewallAllowedRuleInput]] = None
    denied: Optional[List[GCPFirewallDeniedRuleInput]] = None
    source_ranges: Optional[List[str]] = Field(None, alias="sourceRanges")
    destination_ranges: Optional[List[str]] = Field(None, alias="destinationRanges")
    source_tags: Optional[List[str]] = Field(None, alias="sourceTags")
    target_tags: Optional[List[str]] = Field(None, alias="targetTags")
    disabled: bool
    log_config: Optional[GCPFirewallLogConfigInput] = Field(None, alias="logConfig")
    creation_timestamp: datetime = Field(alias="creationTimestamp")
    project_id: str
    # Campo que o collector extrai:
    extracted_network_name: str
    error_details: Optional[str] = None
    class Config:
        populate_by_name = True

# GCP Project IAM Policy
class GCPProjectIAMPolicyDataInput(BaseModel): # Note: Este não é uma Lista no Union, é Optional[GCPProjectIAMPolicyDataInput]
    project_id: str
    iam_policy: GCPBucketIAMPolicyInput # Reutilizando o schema de política de bucket para a estrutura geral
    has_external_members_with_primitive_roles: Optional[bool] = None
    external_primitive_role_details: List[str] = []
    error_details: Optional[str] = None


class AnalysisRequest(BaseModel):
    provider: str = Field(description="Cloud provider name, e.g., 'aws', 'gcp'.")
    service: str = Field(description="Service name, e.g., 's3', 'ec2_instances', 'gcp_storage_buckets'.")
    data: SupportedDataTypes
    account_id: Optional[str] = Field(None, description="Cloud account ID (e.g., AWS Account ID, GCP Project ID/Number).")
    # Para GCP, 'account_id' pode ser o Project ID. Os dados de recurso já devem ter project_id neles.

    class Config:
        pass
