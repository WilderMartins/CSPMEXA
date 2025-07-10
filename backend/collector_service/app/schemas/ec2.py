from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# Schemas para Security Groups
class IpPermission(BaseModel):
    from_port: Optional[int] = Field(None, alias="FromPort")
    to_port: Optional[int] = Field(None, alias="ToPort")
    ip_protocol: Optional[str] = Field(None, alias="IpProtocol")
    ip_ranges: Optional[List[Dict[str, Any]]] = Field(None, alias="IpRanges") # e.g., [{"CidrIp": "0.0.0.0/0"}]
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
    region: str # Adicionado para que cada SG saiba sua região

    class Config:
        populate_by_name = True

# Schemas para Instâncias EC2
class InstanceState(BaseModel):
    code: Optional[int] = Field(None, alias="Code")
    name: Optional[str] = Field(None, alias="Name") # e.g., "running", "stopped"

    class Config:
        populate_by_name = True

class InstanceNetworkInterface(BaseModel):
    network_interface_id: str = Field(alias="NetworkInterfaceId")
    subnet_id: Optional[str] = Field(None, alias="SubnetId")
    vpc_id: Optional[str] = Field(None, alias="VpcId")
    private_ip_address: Optional[str] = Field(None, alias="PrivateIpAddress")
    public_ip_address: Optional[str] = Field(None, alias="Association", description="Public IP if associated") # Simplified
    # Adicionar mais campos de interface de rede conforme necessário

    class Config:
        populate_by_name = True


class Ec2InstanceData(BaseModel):
    instance_id: str = Field(alias="InstanceId")
    instance_type: Optional[str] = Field(None, alias="InstanceType")
    image_id: Optional[str] = Field(None, alias="ImageId")
    launch_time: Optional[datetime] = Field(None, alias="LaunchTime")
    platform: Optional[str] = Field(None, alias="PlatformDetails") # e.g., "Linux/UNIX", "Windows"
    private_dns_name: Optional[str] = Field(None, alias="PrivateDnsName")
    private_ip_address: Optional[str] = Field(None, alias="PrivateIpAddress")
    public_dns_name: Optional[str] = Field(None, alias="PublicDnsName")
    public_ip_address: Optional[str] = Field(None, alias="PublicIpAddress")
    state: Optional[InstanceState] = Field(None, alias="State")
    subnet_id: Optional[str] = Field(None, alias="SubnetId")
    vpc_id: Optional[str] = Field(None, alias="VpcId")
    architecture: Optional[str] = Field(None, alias="Architecture")
    iam_instance_profile_arn: Optional[str] = Field(None, alias="IamInstanceProfile", description="ARN of the IAM instance profile.") # Simplified, need to extract Arn
    security_groups: Optional[List[Dict[str, str]]] = Field(None, alias="SecurityGroups", description="List of security groups (name and ID).") # Simplified, just name and ID
    # network_interfaces: Optional[List[InstanceNetworkInterface]] = Field(None, alias="NetworkInterfaces") # Mais detalhado
    tags: Optional[List[Dict[str, str]]] = Field(None, alias="Tags")
    region: str # Adicionado para saber de qual região esta instância é
    error_details: Optional[str] = Field(None, description="Details of any error encountered while fetching data for this instance.")

    class Config:
        populate_by_name = True

# Lista de Security Groups pode ser um endpoint separado ou parte de uma coleta mais ampla
EC2SecurityGroupsCollectionResponse = List[SecurityGroup]
EC2InstancesCollectionResponse = List[Ec2InstanceData]

class EC2CollectionError(BaseModel):
    error: str = Field(description="Error message detailing why EC2 data collection failed globally.")
