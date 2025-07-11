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
    Optional['GCPProjectIAMPolicyDataInput'], # IAM de projeto é um objeto único, não uma lista

    # Tipos de Dados Huawei Cloud
    List['HuaweiOBSBucketDataInput'],
    List['HuaweiECSServerDataInput'],
    List['HuaweiVPCSecurityGroupInput'],
    List['HuaweiIAMUserDataInput'],

    # Tipos de Dados Azure
    List['AzureVirtualMachineDataInput'],
    List['AzureStorageAccountDataInput'],

    # Tipos de Dados Google Workspace (a serem adicionados)
    List['GoogleWorkspaceUserDataInput']
    # Adicionar outros tipos do Workspace (Drive, Gmail) quando os coletores estiverem prontos
]

# --- Google Workspace Schemas (espelham collector_service/app/schemas/google_workspace_*.py) ---

class GoogleWorkspaceUserNameInput(BaseModel):
    given_name: Optional[str] = Field(None, alias="givenName")
    family_name: Optional[str] = Field(None, alias="familyName")
    full_name: Optional[str] = Field(None, alias="fullName")
    class Config: populate_by_name = True; extra = 'ignore'

class GoogleWorkspaceUserEmailInput(BaseModel): # Adicionado Input no nome para consistência
    address: Optional[str] = None # EmailStr removido para input, validação pode ser mais flexível aqui
    primary: Optional[bool] = None
    class Config: extra = 'ignore'

class GoogleWorkspaceUserDataInput(BaseModel):
    id: str
    primary_email: str = Field(alias="primaryEmail") # EmailStr removido
    name: GoogleWorkspaceUserNameInput # Usar o Input schema
    is_admin: bool = Field(False, alias="isAdmin")
    is_delegated_admin: Optional[bool] = Field(None, alias="isDelegatedAdmin")
    last_login_time: Optional[datetime] = Field(None, alias="lastLoginTime")
    creation_time: Optional[datetime] = Field(None, alias="creationTime")
    suspended: Optional[bool] = False
    archived: Optional[bool] = False
    org_unit_path: Optional[str] = Field(None, alias="orgUnitPath")
    is_enrolled_in_2sv: bool = Field(False, alias="isEnrolledIn2Sv")
    emails: Optional[List[GoogleWorkspaceUserEmailInput]] = None
    error_details: Optional[str] = None
    class Config: populate_by_name = True; extra = 'ignore'


# --- Azure Schemas (espelham collector_service/app/schemas/azure_*.py) ---

# Azure Compute (VMs)
class AzureNetworkSecurityGroupInfoInput(BaseModel):
    id: str
    name: Optional[str] = None
    resource_group: Optional[str] = None
    class Config: extra = 'ignore'; populate_by_name = True

class AzurePublicIPAddressInput(BaseModel):
    id: str
    name: Optional[str] = None
    ip_address: Optional[str] = None
    resource_group: Optional[str] = None
    class Config: extra = 'ignore'; populate_by_name = True

class AzureIPConfigurationInput(BaseModel):
    name: Optional[str] = None
    private_ip_address: Optional[str] = None
    public_ip_address_details: Optional[AzurePublicIPAddressInput] = Field(None, alias="publicIpAddress")
    class Config: extra = 'ignore'; populate_by_name = True


class AzureNetworkInterfaceInput(BaseModel):
    id: str
    name: Optional[str] = None
    resource_group: Optional[str] = None
    ip_configurations: List[AzureIPConfigurationInput] = Field(default_factory=list, alias="ipConfigurations")
    network_security_group: Optional[AzureNetworkSecurityGroupInfoInput] = Field(None, alias="networkSecurityGroup")
    class Config: extra = 'ignore'; populate_by_name = True


class AzureVirtualMachineDataInput(BaseModel):
    id: str
    name: str
    location: str
    resource_group_name: Optional[str] = None
    size: Optional[str] = None
    os_type: Optional[str] = None
    power_state: Optional[str] = None
    tags: Optional[Dict[str, str]] = None
    network_interfaces: List[AzureNetworkInterfaceInput] = Field(default_factory=list)
    error_details: Optional[str] = None
    class Config: extra = 'ignore'


