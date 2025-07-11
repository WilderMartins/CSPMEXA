from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class CloudSQLIpAddress(BaseModel):
    ip_address: Optional[str] = Field(None, alias="ipAddress")
    type: Optional[str] = None # PRIMARY, OUTGOING, PRIVATE
    time_to_retire: Optional[datetime] = Field(None, alias="timeToRetire")
    class Config: populate_by_name = True; extra = 'ignore'

class CloudSQLSettingsVersion(BaseModel): # Usado dentro de settings
    # Este é um int64 na API, mas Pydantic pode lidar com int
    settings_version: Optional[int] = Field(None, alias="settingsVersion")
    kind: Optional[str] = None
    class Config: populate_by_name = True; extra = 'ignore'


class CloudSQLIpConfiguration(BaseModel):
    ipv4_enabled: Optional[bool] = Field(None, alias="ipv4Enabled")
    private_network: Optional[str] = Field(None, alias="privateNetwork") # Self-link to network
    require_ssl: Optional[bool] = Field(None, alias="requireSsl")
    # authorized_networks: List[Dict[str, Any]] = Field(default_factory=list, alias="authorizedNetworks") # AclEntry
    class Config: populate_by_name = True; extra = 'ignore'

class CloudSQLBackupConfiguration(BaseModel):
    enabled: Optional[bool] = None
    start_time: Optional[str] = Field(None, alias="startTime") # HH:MM format
    binary_log_enabled: Optional[bool] = Field(None, alias="binaryLogEnabled")
    # Mais campos como pointInTimeRecoveryEnabled, replicationLogArchivingEnabled
    class Config: populate_by_name = True; extra = 'ignore'

class CloudSQLLocationPreference(BaseModel):
    zone: Optional[str] = None
    kind: Optional[str] = None
    class Config: extra = 'ignore'

class CloudSQLMaintenanceWindow(BaseModel):
    hour: Optional[int] = None
    day: Optional[int] = None # 1-7 (Monday-Sunday)
    update_track: Optional[str] = Field(None, alias="updateTrack") # stable, canary
    kind: Optional[str] = None
    class Config: populate_by_name = True; extra = 'ignore'

class CloudSQLDatabaseFlags(BaseModel):
    name: Optional[str] = None
    value: Optional[str] = None

class CloudSQLSettings(BaseModel):
    settings_version: Optional[str] = Field(None, alias="settingsVersion") # String na listagem, int64 no get
    tier: Optional[str] = None
    data_disk_size_gb: Optional[str] = Field(None, alias="dataDiskSizeGb") # String
    data_disk_type: Optional[str] = Field(None, alias="dataDiskType") # PD_SSD, PD_HDD
    ip_configuration: Optional[CloudSQLIpConfiguration] = Field(None, alias="ipConfiguration")
    backup_configuration: Optional[CloudSQLBackupConfiguration] = Field(None, alias="backupConfiguration")
    location_preference: Optional[CloudSQLLocationPreference] = Field(None, alias="locationPreference")
    maintenance_window: Optional[CloudSQLMaintenanceWindow] = Field(None, alias="maintenanceWindow")
    database_flags: List[CloudSQLDatabaseFlags] = Field(default_factory=list, alias="databaseFlags")
    activation_policy: Optional[str] = Field(None, alias="activationPolicy") # ALWAYS, NEVER, ON_DEMAND
    storage_auto_resize: Optional[bool] = Field(None, alias="storageAutoResize")
    # Muitos outros campos: userLabels, availabilityType, pricingPlan, etc.
    class Config: populate_by_name = True; extra = 'ignore'

class CloudSQLInstanceData(BaseModel):
    kind: Optional[str] = None # "sql#instance"
    name: str # Name of the instance
    project: str # Project ID owning the instance
    region: str
    database_version: Optional[str] = Field(None, alias="databaseVersion") # e.g., MYSQL_5_7, POSTGRES_13
    backend_type: Optional[str] = Field(None, alias="backendType") # FIRST_GEN, SECOND_GEN, EXTERNAL

    connection_name: Optional[str] = Field(None, alias="connectionName") # project:region:instance
    instance_type: Optional[str] = Field(None, alias="instanceType") # CLOUD_SQL_INSTANCE, READ_REPLICA_INSTANCE, ON_PREMISES_INSTANCE

    create_time: Optional[datetime] = Field(None, alias="createTime")
    state: Optional[str] = None # RUNNABLE, SUSPENDED, PENDING_CREATE, MAINTENANC

    ip_addresses: List[CloudSQLIpAddress] = Field(default_factory=list, alias="ipAddresses")
    server_ca_cert: Optional[Dict[str, Any]] = Field(None, alias="serverCaCert") # CertInfo

    settings: Optional[CloudSQLSettings] = None

    # Campos extraídos/adicionados pelo collector
    has_public_ip: Optional[bool] = None
    ssl_required: Optional[bool] = None
    automated_backups_enabled: Optional[bool] = None

    error_details: Optional[str] = None

    class Config:
        populate_by_name = True
        extra = 'ignore'
        arbitrary_types_allowed = True
```
