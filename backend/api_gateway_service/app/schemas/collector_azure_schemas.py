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

# Azure Storage
class AzureBlobContainerData(BaseModel):
    id: str
    name: Optional[str] = None
    public_access: Optional[str] = None
    last_modified_time: Optional[datetime] = Field(None, alias="lastModifiedTime")
    class Config: populate_by_name = True

class AzureStorageAccountData(BaseModel):
    id: str
    name: str
    location: str
    resource_group_name: Optional[str] = None
    kind: Optional[str] = None
    sku_name: Optional[str] = None
    allow_blob_public_access: Optional[bool] = None
    minimum_tls_version: Optional[str] = None
    supports_https_traffic_only: Optional[bool] = None
    blob_containers: List[AzureBlobContainerData] = Field(default_factory=list)
    error_details: Optional[str] = None
