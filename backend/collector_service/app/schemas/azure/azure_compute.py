from typing import List, Optional, Dict
from pydantic import BaseModel, Field

# Schemas para Network Security Groups (NSG) referenciados por NICs
class AzureNetworkSecurityGroupInfo(BaseModel):
    id: str
    name: Optional[str] = None
    resource_group: Optional[str] = None

# Schemas para Public IP Addresses
class AzurePublicIPAddress(BaseModel):
    id: str
    name: Optional[str] = None
    ip_address: Optional[str] = None # O endereço IP real
    resource_group: Optional[str] = None

# Schemas para IP Configurations dentro de uma Network Interface
class AzureIPConfiguration(BaseModel):
    name: Optional[str] = None
    private_ip_address: Optional[str] = None
    public_ip_address_details: Optional[AzurePublicIPAddress] = Field(default=None, alias="publicIpAddress") # Detalhes do IP Público

# Schemas para Network Interfaces (NICs)
class AzureNetworkInterface(BaseModel):
    id: str
    name: Optional[str] = None
    resource_group: Optional[str] = None
    ip_configurations: List[AzureIPConfiguration] = Field(default_factory=list, alias="ipConfigurations")
    network_security_group: Optional[AzureNetworkSecurityGroupInfo] = Field(default=None, alias="networkSecurityGroup")

# Schema principal para Azure Virtual Machine Data
class AzureVirtualMachineData(BaseModel):
    id: str = Field(..., description="Azure Resource ID for the Virtual Machine")
    name: str = Field(..., description="Name of the Virtual Machine")
    location: str = Field(..., description="Azure region where the VM is located")
    resource_group_name: Optional[str] = Field(default=None, description="Name of the Resource Group containing the VM")
    size: Optional[str] = Field(default=None, description="VM Size (e.g., Standard_DS1_v2)")
    os_type: Optional[str] = Field(default=None, description="Operating System type (e.g., Linux, Windows)")
    power_state: Optional[str] = Field(default=None, description="Current power state of the VM (e.g., VM running, VM deallocated)")
    tags: Optional[Dict[str, str]] = Field(default=None, description="Tags associated with the VM")
    network_interfaces: List[AzureNetworkInterface] = Field(default_factory=list, description="List of network interfaces attached to the VM")

    error_details: Optional[str] = Field(default=None, description="Details of any error encountered during data collection for this VM")

    class Config:
        populate_by_name = True
        # Pydantic v2:
        # model_config = {
        #     "populate_by_name": True,
        #     "json_schema_extra": { ... } # (example omitted for brevity)
        # }
