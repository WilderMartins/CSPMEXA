from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# Este schema espelha GKEClusterData do collector_service
# e serve como input para o policy_engine.

class GKENodePoolAutoscalingInput(BaseModel):
    enabled: Optional[bool] = None
    min_node_count: Optional[int] = Field(None, alias="minNodeCount")
    max_node_count: Optional[int] = Field(None, alias="maxNodeCount")
    class Config: populate_by_name = True; extra = 'ignore'

class GKENodeConfigInput(BaseModel):
    machine_type: Optional[str] = Field(None, alias="machineType")
    disk_size_gb: Optional[int] = Field(None, alias="diskSizeGb")
    oauth_scopes: Optional[List[str]] = Field(None, alias="oauthScopes")
    service_account: Optional[str] = Field(None, alias="serviceAccount")
    class Config: populate_by_name = True; extra = 'ignore'

class GKENodePoolManagementInput(BaseModel):
    auto_upgrade: Optional[bool] = Field(None, alias="autoUpgrade")
    auto_repair: Optional[bool] = Field(None, alias="autoRepair")
    class Config: populate_by_name = True; extra = 'ignore'

class GKENodePoolInput(BaseModel):
    name: str
    version: Optional[str] = None
    initial_node_count: Optional[int] = Field(None, alias="initialNodeCount")
    autoscaling: Optional[GKENodePoolAutoscalingInput] = None
    status: Optional[str] = None
    config: Optional[GKENodeConfigInput] = None
    management: Optional[GKENodePoolManagementInput] = None
    class Config: populate_by_name = True; extra = 'ignore'

class GKENetworkPolicyInput(BaseModel):
    provider: Optional[str] = None
    enabled: Optional[bool] = None
    class Config: extra = 'ignore'

class GKEIPAllocationPolicyInput(BaseModel):
    use_ip_aliases: Optional[bool] = Field(None, alias="useIpAliases")
    class Config: populate_by_name = True; extra = 'ignore'

class GKELoggingConfigInput(BaseModel):
    enable_components: Optional[List[str]] = Field(None, alias="enableComponents")
    class Config: populate_by_name = True; extra = 'ignore'

class GKEMonitoringConfigInput(BaseModel):
    enable_components: Optional[List[str]] = Field(None, alias="enableComponents")
    class Config: populate_by_name = True; extra = 'ignore'

class GKEAddonsConfigInput(BaseModel):
    http_load_balancing: Optional[Dict[str, bool]] = Field(None, alias="httpLoadBalancing")
    horizontal_pod_autoscaling: Optional[Dict[str, bool]] = Field(None, alias="horizontalPodAutoscaling")
    network_policy_config: Optional[Dict[str, bool]] = Field(None, alias="networkPolicyConfig")
    class Config: populate_by_name = True; extra = 'ignore'

class GKEPrivateClusterConfigInput(BaseModel):
    enable_private_nodes: Optional[bool] = Field(None, alias="enablePrivateNodes")
    enable_private_endpoint: Optional[bool] = Field(None, alias="enablePrivateEndpoint")
    master_ipv4_cidr_block: Optional[str] = Field(None, alias="masterIpv4CidrBlock")
    private_endpoint: Optional[str] = Field(None, alias="privateEndpoint")
    public_endpoint: Optional[str] = Field(None, alias="publicEndpoint")
    class Config: populate_by_name = True; extra = 'ignore'

class GKEMaintenancePolicyInput(BaseModel):
    window: Optional[Dict[str, Any]] = None
    resource_version: Optional[str] = Field(None, alias="resourceVersion")
    class Config: populate_by_name = True; extra = 'ignore'

class GKEAutopilotInput(BaseModel):
    enabled: Optional[bool] = None
    class Config: extra = 'ignore'

class GKEClusterDataInput(BaseModel):
    name: str
    description: Optional[str] = None
    initial_node_count: Optional[int] = Field(None, alias="initialNodeCount")
    node_pools: List[GKENodePoolInput] = Field(default_factory=list, alias="nodePools")
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
    zone: Optional[str] = None # Deprecated, use location

    network: Optional[str] = None
    subnetwork: Optional[str] = None
    private_cluster_config: Optional[GKEPrivateClusterConfigInput] = Field(None, alias="privateClusterConfig")
    master_authorized_networks_config: Optional[Dict[str, Any]] = Field(None, alias="masterAuthorizedNetworksConfig")
    ip_allocation_policy: Optional[GKEIPAllocationPolicyInput] = Field(None, alias="ipAllocationPolicy")
    network_policy: Optional[GKENetworkPolicyInput] = Field(None, alias="networkPolicy")

    addons_config: Optional[GKEAddonsConfigInput] = Field(None, alias="addonsConfig")

    logging_service: Optional[str] = Field(None, alias="loggingService")
    monitoring_service: Optional[str] = Field(None, alias="monitoringService")
    logging_config: Optional[GKELoggingConfigInput] = Field(None, alias="loggingConfig")
    monitoring_config: Optional[GKEMonitoringConfigInput] = Field(None, alias="monitoringConfig")

    maintenance_policy: Optional[GKEMaintenancePolicyInput] = Field(None, alias="maintenancePolicy")
    autopilot: Optional[GKEAutopilotInput] = None

    project_id: str
    is_autopilot: Optional[bool] = None
    has_public_endpoint: Optional[bool] = None
    network_policy_enabled: Optional[bool] = None
    node_auto_upgrade_enabled_default: Optional[bool] = None

    error_details: Optional[str] = None

    class Config:
        populate_by_name = True
        extra = 'ignore'
        arbitrary_types_allowed = True
```
