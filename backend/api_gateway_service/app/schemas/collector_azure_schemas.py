from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

# Schemas espelhados do collector_service para Azure

# Azure Compute (VMs)
class AzureNetworkSecurityGroupInfo(BaseModel):
    id: str
    name: Optional[str] = None
    resource_group: Optional[str] = None

class AzurePublicIPAddress(BaseModel):
    id: str
    name: Optional[str] = None
    ip_address: Optional[str] = None
    resource_group: Optional[str] = None

class AzureIPConfiguration(BaseModel):
    name: Optional[str] = None
    private_ip_address: Optional[str] = None
    public_ip_address_details: Optional[AzurePublicIPAddress] = Field(None, alias="publicIPAddress")
    class Config: populate_by_name = True


class AzureNetworkInterface(BaseModel):
    id: str
    name: Optional[str] = None
    resource_group: Optional[str] = None
    ip_configurations: List[AzureIPConfiguration] = Field(default_factory=list)
    network_security_group: Optional[AzureNetworkSecurityGroupInfo] = None

class AzureVirtualMachineData(BaseModel):
    id: str
    name: str
    location: str
    resource_group_name: Optional[str] = None
    size: Optional[str] = None
    os_type: Optional[str] = None
    power_state: Optional[str] = None
    tags: Optional[Dict[str, str]] = None
    network_interfaces: List[AzureNetworkInterface] = Field(default_factory=list)
    error_details: Optional[str] = None
    class Config: populate_by_name = True


# Azure Storage (espelhando collector_service.app.schemas.azure.azure_storage.py)
class AzureStorageAccountNetworkRuleSet(BaseModel):
    default_action: str = Field(alias="defaultAction")
    class Config: populate_by_name = True

class AzureStorageAccountBlobProperties(BaseModel):
    delete_retention_policy_enabled: Optional[bool] = Field(None, alias="deleteRetentionPolicy.enabled")
    container_delete_retention_policy_enabled: Optional[bool] = Field(None, alias="containerDeleteRetentionPolicy.enabled")
    is_versioning_enabled: Optional[bool] = Field(None, alias="isVersioningEnabled")
    class Config: populate_by_name = True

class AzureStorageAccountSku(BaseModel):
    name: str
    tier: Optional[str] = None
    class Config: populate_by_name = True

class AzureStorageAccountData(BaseModel):
    id: str
    name: str
    location: str
    resource_group_name: Optional[str] = None
    kind: Optional[str] = None
    sku: Optional[AzureStorageAccountSku] = None # Alterado de sku_name para objeto Sku
    allow_blob_public_access: Optional[bool] = Field(None, alias="allowBlobPublicAccess")
    minimum_tls_version: Optional[str] = Field(None, alias="minimumTlsVersion")
    supports_https_traffic_only: Optional[bool] = Field(None, alias="supportsHttpsTrafficOnly")
    network_rule_set: Optional[AzureStorageAccountNetworkRuleSet] = Field(None, alias="networkAcls") # Espelha networkAcls do SDK
    blob_properties: Optional[AzureStorageAccountBlobProperties] = None
    tags: Optional[Dict[str, str]] = None
    error_details: Optional[str] = None
    # blob_containers: List[AzureBlobContainerData] = Field(default_factory=list) # Removido pois não está no schema do collector para este MVP
    class Config: populate_by_name = True
