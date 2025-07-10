# Cópia de backend/collector_service/app/schemas/huawei_ecs.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class HuaweiECSAddress(BaseModel):
    version: Optional[int] = None
    addr: Optional[str] = None
    mac_addr: Optional[str] = Field(None, alias="OS-EXT-IPS-MAC:mac_addr")
    type: Optional[str] = Field(None, alias="OS-EXT-IPS:type")
    class Config: populate_by_name = True

class HuaweiECSImage(BaseModel):
    id: str

class HuaweiECSFlavor(BaseModel):
    id: str
    name: Optional[str] = None

class HuaweiECSServerMetadata(BaseModel):
    custom_metadata: Optional[Dict[str, str]] = None

class HuaweiECSServerData(BaseModel):
    id: str
    name: str
    status: str
    created: datetime
    updated: Optional[datetime] = None
    user_id: Optional[str] = Field(None, alias="user_id")
    image: Optional[HuaweiECSImage] = None
    flavor: HuaweiECSFlavor
    addresses: Optional[Dict[str, List[HuaweiECSAddress]]] = None
    key_name: Optional[str] = Field(None, alias="key_name")
    availability_zone: Optional[str] = Field(None, alias="OS-EXT-AZ:availability_zone")
    host_id: Optional[str] = Field(None, alias="OS-EXT-SRV-ATTR:host")
    hypervisor_hostname: Optional[str] = Field(None, alias="OS-EXT-SRV-ATTR:hypervisor_hostname")
    security_groups: Optional[List[Dict[str, str]]] = None
    volumes_attached: Optional[List[Dict[str, str]]] = Field(None, alias="os-extended-volumes:volumes_attached")
    metadata: Optional[HuaweiECSServerMetadata] = None
    project_id: str
    region_id: str
    public_ips: List[str] = []
    private_ips: List[str] = []
    error_details: Optional[str] = None
    class Config: populate_by_name = True

class HuaweiVPCSecurityGroupRule(BaseModel):
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

class HuaweiVPCSecurityGroup(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    project_id_from_collector: str = Field(alias="project_id")
    security_group_rules: List[HuaweiVPCSecurityGroupRule] = []
    region_id: str
    error_details: Optional[str] = None
    class Config: populate_by_name = True
