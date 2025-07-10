# Cópia de backend/collector_service/app/schemas/gcp_iam.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class GCPIAMBinding(BaseModel):
    role: str = Field(description="O papel concedido.")
    members: List[str] = Field(description="Lista de membros.")
    condition: Optional[Dict[str, Any]] = Field(None, description="Condição da binding.")

class GCPIAMPolicy(BaseModel):
    version: Optional[int] = Field(None, description="Versão da política.")
    bindings: List[GCPIAMBinding] = Field(description="Bindings da política.")
    etag: Optional[str] = Field(None, description="ETag da política.")

class GCPProjectIAMPolicyData(BaseModel):
    project_id: str = Field(description="ID do projeto GCP.")
    iam_policy: GCPIAMPolicy = Field(description="Política IAM do projeto.")
    has_external_members_with_primitive_roles: Optional[bool] = Field(None)
    external_primitive_role_details: List[str] = Field([])
    error_details: Optional[str] = Field(None)
