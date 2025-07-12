from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import datetime

# Suposição da estrutura de um "Risk" ou "CheckResult" do Huawei CSG
# Esta estrutura precisaria ser validada com a documentação oficial da API/SDK do CSG.

class CSGRiskResourceInfo(BaseModel):
    id: Optional[str] = Field(None, description="ID do recurso afetado.")
    name: Optional[str] = Field(None, description="Nome do recurso afetado.")
    type: Optional[str] = Field(None, description="Tipo do recurso afetado (ex: ECS, OBS, VPC).")
    region_id: Optional[str] = Field(None, alias="regionId", description="Região do recurso.")
    project_id: Optional[str] = Field(None, alias="projectId", description="Projeto do recurso.")
    # Outros detalhes do recurso podem ser incluídos aqui

    class Config:
        populate_by_name = True
        extra = 'ignore'

class CSGRiskItem(BaseModel):
    risk_id: str = Field(..., alias="riskId", description="ID único do risco/descoberta do CSG.")
    check_name: Optional[str] = Field(None, alias="checkName", description="Nome da checagem de segurança que gerou o risco.")
    description: Optional[str] = Field(None, description="Descrição detalhada do risco.")
    severity: Optional[str] = Field(None, description="Severidade do risco (ex: Critical, High, Medium, Low, Informational).") # Mapear para nosso Enum no Policy Engine
    status: Optional[str] = Field(None, description="Status do risco (ex: Unhandled, Handling, Handled, Ignored).")

    resource_info: CSGRiskResourceInfo = Field(..., alias="resource") # Informações do recurso afetado

    suggestion: Optional[str] = Field(None, description="Sugestão de remediação do CSG.")
    # url: Optional[str] = Field(None, description="URL para detalhes do risco no console CSG, se disponível.") # Link para o console

    first_detected_time: Optional[datetime.datetime] = Field(None, alias="firstDetectedTime")
    last_detected_time: Optional[datetime.datetime] = Field(None, alias="lastDetectedTime")
    # Outros campos específicos do CSG: compliance_standard, rule_id, etc.
    additional_properties: Optional[Dict[str, Any]] = Field(None, description="Propriedades adicionais específicas do risco.")

    collection_error_details: Optional[str] = None # Para erros ao processar este item específico

    class Config:
        populate_by_name = True
        extra = 'ignore'
        arbitrary_types_allowed = True

class CSGRiskCollection(BaseModel):
    risks: List[CSGRiskItem] = Field(default_factory=list)
    total_count: Optional[int] = Field(None, alias="totalCount")
    next_marker: Optional[str] = Field(None, alias="nextMarker") # Para paginação, se aplicável

    # Contexto da coleta
    domain_id_queried: Optional[str] = None
    project_id_queried: Optional[str] = None
    region_id_queried: Optional[str] = None
    error_message: Optional[str] = None # Para erros globais na coleta

    class Config:
        populate_by_name = True
        extra = 'ignore'
```
