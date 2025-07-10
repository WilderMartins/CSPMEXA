# Este arquivo é uma cópia de backend/collector_service/app/schemas/ec2.py
# para ser usado pelo api_gateway_service como response_model.
# Manter sincronizado com a fonte original se houver alterações.

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# Schemas para Security Groups
class IpPermission(BaseModel):
    from_port: Optional[int] = Field(None, alias="FromPort")
    to_port: Optional[int] = Field(None, alias="ToPort")
    ip_protocol: Optional[str] = Field(None, alias="IpProtocol")
    ip_ranges: Optional[List[Dict[str, Any]]] = Field(None, alias="IpRanges")
    ipv6_ranges: Optional[List[Dict[str, Any]]] = Field(None, alias="Ipv6Ranges")
    prefix_list_ids: Optional[List[Dict[str, Any]]] = Field(None, alias="PrefixListIds")
    user_id_group_pairs: Optional[List[Dict[str, Any]]] = Field(None, alias="UserIdGroupPairs")

    class Config:
        populate_by_name = True

class SecurityGroup(BaseModel):
    group_id: str = Field(alias="GroupId")
    group_name: Optional[str] = Field(None, alias="GroupName")
    description: Optional[str] = Field(None, alias="Description")
    vpc_id: Optional[str] = Field(None, alias="VpcId")
    owner_id: Optional[str] = Field(None, alias="OwnerId")
    ip_permissions: Optional[List[IpPermission]] = Field(None, alias="IpPermissions")
    ip_permissions_egress: Optional[List[IpPermission]] = Field(None, alias="IpPermissionsEgress")
    tags: Optional[List[Dict[str, str]]] = Field(None, alias="Tags")
    region: str

    class Config:
        populate_by_name = True

# Schemas para Instâncias EC2
class InstanceState(BaseModel):
    code: Optional[int] = Field(None, alias="Code")
    name: Optional[str] = Field(None, alias="Name")

    class Config:
        populate_by_name = True

class Ec2InstanceData(BaseModel):
    instance_id: str = Field(alias="InstanceId")
    instance_type: Optional[str] = Field(None, alias="InstanceType")
    image_id: Optional[str] = Field(None, alias="ImageId")
    launch_time: Optional[datetime] = Field(None, alias="LaunchTime")
    platform: Optional[str] = Field(None, alias="PlatformDetails")
    private_dns_name: Optional[str] = Field(None, alias="PrivateDnsName")
    private_ip_address: Optional[str] = Field(None, alias="PrivateIpAddress")
    public_dns_name: Optional[str] = Field(None, alias="PublicDnsName")
    public_ip_address: Optional[str] = Field(None, alias="PublicIpAddress")
    state: Optional[InstanceState] = Field(None, alias="State")
    subnet_id: Optional[str] = Field(None, alias="SubnetId")
    vpc_id: Optional[str] = Field(None, alias="VpcId")
    architecture: Optional[str] = Field(None, alias="Architecture")
    iam_instance_profile_arn: Optional[str] = Field(None, alias="IamInstanceProfile")
    security_groups: Optional[List[Dict[str, str]]] = Field(None, alias="SecurityGroups")
    tags: Optional[List[Dict[str, str]]] = Field(None, alias="Tags")
    region: str
    error_details: Optional[str] = Field(None)

    class Config:
        populate_by_name = True
