# Cópia de backend/collector_service/app/schemas/gcp_storage.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class GCPBucketIAMBinding(BaseModel):
    role: str = Field(description="Papel concedido aos membros (ex: roles/storage.objectViewer).")
    members: List[str] = Field(description="Membros aos quais o papel é concedido (ex: user:email@example.com, serviceAccount:..., allUsers, allAuthenticatedUsers).")
    condition: Optional[Dict[str, Any]] = Field(None, description="Condição associada a esta ligação.")

class GCPBucketIAMPolicy(BaseModel):
    version: Optional[int] = Field(None)
    bindings: List[GCPBucketIAMBinding] = []
    etag: Optional[str] = Field(None)

class GCPBucketVersioning(BaseModel):
    enabled: bool

class GCPBucketLogging(BaseModel):
    log_bucket: Optional[str] = Field(None)
    log_object_prefix: Optional[str] = Field(None)

class GCPBucketWebsite(BaseModel):
    main_page_suffix: Optional[str] = Field(None)
    not_found_page: Optional[str] = Field(None)

class GCPBucketRetentionPolicy(BaseModel):
    retention_period: Optional[int] = Field(None, description="Período de retenção em segundos.")
    effective_time: Optional[datetime] = Field(None)
    is_locked: Optional[bool] = Field(None)

class GCPStorageBucketData(BaseModel):
    id: str = Field(description="ID do bucket (geralmente o nome).")
    name: str = Field(description="Nome do bucket.")
    project_number: Optional[str] = Field(None, description="Número do projeto ao qual o bucket pertence.")
    location: str = Field(description="Localização do bucket (ex: US-EAST1).")
    storage_class: str = Field(alias="storageClass", description="Classe de armazenamento padrão do bucket.")
    time_created: datetime = Field(alias="timeCreated")
    updated: datetime
    iam_policy: Optional[GCPBucketIAMPolicy] = Field(None, description="Política IAM do bucket.")
    versioning: Optional[GCPBucketVersioning] = Field(None)
    logging: Optional[GCPBucketLogging] = Field(None)
    website_configuration: Optional[GCPBucketWebsite] = Field(None, alias="website")
    retention_policy: Optional[GCPBucketRetentionPolicy] = Field(None, alias="retentionPolicy")
    is_public_by_iam: Optional[bool] = Field(None, description="Indica se a política IAM permite acesso público.")
    public_iam_details: List[str] = Field([], description="Detalhes das bindings IAM que concedem acesso público.")
    labels: Optional[Dict[str, str]] = Field(None)
    error_details: Optional[str] = Field(None, description="Detalhes de qualquer erro.")

    class Config:
        populate_by_name = True
