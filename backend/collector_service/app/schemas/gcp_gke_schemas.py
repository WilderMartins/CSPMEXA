from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# Sub-schemas para GKE Cluster
class GKENodePoolAutoscaling(BaseModel):
    enabled: Optional[bool] = None
    min_node_count: Optional[int] = Field(None, alias="minNodeCount")
    max_node_count: Optional[int] = Field(None, alias="maxNodeCount")
    class Config: populate_by_name = True; extra = 'ignore'

class GKENodeConfig(BaseModel):
    machine_type: Optional[str] = Field(None, alias="machineType")
    disk_size_gb: Optional[int] = Field(None, alias="diskSizeGb")
    oauth_scopes: Optional[List[str]] = Field(None, alias="oauthScopes")
    service_account: Optional[str] = Field(None, alias="serviceAccount")
    # Adicionar mais campos se necessário (imageType, labels, taints, etc.)
    class Config: populate_by_name = True; extra = 'ignore'

class GKENodePool(BaseModel):
    name: str
    version: Optional[str] = None
    initial_node_count: Optional[int] = Field(None, alias="initialNodeCount")
    autoscaling: Optional[GKENodePoolAutoscaling] = None
    status: Optional[str] = None
    config: Optional[GKENodeConfig] = None
    # Adicionar locations, networkConfig, management, etc.
    class Config: populate_by_name = True; extra = 'ignore'

class GKEMasterAuth(BaseModel):
    client_certificate: Optional[str] = Field(None, alias="clientCertificate")
    client_key: Optional[str] = Field(None, alias="clientKey") # Sensível, verificar se realmente precisamos coletar
    cluster_ca_certificate: Optional[str] = Field(None, alias="clusterCaCertificate")
    username: Optional[str] = None
    password: Optional[str] = None # Sensível
    class Config: populate_by_name = True; extra = 'ignore'

class GKENetworkPolicy(BaseModel):
    provider: Optional[str] = None # e.g., "CALICO" or "PROVIDER_UNSPECIFIED"
    enabled: Optional[bool] = None
    class Config: extra = 'ignore'

class GKEIPAllocationPolicy(BaseModel):
    use_ip_aliases: Optional[bool] = Field(None, alias="useIpAliases")
    # Adicionar outros campos como clusterIpv4CidrBlock, servicesIpv4CidrBlock
    class Config: populate_by_name = True; extra = 'ignore'

class GKELoggingConfig(BaseModel):
    enable_components: Optional[List[str]] = Field(None, alias="enableComponents") # e.g., ["SYSTEM_COMPONENTS", "WORKLOADS"]
    class Config: populate_by_name = True; extra = 'ignore'

class GKEMonitoringConfig(BaseModel):
    enable_components: Optional[List[str]] = Field(None, alias="enableComponents") # e.g., ["SYSTEM_COMPONENTS"]
    class Config: populate_by_name = True; extra = 'ignore'

class GKEDataplaneProvider(BaseModel): # Para Dataplane V2
    enable_dataplane_v2: Optional[bool] = Field(None, alias="enableDataplaneV2")
    class Config: populate_by_name = True; extra = 'ignore'

class GKEAddonsConfig(BaseModel):
    http_load_balancing: Optional[Dict[str, bool]] = Field(None, alias="httpLoadBalancing")
    horizontal_pod_autoscaling: Optional[Dict[str, bool]] = Field(None, alias="horizontalPodAutoscaling")
    network_policy_config: Optional[Dict[str, bool]] = Field(None, alias="networkPolicyConfig") # Se NetworkPolicy está habilitada nos addons
    # Adicionar outros addons como Istio, CloudRun, etc.
    class Config: populate_by_name = True; extra = 'ignore'

class GKEPrivateClusterConfig(BaseModel):
    enable_private_nodes: Optional[bool] = Field(None, alias="enablePrivateNodes")
    enable_private_endpoint: Optional[bool] = Field(None, alias="enablePrivateEndpoint")
    master_ipv4_cidr_block: Optional[str] = Field(None, alias="masterIpv4CidrBlock")
    private_endpoint: Optional[str] = Field(None, alias="privateEndpoint") # Read-only
    public_endpoint: Optional[str] = Field(None, alias="publicEndpoint")   # Read-only
    class Config: populate_by_name = True; extra = 'ignore'

class GKEMaintenancePolicy(BaseModel):
    window: Optional[Dict[str, Any]] = None # Pode ser complexo, ex: DailyMaintenanceWindow
    resource_version: Optional[str] = Field(None, alias="resourceVersion")
    class Config: populate_by_name = True; extra = 'ignore'

