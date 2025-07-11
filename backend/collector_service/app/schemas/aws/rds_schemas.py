from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import datetime

class RDSTag(BaseModel):
    Key: str
    Value: str

class RDSVpcSecurityGroupMembership(BaseModel):
    VpcSecurityGroupId: Optional[str] = None
    Status: Optional[str] = None

class RDSEndpoint(BaseModel):
    Address: Optional[str] = None
    Port: Optional[int] = None
    HostedZoneId: Optional[str] = None

class RDSInstanceData(BaseModel):
    DBInstanceIdentifier: str
    DBInstanceArn: str
    DBInstanceClass: str
    Engine: str
    DBInstanceStatus: str
    MasterUsername: Optional[str] = None # Not always present
    Endpoint: Optional[RDSEndpoint] = None
    AllocatedStorage: int
    InstanceCreateTime: datetime.datetime
    PreferredBackupWindow: Optional[str] = None
    BackupRetentionPeriod: int
    DBSecurityGroups: List[str] = Field(default_factory=list) # Older EC2-Classic SGs
    VpcSecurityGroups: List[RDSVpcSecurityGroupMembership] = Field(default_factory=list)
    DBParameterGroups: List[Dict[str, Any]] = Field(default_factory=list) # Simplified for now
    AvailabilityZone: Optional[str] = None
    DBSubnetGroup: Optional[Dict[str, Any]] = None # Simplified for now
    PreferredMaintenanceWindow: Optional[str] = None
    PendingModifiedValues: Optional[Dict[str, Any]] = None # Simplified for now
    LatestRestorableTime: Optional[datetime.datetime] = None
    MultiAZ: bool
    EngineVersion: str
    AutoMinorVersionUpgrade: bool
    ReadReplicaSourceDBInstanceIdentifier: Optional[str] = None
    ReadReplicaDBInstanceIdentifiers: List[str] = Field(default_factory=list)
    LicenseModel: Optional[str] = None
    OptionGroupMemberships: List[Dict[str, Any]] = Field(default_factory=list) # Simplified for now
    PubliclyAccessible: bool
    StorageType: Optional[str] = None
    DbInstancePort: Optional[int] = None # Not always present, use Endpoint.Port
    StorageEncrypted: bool
    KmsKeyId: Optional[str] = None
    DbiResourceId: str
    CACertificateIdentifier: Optional[str] = None
    DomainMemberships: List[Dict[str, Any]] = Field(default_factory=list) # Simplified for now
    CopyTagsToSnapshot: Optional[bool] = None
    MonitoringInterval: Optional[int] = None
    MonitoringRoleArn: Optional[str] = None
    PromotionTier: Optional[int] = None
    IAMDatabaseAuthenticationEnabled: Optional[bool] = None
    PerformanceInsightsEnabled: Optional[bool] = None
    PerformanceInsightsKMSKeyId: Optional[str] = None
    PerformanceInsightsRetentionPeriod: Optional[int] = None
    EnabledCloudwatchLogsExports: Optional[List[str]] = None
    DeletionProtection: Optional[bool] = None
    TagList: Optional[List[RDSTag]] = None # Using RDSTag model

    # Custom extracted fields for convenience
    region: str # To be populated based on the client's region

    class Config:
        from_attributes = True # Pydantic V2
        # orm_mode = True # Pydantic V1
        arbitrary_types_allowed = True # For datetime