# Azure Storage
class AzureBlobContainerDataInput(BaseModel):
    id: str
    name: Optional[str] = None
    public_access: Optional[str] = None
    last_modified_time: Optional[datetime] = Field(None, alias="lastModifiedTime")
    class Config: populate_by_name = True; extra = 'ignore'


class AzureStorageAccountDataInput(BaseModel):
    id: str
    name: str
    location: str
    resource_group_name: Optional[str] = None
    kind: Optional[str] = None
    sku_name: Optional[str] = None
    allow_blob_public_access: Optional[bool] = None
    minimum_tls_version: Optional[str] = None
    supports_https_traffic_only: Optional[bool] = None
    blob_containers: List[AzureBlobContainerDataInput] = Field(default_factory=list)
    error_details: Optional[str] = None
    class Config: extra = 'ignore'


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

# --- Huawei Cloud Schemas (devem espelhar os do collector_service/app/schemas/huawei_*.py) ---

# Huawei OBS
class HuaweiOBSBucketPolicyStatementInput(BaseModel):
    sid: Optional[str] = Field(None, alias="Sid")
    effect: str = Field(alias="Effect")
    principal: Dict[str, Any] = Field(alias="Principal")
    action: List[str] = Field(alias="Action")
    resource: List[str] = Field(alias="Resource")
    condition: Optional[Dict[str, Dict[str, List[str]]]] = Field(None, alias="Condition")
    class Config: populate_by_name = True

class HuaweiOBSBucketPolicyInput(BaseModel):
    version: Optional[str] = Field(None, alias="Version")
    statement: List[HuaweiOBSBucketPolicyStatementInput] = Field(alias="Statement")
    class Config: populate_by_name = True

class HuaweiOBSGranteeInput(BaseModel):
    id: Optional[str] = Field(None, alias="ID")
    uri: Optional[str] = Field(None, alias="URI")
    class Config: populate_by_name = True

class HuaweiOBSGrantInput(BaseModel):
    grantee: HuaweiOBSGranteeInput = Field(alias="Grantee")
    permission: str = Field(alias="Permission")
    class Config: populate_by_name = True

class HuaweiOBSOwnerInput(BaseModel):
    id: str = Field(alias="ID")
    class Config: populate_by_name = True

class HuaweiOBSBucketACLInput(BaseModel):
    owner: HuaweiOBSOwnerInput = Field(alias="Owner")
    grants: List[HuaweiOBSGrantInput] = Field([], alias="Grant")
    class Config: populate_by_name = True

class HuaweiOBSBucketVersioningInput(BaseModel):
    status: Optional[str] = None

class HuaweiOBSBucketLoggingInput(BaseModel):
    enabled: bool = False
    target_bucket: Optional[str] = None
    target_prefix: Optional[str] = None

class HuaweiOBSBucketDataInput(BaseModel):
    name: str
    creation_date: Optional[datetime] = None
    location: Optional[str] = None
    storage_class: Optional[str] = None
    bucket_policy: Optional[HuaweiOBSBucketPolicyInput] = None
    acl: Optional[HuaweiOBSBucketACLInput] = None
    versioning: Optional[HuaweiOBSBucketVersioningInput] = None
    logging: Optional[HuaweiOBSBucketLoggingInput] = None
    is_public_by_policy: Optional[bool] = None
    public_policy_details: List[str] = []
    is_public_by_acl: Optional[bool] = None
    public_acl_details: List[str] = []
    error_details: Optional[str] = None

# Huawei ECS & VPC (Security Groups)
class HuaweiECSAddressInput(BaseModel):
    version: Optional[int] = None
    addr: Optional[str] = None
    mac_addr: Optional[str] = Field(None, alias="OS-EXT-IPS-MAC:mac_addr")
    type: Optional[str] = Field(None, alias="OS-EXT-IPS:type")
    class Config: populate_by_name = True

class HuaweiECSImageInput(BaseModel):
    id: str