class GKEAutopilot(BaseModel):
    enabled: Optional[bool] = None
    class Config: extra = 'ignore'

class GKENodePoolAutoUpgrade(BaseModel): # Para NodePool.management.autoUpgrade
    enabled: Optional[bool] = True
    class Config: extra = 'ignore'

class GKENodePoolManagement(BaseModel):
    auto_upgrade: Optional[bool] = Field(None, alias="autoUpgrade") # Corrigido para ser booleano
    auto_repair: Optional[bool] = Field(None, alias="autoRepair")
    class Config: populate_by_name = True; extra = 'ignore'


# Schema principal para GKE Cluster
class GKEClusterData(BaseModel):
    name: str
    description: Optional[str] = None
    initial_node_count: Optional[int] = Field(None, alias="initialNodeCount") # Pode estar em defaultNodePool
    node_pools: List[GKENodePool] = Field(default_factory=list, alias="nodePools")
    locations: Optional[List[str]] = None # Zonas/regiões onde o cluster está
    location: Optional[str] = None # Location do cluster (pode ser regional ou zonal)
    endpoint: Optional[str] = None # Endpoint do master (pode ser público ou privado)
    initial_cluster_version: Optional[str] = Field(None, alias="initialClusterVersion")
    current_master_version: Optional[str] = Field(None, alias="currentMasterVersion")
    current_node_version: Optional[str] = Field(None, alias="currentNodeVersion") # Versão dos nós (pode variar por nodepool)
    create_time: Optional[datetime] = Field(None, alias="createTime")
    status: Optional[str] = None # e.g., "RUNNING", "PROVISIONING"
    status_message: Optional[str] = Field(None, alias="statusMessage")
    node_ipv4_cidr_size: Optional[int] = Field(None, alias="nodeIpv4CidrSize")
    services_ipv4_cidr: Optional[str] = Field(None, alias="servicesIpv4Cidr")
    instance_group_urls: Optional[List[str]] = Field(default_factory=list, alias="instanceGroupUrls")
    self_link: Optional[str] = Field(None, alias="selfLink")
    zone: Optional[str] = None # Deprecated in favor of location. Se for zonal, location terá a zona.

    # Configurações de segurança e rede
    network: Optional[str] = None # Nome da rede VPC
    subnetwork: Optional[str] = None # Nome da subrede VPC
    private_cluster_config: Optional[GKEPrivateClusterConfig] = Field(None, alias="privateClusterConfig")
    master_authorized_networks_config: Optional[Dict[str, Any]] = Field(None, alias="masterAuthorizedNetworksConfig")
    ip_allocation_policy: Optional[GKEIPAllocationPolicy] = Field(None, alias="ipAllocationPolicy")
    network_policy: Optional[GKENetworkPolicy] = Field(None, alias="networkPolicy") # Política de rede (Calico)

    # Addons
    addons_config: Optional[GKEAddonsConfig] = Field(None, alias="addonsConfig")

    # Logging e Monitoring
    logging_service: Optional[str] = Field(None, alias="loggingService") # e.g., "logging.googleapis.com/kubernetes"
    monitoring_service: Optional[str] = Field(None, alias="monitoringService") # e.g., "monitoring.googleapis.com/kubernetes"
    logging_config: Optional[GKELoggingConfig] = Field(None, alias="loggingConfig")
    monitoring_config: Optional[GKEMonitoringConfig] = Field(None, alias="monitoringConfig")

    # Outras configs
    maintenance_policy: Optional[GKEMaintenancePolicy] = Field(None, alias="maintenancePolicy")
    autopilot: Optional[GKEAutopilot] = None # Configuração do Autopilot

    # Campos extraídos/adicionados pelo collector
    project_id: str
    # location: str # Já definido acima, será a região ou zona do cluster
    is_autopilot: Optional[bool] = None # Derivado de autopilot.enabled
    has_public_endpoint: Optional[bool] = None # Derivado de privateClusterConfig
    network_policy_enabled: Optional[bool] = None # Derivado de networkPolicy.enabled ou addonsConfig.networkPolicyConfig.disabled
    node_auto_upgrade_enabled_default: Optional[bool] = None # Derivado de nodePools[0].management.autoUpgrade se existir

    error_details: Optional[str] = None

    class Config:
        populate_by_name = True # Permite usar alias nos campos
        extra = 'ignore' # Ignorar campos extras vindos da API
        arbitrary_types_allowed = True # Para datetime
