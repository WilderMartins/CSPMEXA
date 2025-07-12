from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import datetime

# Referência: https://cloud.google.com/asset-inventory/docs/reference/rest/v1/assets/list
# O objeto Asset retornado pela API é rico e pode incluir IAM policy e Resource details.

class GCPAsset(BaseModel):
    name: str = Field(description="Nome completo do recurso do ativo. Ex: //compute.googleapis.com/projects/my-project/zones/us-central1-a/instances/my-instance")
    asset_type: str = Field(..., alias="assetType", description="Tipo do ativo. Ex: compute.googleapis.com/Instance")
    resource: Optional[Dict[str, Any]] = Field(None, description="Representação do recurso em si. A estrutura varia conforme o asset_type.")
    iam_policy: Optional[Dict[str, Any]] = Field(None, alias="iamPolicy", description="Política IAM anexada diretamente a este recurso, se aplicável e solicitada.")
    # organization_policy: Optional[List[Dict[str, Any]]] = Field(None, alias="orgPolicy", description="Políticas da Organização aplicadas a este recurso.") # Pode ser muito
    # access_policy: Optional[List[Dict[str, Any]]] = Field(None, alias="accessPolicy", description="Políticas do Access Context Manager.") # Pode ser muito

    # Campos extraídos/adicionados pelo coletor para conveniência
    project_id: Optional[str] = None
    location: Optional[str] = None # Extraído de 'name' ou 'resource.location' se possível
    display_name: Optional[str] = Field(None, description="Nome de exibição do recurso, se disponível em 'resource.data.displayName'.")
    create_time: Optional[datetime.datetime] = Field(None, alias="createTime", description="Timestamp de criação do recurso, se disponível.")
    update_time: Optional[datetime.datetime] = Field(None, alias="updateTime", description="Timestamp da última atualização do recurso, se disponível.")

    collection_error_details: Optional[str] = None # Para erros ao processar este ativo específico

    class Config:
        populate_by_name = True
        extra = 'ignore'
        arbitrary_types_allowed = True


class GCPAssetCollection(BaseModel):
    assets: List[GCPAsset] = Field(default_factory=list)
    next_page_token: Optional[str] = Field(None, alias="nextPageToken")
    read_time: Optional[datetime.datetime] = Field(None, alias="readTime", description="Timestamp da consistência dos dados do inventário.")

    # Contexto da coleta
    scope_queried: Optional[str] = Field(None, description="Escopo da consulta (ex: projects/my-project).")
    asset_types_queried: Optional[List[str]] = None
    content_type_queried: Optional[str] = None # RESOURCE, IAM_POLICY, ORG_POLICY, ACCESS_POLICY
    error_message: Optional[str] = None # Para erros globais na coleta

    class Config:
        populate_by_name = True
        extra = 'ignore'
        arbitrary_types_allowed = True
```
