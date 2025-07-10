from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# Schema para uma binding dentro de uma política IAM do GCP
class GCPIAMBinding(BaseModel):
    role: str = Field(description="O papel concedido, ex: 'roles/owner', 'roles/storage.objectViewer'.")
    members: List[str] = Field(description="Lista de membros aos quais o papel é concedido. Formatos: user:{emailid}, serviceAccount:{emailid}, group:{emailid}, domain:{domain}, allUsers, allAuthenticatedUsers.")
    condition: Optional[Dict[str, Any]] = Field(None, description="A condição associada a esta binding, se houver.")

# Schema para a política IAM de um recurso (ex: Projeto, Bucket, etc.)
class GCPIAMPolicy(BaseModel):
    version: Optional[int] = Field(None, description="Versão do formato da política.")
    bindings: List[GCPIAMBinding] = Field(description="Lista de bindings que associam membros a papéis.")
    etag: Optional[str] = Field(None, description="ETag da política, usado para controle de concorrência otimista.")
    # audit_configs: Optional[List[Any]] = Field(None) # AuditConfigs podem ser complexos, omitir por enquanto

# Schema para representar os dados coletados de políticas IAM de um projeto GCP
class GCPProjectIAMPolicyData(BaseModel):
    project_id: str = Field(description="ID do projeto GCP ao qual esta política se aplica.")
    # project_number: str # Opcional, pode ser útil
    iam_policy: GCPIAMPolicy = Field(description="A política IAM completa do projeto.")

    # Campos para indicar acesso público ou outros riscos inferidos
    has_external_members_with_primitive_roles: Optional[bool] = Field(None, description="Indica se há membros externos (allUsers, allAuthenticatedUsers) com papéis primitivos (owner, editor, viewer).")
    external_primitive_role_details: List[str] = Field([], description="Detalhes das bindings com membros externos em papéis primitivos.")

    error_details: Optional[str] = Field(None, description="Detalhes de qualquer erro encontrado ao buscar dados para esta política de projeto.")

# Poderíamos ter schemas mais granulares para Service Accounts, etc., mas para CSPM,
# analisar a política IAM do projeto (e de recursos chave como buckets) é um bom começo.
# Futuramente, podemos adicionar GCPServiceAccountData, etc.
