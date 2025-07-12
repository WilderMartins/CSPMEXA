from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import datetime

# Referência: https://cloud.google.com/python/docs/reference/securitycenter/latest/google.cloud.securitycenter_v1.types.Finding

class GCPFindingSourceProperties(BaseModel):
    # Propriedades específicas da fonte, varia muito. Usar Dict[str, Any].
    # Exemplos: " explicación", "scanner_name" para Security Health Analytics.
    additional_properties: Optional[Dict[str, Any]] = None

    class Config:
        extra = 'allow'

class GCPFindingSeverity(str): # Embora o SDK use um Enum, a string é mais fácil para Pydantic
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    SEVERITY_UNSPECIFIED = "SEVERITY_UNSPECIFIED"

class GCPFinding(BaseModel):
    name: str # Formato: organizations/{organization_id}/sources/{source_id}/findings/{finding_id}
    parent: str # ID da fonte do finding.
    resource_name: str = Field(..., alias="resourceName", description="Nome completo do recurso associado ao finding.")
    state: str # "ACTIVE", "INACTIVE", "MUTED"
    category: str # Categoria da descoberta (ex: "MISCONFIGURATION", "THREAT").
    external_uri: Optional[str] = Field(None, alias="externalUri", description="URI para mais detalhes sobre o finding.")
    source_properties: Optional[GCPFindingSourceProperties] = Field(None, alias="sourceProperties")

    # SecurityMarks são annotations do usuário, podem não ser relevantes para todas as políticas CSPM, mas bom ter.
    # security_marks: Optional[Dict[str, Any]] = Field(None, alias="securityMarks") # Objeto complexo

    event_time: datetime.datetime = Field(..., alias="eventTime", description="Hora em que o evento que gerou o finding ocorreu.")
    create_time: datetime.datetime = Field(..., alias="createTime", description="Hora em que o finding foi criado no SCC.")
    update_time: Optional[datetime.datetime] = Field(None, alias="updateTime", description="Hora da última atualização do finding.")

    severity: str # Usar o Enum GCPFindingSeverity idealmente, mas string para Pydantic é mais simples se os valores são conhecidos.
                 # O SDK retorna um Enum, então precisaremos converter para string no coletor.

    canonical_name: Optional[str] = Field(None, alias="canonicalName", description="Nome canônico do tipo de finding.")
    description: Optional[str] = None # Descrição do finding (pode estar em source_properties).
    # finding_class: Optional[str] = Field(None, alias="findingClass") # THREAT, VULNERABILITY, MISCONFIGURATION etc. (SDK v1)
                                                                      # No SDK mais recente, 'category' pode ser preferível.

    # Campos de vulnerabilidade (se aplicável, para findings de vulnerabilidade)
    # vulnerability: Optional[Dict[str, Any]] = None

    # Campos de misconfiguração (se aplicável)
    # misconfiguration: Optional[Dict[str, Any]] = None

    # Campos extraídos/adicionados pelo coletor
    project_id: Optional[str] = Field(None, description="ID do projeto ao qual o recurso do finding pertence (extraído de resource_name).")
    organization_id: Optional[str] = Field(None, description="ID da organização (extraído de parent ou name).")
    source_id: Optional[str] = Field(None, description="ID da fonte (extraído de parent ou name).")
    finding_id: Optional[str] = Field(None, description="ID único do finding (extraído de name).")

    collection_error_details: Optional[str] = None

    class Config:
        populate_by_name = True
        extra = 'ignore'
        arbitrary_types_allowed = True


class GCPSCCFindingCollection(BaseModel):
    findings: List[GCPFinding] = Field(default_factory=list)
    next_page_token: Optional[str] = Field(None, alias="nextPageToken")
    total_size: Optional[int] = Field(None, alias="totalSize", description="Contagem total de findings se fornecido pela API (pode não ser sempre preciso com filtros).")

    # Contexto da coleta
    parent_resource_queried: Optional[str] = Field(None, description="Recurso pai consultado (org, folder, ou project).")
    filter_used: Optional[str] = None
    error_message: Optional[str] = None

    class Config:
        populate_by_name = True
        extra = 'ignore'
```
