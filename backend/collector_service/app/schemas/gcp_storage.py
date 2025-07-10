from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# Schemas para Políticas IAM de Bucket GCP
class GCPBucketIAMBinding(BaseModel):
    role: str = Field(description="Papel concedido aos membros (ex: roles/storage.objectViewer).")
    members: List[str] = Field(description="Membros aos quais o papel é concedido (ex: user:email@example.com, serviceAccount:..., allUsers, allAuthenticatedUsers).")
    condition: Optional[Dict[str, Any]] = Field(None, description="Condição associada a esta ligação.")

class GCPBucketIAMPolicy(BaseModel):
    version: Optional[int] = Field(None)
    bindings: List[GCPBucketIAMBinding] = []
    etag: Optional[str] = Field(None)

# Schemas para ACLs de Bucket GCP (Legado, mas ainda pode ser relevante)
class GCPBucketACLEntity(BaseModel):
    entity: str = Field(description="O principal ao qual o acesso é concedido (ex: user-email, group-email, allUsers).")
    role: str = Field(description="O papel concedido (OWNER, READER, WRITER).")
    # Outros campos como id, domain, projectTeam podem existir.

class GCPBucketACL(BaseModel):
    items: List[GCPBucketACLEntity] = []

class GCPBucketVersioning(BaseModel):
    enabled: bool

class GCPBucketLogging(BaseModel):
    log_bucket: Optional[str] = Field(None)
    log_object_prefix: Optional[str] = Field(None)
    # enabled: bool # O logging é considerado habilitado se log_bucket estiver definido.

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
    project_number: Optional[str] = Field(None, description="Número do projeto ao qual o bucket pertence.") # GCP usa projectNumber para buckets
    location: str = Field(description="Localização do bucket (ex: US-EAST1).")
    storage_class: str = Field(alias="storageClass", description="Classe de armazenamento padrão do bucket.")
    time_created: datetime = Field(alias="timeCreated")
    updated: datetime

    iam_policy: Optional[GCPBucketIAMPolicy] = Field(None, description="Política IAM do bucket.")
    # acl: Optional[GCPBucketACL] = Field(None, description="ACLs legadas do bucket.") # Pode ser omitido se focarmos em IAM uniforme.
    versioning: Optional[GCPBucketVersioning] = Field(None)
    logging: Optional[GCPBucketLogging] = Field(None)
    website_configuration: Optional[GCPBucketWebsite] = Field(None, alias="website")
    retention_policy: Optional[GCPBucketRetentionPolicy] = Field(None, alias="retentionPolicy")

    # Campos para indicar acesso público inferido
    is_public_by_iam: Optional[bool] = Field(None, description="Indica se a política IAM permite acesso público (ex: allUsers, allAuthenticatedUsers).")
    public_iam_details: List[str] = Field([], description="Detalhes das bindings IAM que concedem acesso público.")
    # is_public_by_acl: Optional[bool] = Field(None, description="Indica se as ACLs legadas permitem acesso público.")
    # public_acl_details: List[str] = Field([], description="Detalhes das ACLs que concedem acesso público.")

    labels: Optional[Dict[str, str]] = Field(None)
    error_details: Optional[str] = Field(None, description="Detalhes de qualquer erro encontrado ao buscar dados para este bucket.")

    class Config:
        populate_by_name = True # Permite usar aliases como 'storageClass'
        # Para Pydantic V2, seria:
        # alias_generator = lambda field_name: field_name # ou custom
        # populate_by_name = True
        # Para Pydantic V1, populate_by_name é suficiente para aliases.
        # Se os nomes dos campos do objeto original não corresponderem exatamente,
        # ou se precisarmos de lógica de validação/transformação mais complexa,
        # podemos usar @validator ou @root_validator.
        # Exemplo: Pydantic V1 `allow_population_by_field_name = True`
        # Pydantic V2 `populate_by_name = True`
        # O comportamento padrão já tenta por nome do campo e depois por alias.
        # `populate_by_name = True` (Pydantic V2) ou `allow_population_by_field_name = True` (Pydantic V1)
        # é útil se você quiser que os aliases sejam considerados *primeiro* ou se os nomes dos campos no
        # dicionário de entrada correspondem aos aliases e não aos nomes dos campos do modelo.
        # Para este caso, os nomes dos campos do objeto Bucket do google-cloud-storage
        # geralmente são snake_case, então o mapeamento direto deve funcionar para muitos campos.
        # Os aliases são úteis para campos como `storageClass` que vêm como camelCase.
        # A configuração `populate_by_name = True` é mais relevante para Pydantic V2.
        # Para Pydantic V1, o comportamento padrão já é bastante flexível com aliases.
        # Apenas garantir que `alias` esteja definido corretamente nos Fields.
        pass
