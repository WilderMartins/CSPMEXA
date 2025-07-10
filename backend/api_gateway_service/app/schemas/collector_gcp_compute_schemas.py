# Cópia de backend/collector_service/app/schemas/gcp_compute.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class GCPComputeNetworkInterfaceAccessConfig(BaseModel):
    type: Optional[str] = Field(None)
    name: Optional[str] = Field(None)
    nat_ip: Optional[str] = Field(None, alias="natIP")
    public_ptr_domain_name: Optional[str] = Field(None, alias="publicPtrDomainName")
    network_tier: Optional[str] = Field(None, alias="networkTier")
    class Config: populate_by_name = True

class GCPComputeNetworkInterface(BaseModel):
    name: Optional[str] = Field(None)
    network: Optional[str] = Field(None)
    subnetwork: Optional[str] = Field(None)
    network_ip: Optional[str] = Field(None, alias="networkIP")
    access_configs: Optional[List[GCPComputeNetworkInterfaceAccessConfig]] = Field(None, alias="accessConfigs")
    class Config: populate_by_name = True

class GCPComputeDiskAttachedDiskInitializeParams(BaseModel):
    disk_name: Optional[str] = Field(None, alias="diskName")
    disk_size_gb: Optional[str] = Field(None, alias="diskSizeGb")
    disk_type: Optional[str] = Field(None, alias="diskType")
    source_image: Optional[str] = Field(None, alias="sourceImage")
    class Config: populate_by_name = True

class GCPComputeAttachedDisk(BaseModel):
    type: Optional[str] = Field(None)
    mode: Optional[str] = Field(None)
    source: Optional[str] = Field(None)
    device_name: Optional[str] = Field(None, alias="deviceName")
    index: Optional[int] = Field(None)
    boot: Optional[bool] = Field(None)
    auto_delete: Optional[bool] = Field(None, alias="autoDelete")
    interface: Optional[str] = Field(None)
    initialize_params: Optional[GCPComputeDiskAttachedDiskInitializeParams] = Field(None, alias="initializeParams")
    class Config: populate_by_name = True

class GCPComputeServiceAccount(BaseModel):
    email: Optional[str] = Field(None)
    scopes: Optional[List[str]] = Field(None)

class GCPComputeScheduling(BaseModel):
    on_host_maintenance: Optional[str] = Field(None, alias="onHostMaintenance")
    automatic_restart: Optional[bool] = Field(None, alias="automaticRestart")
    preemptible: Optional[bool] = Field(None)
    class Config: populate_by_name = True

class GCPComputeInstanceData(BaseModel):
    id: str
    name: str
    description: Optional[str] = Field(None)
    zone: str
    machine_type: str = Field(alias="machineType")
    status: str
    creation_timestamp: datetime = Field(alias="creationTimestamp")
    can_ip_forward: Optional[bool] = Field(None, alias="canIpForward")
    deletion_protection: Optional[bool] = Field(None, alias="deletionProtection")
    network_interfaces: Optional[List[GCPComputeNetworkInterface]] = Field(None, alias="networkInterfaces")
    disks: Optional[List[GCPComputeAttachedDisk]] = Field(None)
    service_accounts: Optional[List[GCPComputeServiceAccount]] = Field(None, alias="serviceAccounts")
    scheduling: Optional[GCPComputeScheduling] = Field(None)
    tags_fingerprint: Optional[str] = Field(None, alias="tags")
    tags_items: Optional[List[str]] = Field(None)
    labels: Optional[Dict[str, str]] = Field(None)
    label_fingerprint: Optional[str] = Field(None, alias="labelFingerprint")
    project_id: str
    extracted_zone: str
    extracted_machine_type: str
    public_ip_addresses: List[str] = Field([])
    private_ip_addresses: List[str] = Field([])
    error_details: Optional[str] = Field(None)
    class Config: populate_by_name = True

class GCPFirewallAllowedRule(BaseModel):
    ip_protocol: str = Field(alias="IPProtocol")
    ports: Optional[List[str]] = Field(None)
    class Config: populate_by_name = True

class GCPFirewallDeniedRule(BaseModel):
    ip_protocol: str = Field(alias="IPProtocol")
    ports: Optional[List[str]] = Field(None)
    class Config: populate_by_name = True

class GCPFirewallLogConfig(BaseModel):
    enable: bool
    metadata: Optional[str] = Field(None)

class GCPFirewallData(BaseModel):
    id: str
    name: str
    description: Optional[str] = Field(None)
    network: str
    priority: int
    direction: str
    allowed: Optional[List[GCPFirewallAllowedRule]] = Field(None)
    denied: Optional[List[GCPFirewallDeniedRule]] = Field(None)
    source_ranges: Optional[List[str]] = Field(None, alias="sourceRanges")
    destination_ranges: Optional[List[str]] = Field(None, alias="destinationRanges")
    source_tags: Optional[List[str]] = Field(None, alias="sourceTags")
    target_tags: Optional[List[str]] = Field(None, alias="targetTags")
    source_service_accounts: Optional[List[str]] = Field(None, alias="sourceServiceAccounts")
    target_service_accounts: Optional[List[str]] = Field(None, alias="targetServiceAccounts")
    disabled: bool
    log_config: Optional[GCPFirewallLogConfig] = Field(None, alias="logConfig")
    creation_timestamp: datetime = Field(alias="creationTimestamp")
    project_id: str
    extracted_network_name: str
    error_details: Optional[str] = Field(None)
    class Config: populate_by_name = True
