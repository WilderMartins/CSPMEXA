# AWS Schemas (agora importados de um subpacote)
from .aws.s3_schemas import S3BucketData, S3Tag, S3ServerSideEncryptionRule, S3LifecycleRule, S3ReplicationRule, S3BucketPolicy, S3BucketACL, S3Grant, S3Grantee, S3Owner, S3BucketLogging, S3BucketVersioning, S3PublicAccessBlockData
from .aws.ec2_schemas import Ec2InstanceData, SecurityGroup, SecurityGroupRule, InstanceProfile, InstanceTag, InstanceNetworkInterface, PrivateIpAddress, InstanceBlockDeviceMapping, EbsInstanceBlockDevice
from .aws.iam_schemas import IAMUserData, IAMUserTag, IAMUserMFADevices, IAMAccessKeyMetadata, IAMUserPolicy, IAMRoleData, IAMRoleTag, IAMPolicyData, IAMAttachedPolicy, PolicyVersion
from .aws.rds_schemas import RDSInstanceData, RDSTag, RDSVpcSecurityGroupMembership, RDSEndpoint

# GCP Schemas
from .gcp_storage import GCPStorageBucketData, GCPBucketIAMMember, GCPBucketLifecycleRule, GCPBucketLoggingData, GCPBucketVersioningData
from .gcp_compute import GCPComputeInstanceData, GCPInstanceNetworkInterface, GCPInstanceDisk, GCPInstanceAttachedDisk, GCPFirewallData, GCPFirewallRule
from .gcp_iam import GCPProjectIAMPolicyData, GCPProjectIAMBinding, GCPProjectIAMMember

# Huawei Cloud Schemas
from .huawei_obs import HuaweiOBSBucketData, HuaweiOBSPolicyStatement, HuaweiOBSUser, HuaweiOBSGroup, HuaweiOBSCondition
from .huawei_ecs import HuaweiECSServerData, HuaweiECSNetworkInterface, HuaweiECSVolumeAttached, HuaweiVPCSecurityGroup, HuaweiVPCSecurityGroupRule
from .huawei_iam import HuaweiIAMUserData, HuaweiIAMUserCredential, HuaweiIAMUserMFADevice

# Azure Schemas
from .azure.azure_compute import AzureVirtualMachineData, AzureNicData, AzureIpConfigurationData, AzurePublicIpAddressData, AzureNetworkSecurityGroupData
from .azure.azure_storage import AzureStorageAccountData, AzureBlobServiceProperties, AzureBlobProperties, AzureFileServiceProperties

# Google Workspace Schemas
from .google_workspace.google_workspace_user import GoogleWorkspaceUser, GoogleWorkspaceUserCollection
from .google_workspace.google_drive_shared_drive import SharedDriveData, SharedDriveRestrictions, SharedDriveTheme
from .google_workspace.google_drive_file import DriveFileData
from .google_workspace.google_drive_permission import DrivePermissionData


# Re-export para facilitar o acesso
__all__ = [
    # AWS
    "S3BucketData", "S3Tag", "S3ServerSideEncryptionRule", "S3LifecycleRule", "S3ReplicationRule",
    "S3BucketPolicy", "S3BucketACL", "S3Grant", "S3Grantee", "S3Owner",
    "S3BucketLogging", "S3BucketVersioning", "S3PublicAccessBlockData",
    "Ec2InstanceData", "SecurityGroup", "SecurityGroupRule", "InstanceProfile", "InstanceTag",
    "InstanceNetworkInterface", "PrivateIpAddress", "InstanceBlockDeviceMapping", "EbsInstanceBlockDevice",
    "IAMUserData", "IAMUserTag", "IAMUserMFADevices", "IAMAccessKeyMetadata", "IAMUserPolicy",
    "IAMRoleData", "IAMRoleTag", "IAMPolicyData", "IAMAttachedPolicy", "PolicyVersion",
    "RDSInstanceData", "RDSTag", "RDSVpcSecurityGroupMembership", "RDSEndpoint",

    # GCP
    "GCPStorageBucketData", "GCPBucketIAMMember", "GCPBucketLifecycleRule", "GCPBucketLoggingData", "GCPBucketVersioningData",
    "GCPComputeInstanceData", "GCPInstanceNetworkInterface", "GCPInstanceDisk", "GCPInstanceAttachedDisk", "GCPFirewallData", "GCPFirewallRule",
    "GCPProjectIAMPolicyData", "GCPProjectIAMBinding", "GCPProjectIAMMember",

    # Huawei
    "HuaweiOBSBucketData", "HuaweiOBSPolicyStatement", "HuaweiOBSUser", "HuaweiOBSGroup", "HuaweiOBSCondition",
    "HuaweiECSServerData", "HuaweiECSNetworkInterface", "HuaweiECSVolumeAttached", "HuaweiVPCSecurityGroup", "HuaweiVPCSecurityGroupRule",
    "HuaweiIAMUserData", "HuaweiIAMUserCredential", "HuaweiIAMUserMFADevice",

    # Azure
    "AzureVirtualMachineData", "AzureNicData", "AzureIpConfigurationData", "AzurePublicIpAddressData", "AzureNetworkSecurityGroupData",
    "AzureStorageAccountData", "AzureBlobServiceProperties", "AzureBlobProperties", "AzureFileServiceProperties",

    # Google Workspace
    "GoogleWorkspaceUser", "GoogleWorkspaceUserCollection",
    "SharedDriveData", "SharedDriveRestrictions", "SharedDriveTheme",
    "DriveFileData", "DrivePermissionData",
]