class HuaweiECSFlavorInput(BaseModel):
    id: str
    name: Optional[str] = None

class HuaweiECSServerMetadataInput(BaseModel):
    custom_metadata: Optional[Dict[str, str]] = None

class HuaweiECSServerDataInput(BaseModel):
    id: str
    name: str
    status: str
    created: datetime
    updated: Optional[datetime] = None
    user_id: Optional[str] = Field(None, alias="user_id")
    image: Optional[HuaweiECSImageInput] = None
    flavor: HuaweiECSFlavorInput
    addresses: Optional[Dict[str, List[HuaweiECSAddressInput]]] = None
    key_name: Optional[str] = Field(None, alias="key_name")
    availability_zone: Optional[str] = Field(None, alias="OS-EXT-AZ:availability_zone")
    host_id: Optional[str] = Field(None, alias="OS-EXT-SRV-ATTR:host")
    hypervisor_hostname: Optional[str] = Field(None, alias="OS-EXT-SRV-ATTR:hypervisor_hostname")
    security_groups: Optional[List[Dict[str, str]]] = None
    volumes_attached: Optional[List[Dict[str, str]]] = Field(None, alias="os-extended-volumes:volumes_attached")
    metadata: Optional[HuaweiECSServerMetadataInput] = None
    project_id: str
    region_id: str
    public_ips: List[str] = []
    private_ips: List[str] = []
    error_details: Optional[str] = None
    class Config: populate_by_name = True

class HuaweiVPCSecurityGroupRuleInput(BaseModel):
    id: str
    description: Optional[str] = None
    security_group_id: str
    direction: str
    ethertype: Optional[str] = None
    protocol: Optional[str] = None
    port_range_min: Optional[int] = Field(None, alias="port_range_min")
    port_range_max: Optional[int] = Field(None, alias="port_range_max")
    remote_ip_prefix: Optional[str] = Field(None, alias="remote_ip_prefix")
    remote_group_id: Optional[str] = Field(None, alias="remote_group_id")
    class Config: populate_by_name = True

class HuaweiVPCSecurityGroupInput(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    project_id_from_collector: str = Field(alias="project_id")
    security_group_rules: List[HuaweiVPCSecurityGroupRuleInput] = []
    region_id: str
    error_details: Optional[str] = None
    class Config: populate_by_name = True

# Huawei IAM
class HuaweiIAMUserLoginProtectInput(BaseModel):
    enabled: bool
    verification_method: Optional[str] = None

class HuaweiIAMUserAccessKeyInput(BaseModel):
    access_key: str = Field(alias="access")
    status: str
    create_time: Optional[datetime] = Field(None, alias="create_time_format")
    description: Optional[str] = None
    class Config: populate_by_name = True

class HuaweiIAMUserMfaDeviceInput(BaseModel):
    serial_number: str
    type: str

class HuaweiIAMUserDataInput(BaseModel):
    id: str
    name: str
    domain_id: str
    enabled: bool
    email: Optional[str] = None
    phone: Optional[str] = Field(None, alias="areacode_mobile")
    login_protect: Optional[HuaweiIAMUserLoginProtectInput] = Field(None, alias="login_protect")
    access_keys: Optional[List[HuaweiIAMUserAccessKeyInput]] = None
    mfa_devices: Optional[List[HuaweiIAMUserMfaDeviceInput]] = None
    error_details: Optional[str] = None
    class Config: populate_by_name = True


class AnalysisRequest(BaseModel):
    provider: str = Field(description="Cloud provider name, e.g., 'aws', 'gcp', 'huawei'.")
    service: str = Field(description="Service name, e.g., 's3', 'ec2_instances', 'gcp_storage_buckets', 'huawei_obs_buckets'.")
    data: SupportedDataTypes
    account_id: Optional[str] = Field(None, description="Cloud account ID (e.g., AWS Account ID, GCP Project ID, Huawei Domain/Project ID).")
    # Para Huawei, account_id pode ser o Domain ID ou Project ID dependendo do serviço.

    class Config:
        pass
