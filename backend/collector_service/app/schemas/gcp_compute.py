from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- Schemas para Instâncias de VM do Compute Engine ---

class GCPComputeNetworkInterfaceAccessConfig(BaseModel):
    type: Optional[str] = Field(None) # ONE_TO_ONE_NAT
    name: Optional[str] = Field(None)
    nat_ip: Optional[str] = Field(None, alias="natIP")
    public_ptr_domain_name: Optional[str] = Field(None, alias="publicPtrDomainName")
    network_tier: Optional[str] = Field(None, alias="networkTier")

    class Config:
        populate_by_name = True

class GCPComputeNetworkInterface(BaseModel):
    name: Optional[str] = Field(None)
    network: Optional[str] = Field(None, description="URL da rede.")
    subnetwork: Optional[str] = Field(None, description="URL da sub-rede.")
    network_ip: Optional[str] = Field(None, alias="networkIP", description="IP privado principal.")
    access_configs: Optional[List[GCPComputeNetworkInterfaceAccessConfig]] = Field(None, alias="accessConfigs")
    # Outros campos: kind, stackType, etc.

    class Config:
        populate_by_name = True

class GCPComputeDiskAttachedDiskInitializeParams(BaseModel):
    disk_name: Optional[str] = Field(None, alias="diskName")
    disk_size_gb: Optional[str] = Field(None, alias="diskSizeGb") # Vem como string da API
    disk_type: Optional[str] = Field(None, alias="diskType") # URL do tipo de disco
    source_image: Optional[str] = Field(None, alias="sourceImage") # URL da imagem
    # Outros campos: description, labels, etc.

    class Config:
        populate_by_name = True

class GCPComputeAttachedDisk(BaseModel):
    type: Optional[str] = Field(None) # PERSISTENT, SCRATCH
    mode: Optional[str] = Field(None) # READ_WRITE, READ_ONLY
    source: Optional[str] = Field(None, description="URL do disco persistente, se já existente.")
    device_name: Optional[str] = Field(None, alias="deviceName")
    index: Optional[int] = Field(None)
    boot: Optional[bool] = Field(None)
    auto_delete: Optional[bool] = Field(None, alias="autoDelete")
    interface: Optional[str] = Field(None) # SCSI, NVME
    initialize_params: Optional[GCPComputeDiskAttachedDiskInitializeParams] = Field(None, alias="initializeParams")
    # Outros campos: guestOsFeatures, kind, licenses

    class Config:
        populate_by_name = True

class GCPComputeServiceAccount(BaseModel):
    email: Optional[str] = Field(None)
    scopes: Optional[List[str]] = Field(None)

class GCPComputeScheduling(BaseModel):
    on_host_maintenance: Optional[str] = Field(None, alias="onHostMaintenance") # MIGRATE, TERMINATE
    automatic_restart: Optional[bool] = Field(None, alias="automaticRestart")
    preemptible: Optional[bool] = Field(None)
    # Outros campos: provisioningModel, instanceTerminationAction

    class Config:
        populate_by_name = True

class GCPComputeInstanceData(BaseModel):
    id: str
    name: str
    description: Optional[str] = Field(None)
    zone: str # Vem como URL, precisaremos extrair o nome da zona
    machine_type: str = Field(alias="machineType", description="URL do tipo de máquina, precisaremos extrair.") # Vem como URL
    status: str # RUNNING, TERMINATED, STAGING, STOPPING, etc.
    creation_timestamp: datetime = Field(alias="creationTimestamp")

    can_ip_forward: Optional[bool] = Field(None, alias="canIpForward")
    deletion_protection: Optional[bool] = Field(None, alias="deletionProtection")

    network_interfaces: Optional[List[GCPComputeNetworkInterface]] = Field(None, alias="networkInterfaces")
    disks: Optional[List[GCPComputeAttachedDisk]] = Field(None)
    service_accounts: Optional[List[GCPComputeServiceAccount]] = Field(None, alias="serviceAccounts")
    scheduling: Optional[GCPComputeScheduling] = Field(None)

    tags_fingerprint: Optional[str] = Field(None, alias="tags", description="Fingerprint das tags. As tags em si estão em items.")
    tags_items: Optional[List[str]] = Field(None, description="Lista de tags aplicadas à instância.") # Extraído de tags.items se presente

    labels: Optional[Dict[str, str]] = Field(None)
    label_fingerprint: Optional[str] = Field(None, alias="labelFingerprint")

    # Campos extraídos para conveniência
    project_id: str
    extracted_zone: str
    extracted_machine_type: str
    public_ip_addresses: List[str] = Field(default_factory=list, description="Lista de IPs públicos extraídos.")
    private_ip_addresses: List[str] = Field(default_factory=list, description="Lista de IPs privados extraídos.")

    error_details: Optional[str] = Field(None)

    class Config:
        populate_by_name = True
        extra = 'ignore' # Adicionado para ignorar campos não mapeados da API


# --- Schemas para Firewalls VPC ---
class GCPFirewallAllowedRule(BaseModel):
    ip_protocol: str = Field(alias="IPProtocol")
    ports: Optional[List[str]] = Field(None) # Lista de portas ou ranges (ex: "22", "8000-9000")

    class Config:
        populate_by_name = True

class GCPFirewallDeniedRule(BaseModel): # Similar ao Allowed, mas para regras de negação
    ip_protocol: str = Field(alias="IPProtocol")
    ports: Optional[List[str]] = Field(None)

    class Config:
        populate_by_name = True

class GCPFirewallLogConfig(BaseModel):
    enable: bool
    metadata: Optional[str] = Field(None) # INCLUDE_ALL_METADATA, EXCLUDE_ALL_METADATA

class GCPFirewallData(BaseModel):
    id: str
    name: str
    description: Optional[str] = Field(None)
    network: str = Field(description="URL da rede VPC à qual a firewall se aplica.")
    priority: int
    direction: str # INGRESS, EGRESS

    allowed: Optional[List[GCPFirewallAllowedRule]] = Field(None)
    denied: Optional[List[GCPFirewallDeniedRule]] = Field(None)

    source_ranges: Optional[List[str]] = Field(None, alias="sourceRanges") # CIDRs de origem (para INGRESS)
    destination_ranges: Optional[List[str]] = Field(None, alias="destinationRanges") # CIDRs de destino (para EGRESS)
    source_tags: Optional[List[str]] = Field(None, alias="sourceTags")
    target_tags: Optional[List[str]] = Field(None, alias="targetTags")
    source_service_accounts: Optional[List[str]] = Field(None, alias="sourceServiceAccounts")
    target_service_accounts: Optional[List[str]] = Field(None, alias="targetServiceAccounts")

    disabled: bool
    log_config: Optional[GCPFirewallLogConfig] = Field(None, alias="logConfig")
    creation_timestamp: datetime = Field(alias="creationTimestamp")

    # Campos extraídos
    project_id: str
    extracted_network_name: str

    error_details: Optional[str] = Field(None)

    class Config:
        populate_by_name = True
        extra = 'ignore' # Adicionado
