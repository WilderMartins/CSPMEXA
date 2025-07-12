from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any # Dict, Any podem não ser necessários aqui se não usarmos source_properties complexas
import datetime

# Estes schemas espelham os de collector_service/app/schemas/m365/m365_security_schemas.py
# para uso no API Gateway (validação de resposta do collector, payload para policy engine).

# --- MFA Status ---
class M365UserMFADetail(BaseModel):
    user_principal_name: str = Field(..., alias="userPrincipalName")
    user_id: str = Field(..., alias="id")
    display_name: Optional[str] = Field(None, alias="displayName")
    is_mfa_registered: Optional[bool] = None
    is_mfa_enabled_via_policies: Optional[bool] = None
    mfa_state: Optional[str] = None
    error_details: Optional[str] = None

    class Config:
        populate_by_name = True
        extra = 'ignore'

class M365UserMFAStatusCollection(BaseModel):
    users_mfa_status: List[M365UserMFADetail] = Field(default_factory=list)
    total_users_scanned: int = 0
    total_users_with_mfa_issues: int = 0
    error_message: Optional[str] = None

    class Config:
        extra = 'ignore'

# --- Conditional Access Policies ---
class M365ConditionalAccessPolicyDetail(BaseModel):
    id: str
    display_name: str = Field(..., alias="displayName")
    state: str
    error_details: Optional[str] = None

    class Config:
        populate_by_name = True
        extra = 'ignore'

class M365ConditionalAccessPolicyCollection(BaseModel):
    policies: List[M365ConditionalAccessPolicyDetail] = Field(default_factory=list)
    total_policies_found: int = 0
    error_message: Optional[str] = None

    class Config:
        extra = 'ignore'

# Schema para o payload de análise M365 que o API Gateway enviará ao Policy Engine
# Pode ser um agregado se uma única chamada /analyze/m365 lida com múltiplos tipos de dados.
class M365TenantSecurityInput(BaseModel):
    users_mfa_status: Optional[M365UserMFAStatusCollection] = None
    conditional_access_policies: Optional[M365ConditionalAccessPolicyCollection] = None
    # Adicionar outros tipos de dados M365 aqui conforme são implementados
```
