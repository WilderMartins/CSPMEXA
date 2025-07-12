from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import datetime

# --- MFA Status ---
class M365UserMFAMethod(BaseModel):
    method_type: Optional[str] = Field(None, alias="methodType") # e.g., "microsoftAuthenticator", "sms", "voice"
    is_enabled: Optional[bool] = Field(None, alias="isEnabled") # Custom field, Graph API might not return this directly per method in bulk easily

class M365UserMFADetail(BaseModel):
    user_principal_name: str = Field(..., alias="userPrincipalName")
    user_id: str = Field(..., alias="id")
    display_name: Optional[str] = Field(None, alias="displayName")

    # O status de MFA pode ser inferido de várias formas:
    # 1. Pelos 'authenticationMethods' registrados para o usuário (requer permissão UserAuthenticationMethod.Read.All)
    # 2. Pelo estado de registro de MFA (mais antigo, via MSOnline/AzureAD PowerShell, ou via reports)
    # 3. Pelo resultado de políticas de Acesso Condicional
    # Para CSPM, queremos saber se o MFA está "efetivamente" protegendo o usuário.

    is_mfa_registered: Optional[bool] = Field(None, description="Indica se o usuário completou o registro de MFA (pode ser via SSPR registration).")
    is_mfa_enabled_via_policies: Optional[bool] = Field(None, description="Indica se o MFA é imposto ao usuário por políticas (ex: Acesso Condicional, Security Defaults).")
    # strong_authentication_methods: Optional[List[M365UserMFAMethod]] = Field(default_factory=list, description="Métodos de autenticação forte registrados.")
    # O campo acima pode ser muito detalhado para uma visão geral inicial de CSPM.
    # Um campo mais simples poderia ser:
    mfa_state: Optional[str] = Field(None, description="Estado geral do MFA para o usuário (ex: NotEnabled, Enforced, RegisteredNotEnforced)")

    # Detalhes sobre métodos de autenticação (simplificado para o schema)
    # Poderíamos ter um campo 'registered_auth_methods' que lista os tipos de métodos.
    # Ex: ["microsoftAuthenticator", "sms"]
    # Para o escopo inicial, focar em um status geral é mais prático.
    # Se o usuário tem "MFA forte" (ex: Authenticator App, FIDO2) vs "MFA fraco" (SMS, Voz) pode ser um detalhe.

    error_details: Optional[str] = None # Para erros ao buscar dados deste usuário específico

class M365UserMFAStatusCollection(BaseModel):
    users_mfa_status: List[M365UserMFADetail] = Field(default_factory=list)
    total_users_scanned: int = 0
    total_users_with_mfa_issues: int = 0 # Ex: MFA não registrado ou não imposto
    error_message: Optional[str] = None # Para erros globais na coleta


# --- Conditional Access Policies ---
class M365ConditionalAccessPolicyDetail(BaseModel):
    id: str
    display_name: str = Field(..., alias="displayName")
    state: str # "enabled", "disabled", "enabledForReportingButNotEnforced"
    # Adicionar outros campos relevantes se necessário para as políticas:
    # created_date_time: Optional[datetime.datetime] = Field(None, alias="createdDateTime")
    # modified_date_time: Optional[datetime.datetime] = Field(None, alias="modifiedDateTime")
    # conditions: Optional[Dict[str, Any]] = None # Pode ser muito complexo
    # grant_controls: Optional[Dict[str, Any]] = None # Pode ser muito complexo

    error_details: Optional[str] = None

class M365ConditionalAccessPolicyCollection(BaseModel):
    policies: List[M365ConditionalAccessPolicyDetail] = Field(default_factory=list)
    total_policies_found: int = 0
    error_message: Optional[str] = None

# Outros Schemas M365 (Exemplos para o futuro):
# class M365TenantSecureScore(BaseModel): ...
# class M365SharePointSharingConfig(BaseModel): ...
# class M365ExchangeTransportRule(BaseModel): ...

# Para garantir que alias funcione na serialização também, se necessário:
# class Config:
#     populate_by_name = True
#     extra = 'ignore'
#     arbitrary_types_allowed = True

# Adicionar Config aos modelos se for usar `model_dump(by_alias=True)` extensivamente
# e quiser garantir que os alias são usados na saída também, ou se tiver tipos arbitrários.
# Para Pydantic V2, `from_attributes = True` é o novo `orm_mode = True`.
# `populate_by_name = True` é útil para quando os dados de entrada usam os nomes originais da API.
# `extra = 'ignore'` é bom para não quebrar se a API retornar campos extras.

for model in [M365UserMFAMethod, M365UserMFADetail, M365UserMFAStatusCollection,
              M365ConditionalAccessPolicyDetail, M365ConditionalAccessPolicyCollection]:
    model.model_config = { # Pydantic V2
        "populate_by_name": True,
        "extra": "ignore",
        "arbitrary_types_allowed": True
    }
    # Para Pydantic V1, seria:
    # class Config:
    #     allow_population_by_field_name = True
    #     extra = 'ignore'
    #     arbitrary_types_allowed = True
    # model.Config = Config
```
