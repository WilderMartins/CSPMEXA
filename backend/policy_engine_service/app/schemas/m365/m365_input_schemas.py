from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import datetime

# Estes schemas são para os dados que o Policy Engine espera receber do Collector Service.
# Eles devem ser compatíveis com os schemas de output do collector
# (collector_service/app/schemas/m365/m365_security_schemas.py)

# --- MFA Status Input ---
class M365UserMFADetailInput(BaseModel):
    user_principal_name: str = Field(..., alias="userPrincipalName")
    user_id: str = Field(..., alias="id")
    display_name: Optional[str] = Field(None, alias="displayName") # Pode ser o UPN se o coletor não conseguir o displayName real
    is_mfa_registered: Optional[bool] = None
    is_mfa_enabled_via_policies: Optional[bool] = None # Mapeado do 'isEnabled' do report
    mfa_state: Optional[str] = None # Ex: "NotRegistered", "Registered", "Enforced"
    error_details: Optional[str] = None

    class Config:
        populate_by_name = True # Permite que 'userPrincipalName' no JSON mapeie para user_principal_name
        extra = 'ignore'


class M365UserMFAStatusCollectionInput(BaseModel):
    users_mfa_status: List[M365UserMFADetailInput] = Field(default_factory=list)
    total_users_scanned: Optional[int] = 0 # Opcional, caso o coletor não consiga essa info
    total_users_with_mfa_issues: Optional[int] = 0
    error_message: Optional[str] = None


# --- Conditional Access Policies Input ---
class M365ConditionalAccessPolicyDetailInput(BaseModel):
    id: str
    display_name: str = Field(..., alias="displayName")
    state: str # "enabled", "disabled", "enabledForReportingButNotEnforced"
    error_details: Optional[str] = None

    class Config:
        populate_by_name = True
        extra = 'ignore'

class M365ConditionalAccessPolicyCollectionInput(BaseModel):
    policies: List[M365ConditionalAccessPolicyDetailInput] = Field(default_factory=list)
    total_policies_found: Optional[int] = 0
    error_message: Optional[str] = None

# Nota: No futuro, se os schemas do coletor e do motor de políticas divergirem mais,
# pode ser útil ter funções de mapeamento explícitas no API Gateway ou no Policy Engine.
# Por enquanto, manter os nomes dos campos alinhados (usando alias onde necessário) é suficiente.
```
