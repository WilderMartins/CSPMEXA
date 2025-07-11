from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# Este schema deve espelhar GKEClusterData do collector_service
# e GKEClusterDataInput do policy_engine_service.

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
    class Config: populate_by_name = True; extra = 'ignore'

class GKENodePoolManagement(BaseModel):
    auto_upgrade: Optional[bool] = Field(None, alias="autoUpgrade")
    auto_repair: Optional[bool] = Field(None, alias="autoRepair")
    class Config: populate_by_name = True; extra = 'ignore'

class GKENodePool(BaseModel):
    name: str
    version: Optional[str] = None
    initial_node_count: Optional[int] = Field(None, alias="initialNodeCount")
    autoscaling: Optional[GKENodePoolAutoscaling] = None
    status: Optional[str] = None
    config: Optional[GKENodeConfig] = None
    management: Optional[GKENodePoolManagement] = None
    class Config: populate_by_name = True; extra = 'ignore'

class GKENetworkPolicy(BaseModel):
    provider: Optional[str] = None
    enabled: Optional[bool] = None
    class Config: extra = 'ignore'

class GKEIPAllocationPolicy(BaseModel):
    use_ip_aliases: Optional[bool] = Field(None, alias="useIpAliases")
    class Config: populate_by_name = True; extra = 'ignore'

class GKELoggingConfig(BaseModel):
    enable_components: Optional[List[str]] = Field(None, alias="enableComponents")
    class Config: populate_by_name = True; extra = 'ignore'

class GKEMonitoringConfig(BaseModel):
    enable_components: Optional[List[str]] = Field(None, alias="enableComponents")
    class Config: populate_by_name = True; extra = 'ignore'

class GKEAddonsConfig(BaseModel):
    http_load_balancing: Optional[Dict[str, bool]] = Field(None, alias="httpLoadBalancing")
    horizontal_pod_autoscaling: Optional[Dict[str, bool]] = Field(None, alias="horizontalPodAutoscaling")
    network_policy_config: Optional[Dict[str, bool]] = Field(None, alias="networkPolicyConfig")
    class Config: populate_by_name = True; extra = 'ignore'

class GKEPrivateClusterConfig(BaseModel):
    enable_private_nodes: Optional[bool] = Field(None, alias="enablePrivateNodes")
    enable_private_endpoint: Optional[bool] = Field(None, alias="enablePrivateEndpoint")
    master_ipv4_cidr_block: Optional[str] = Field(None, alias="masterIpv4CidrBlock")
    private_endpoint: Optional[str] = Field(None, alias="privateEndpoint")
    public_endpoint: Optional[str] = Field(None, alias="publicEndpoint")
    class Config: populate_by_name = True; extra = 'ignore'

class GKEMaintenancePolicy(BaseModel):
    window: Optional[Dict[str, Any]] = None
    resource_version: Optional[str] = Field(None, alias="resourceVersion")
    class Config: populate_by_name = True; extra = 'ignore'

class GKEAutopilot(BaseModel):
    enabled: Optional[bool] = None
    class Config: extra = 'ignore'

class GKEClusterData(BaseModel): # Para o Gateway, este é o schema de resposta da coleta
    name: str
    description: Optional[str] = None
    initial_node_count: Optional[int] = Field(None, alias="initialNodeCount")
    node_pools: List[GKENodePool] = Field(default_factory=list, alias="nodePools")
    locations: Optional[List[str]] = None
    location: Optional[str] = None
    endpoint: Optional[str] = None
    initial_cluster_version: Optional[str] = Field(None, alias="initialClusterVersion")
    current_master_version: Optional[str] = Field(None, alias="currentMasterVersion")
    current_node_version: Optional[str] = Field(None, alias="currentNodeVersion")
    create_time: Optional[datetime] = Field(None, alias="createTime")
    status: Optional[str] = None
    status_message: Optional[str] = Field(None, alias="statusMessage")
    node_ipv4_cidr_size: Optional[int] = Field(None, alias="nodeIpv4CidrSize")
    services_ipv4_cidr: Optional[str] = Field(None, alias="servicesIpv4Cidr")
    instance_group_urls: Optional[List[str]] = Field(default_factory=list, alias="instanceGroupUrls")
    self_link: Optional[str] = Field(None, alias="selfLink")
    zone: Optional[str] = None

    network: Optional[str] = None
    subnetwork: Optional[str] = None
    private_cluster_config: Optional[GKEPrivateClusterConfig] = Field(None, alias="privateClusterConfig")
    master_authorized_networks_config: Optional[Dict[str, Any]] = Field(None, alias="masterAuthorizedNetworksConfig")
    ip_allocation_policy: Optional[GKEIPAllocationPolicy] = Field(None, alias="ipAllocationPolicy")
    network_policy: Optional[GKENetworkPolicy] = Field(None, alias="networkPolicy")

    addons_config: Optional[GKEAddonsConfig] = Field(None, alias="addonsConfig")

    logging_service: Optional[str] = Field(None, alias="loggingService")
    monitoring_service: Optional[str] = Field(None, alias="monitoringService")
    logging_config: Optional[GKELoggingConfig] = Field(None, alias="loggingConfig")
    monitoring_config: Optional[GKEMonitoringConfig] = Field(None, alias="monitoringConfig")

    maintenance_policy: Optional[GKEMaintenancePolicy] = Field(None, alias="maintenancePolicy")
    autopilot: Optional[GKEAutopilot] = None

    project_id: str
    is_autopilot: Optional[bool] = None
    has_public_endpoint: Optional[bool] = None
    network_policy_enabled: Optional[bool] = None
    node_auto_upgrade_enabled_default: Optional[bool] = None

    error_details: Optional[str] = None

    class Config:
        populate_by_name = True
        extra = 'ignore'
        from_attributes = True # Pydantic V2, or orm_mode = True for V1
        arbitrary_types_allowed = True
```
