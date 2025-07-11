from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import datetime

# Este schema deve espelhar RDSInstanceData do collector_service
# e RDSInstanceDataInput do policy_engine_service (que por sua vez espelha o do collector)

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
    MasterUsername: Optional[str] = None
    Endpoint: Optional[RDSEndpoint] = None
    AllocatedStorage: int
    InstanceCreateTime: datetime.datetime
    PreferredBackupWindow: Optional[str] = None
    BackupRetentionPeriod: int
    DBSecurityGroups: List[str] = Field(default_factory=list)
    VpcSecurityGroups: List[RDSVpcSecurityGroupMembership] = Field(default_factory=list)
    DBParameterGroups: List[Dict[str, Any]] = Field(default_factory=list)
    AvailabilityZone: Optional[str] = None
    DBSubnetGroup: Optional[Dict[str, Any]] = None
    PreferredMaintenanceWindow: Optional[str] = None
    PendingModifiedValues: Optional[Dict[str, Any]] = None
    LatestRestorableTime: Optional[datetime.datetime] = None
    MultiAZ: bool
    EngineVersion: str
    AutoMinorVersionUpgrade: bool
    ReadReplicaSourceDBInstanceIdentifier: Optional[str] = None
    ReadReplicaDBInstanceIdentifiers: List[str] = Field(default_factory=list)
    LicenseModel: Optional[str] = None
    OptionGroupMemberships: List[Dict[str, Any]] = Field(default_factory=list)
    PubliclyAccessible: bool
    StorageType: Optional[str] = None
    DbInstancePort: Optional[int] = None
    StorageEncrypted: bool
    KmsKeyId: Optional[str] = None
    DbiResourceId: str
    CACertificateIdentifier: Optional[str] = None
    DomainMemberships: List[Dict[str, Any]] = Field(default_factory=list)
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
    TagList: Optional[List[RDSTag]] = None

    region: str

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True
        # Se houver campos extras vindos do collector que não estão aqui,
        # pode-se adicionar extra = 'ignore' para Pydantic V2 ou ajustar no Pydantic V1
        # No entanto, é melhor manter os schemas alinhados.
