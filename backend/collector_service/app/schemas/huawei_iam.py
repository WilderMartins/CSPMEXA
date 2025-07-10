from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- Schemas para Huawei Cloud IAM ---

class HuaweiIAMUserLoginProtect(BaseModel): # Parte da resposta de GetUser
    enabled: bool
    verification_method: Optional[str] = Field(None, description="ex: sms, email, vmfa") # vmfa é Virtual MFA

class HuaweiIAMUserPasswordStatus(BaseModel): # Parte da resposta de GetUser
    # A API pode não retornar diretamente a idade da senha, mas se ela expira.
    # Para CSPM, o importante é se há política de expiração e se a senha é forte (não coletável diretamente).
    # Vamos focar no status do MFA e nas credenciais de acesso programático.
    # last_password_change: Optional[datetime] = None # Se disponível
    expires_at: Optional[datetime] = Field(None, description="Data de expiração da senha, se aplicável.")


class HuaweiIAMUserAccessKey(BaseModel):
    access_key: str = Field(alias="access") # AK
    secret: Optional[str] = Field(None, description="SK não é retornado pela API após criação.")
    status: str # Active, Inactive
    create_time: Optional[datetime] = Field(None, alias="create_time_format") # Verificar formato exato da API
    description: Optional[str] = Field(None)
    # last_used_time: Optional[datetime] = Field(None) # API para último uso de AK/SK pode ser separada

class HuaweiIAMUserConsoleLogin(BaseModel): # Informações sobre login no console
    # Se o usuário pode ou não fazer login no console
    console_access: Optional[bool] = Field(None)
    # Outros detalhes como último login podem não estar diretamente no GetUser

class HuaweiIAMUserMfaDevice(BaseModel): # Pode vir de uma chamada separada como ListUserMfaDevices
    serial_number: str
    type: str # Ex: "virtual"
    # enable_date: Optional[datetime] # Data de habilitação do MFA

class HuaweiIAMUserData(BaseModel):
    id: str
    name: str
    domain_id: str # ID do domínio (conta) à qual o usuário pertence
    enabled: bool

    email: Optional[str] = Field(None)
    phone: Optional[str] = Field(None, alias="areacode_mobile") # Pode vir como combinação

    # Informações de segurança diretamente do GetUser
    login_protect: Optional[HuaweiIAMUserLoginProtect] = Field(None, alias="login_protect") # Se MFA está habilitado para login
    # password_status: Optional[HuaweiIAMUserPasswordStatus] = Field(None, alias="pwd_status") # Se a senha expira

    # Informações que podem precisar de chamadas adicionais ou vêm de outras listagens
    access_keys: Optional[List[HuaweiIAMUserAccessKey]] = Field(None, description="Lista de chaves de acesso AK/SK do usuário.")
    mfa_devices: Optional[List[HuaweiIAMUserMfaDevice]] = Field(None, description="Lista de dispositivos MFA associados.")
    # console_login_details: Optional[HuaweiIAMUserConsoleLogin] = Field(None)

    # Adicionado pelo collector
    # project_id: str # Usuários IAM são a nível de Domínio/Conta, não Projeto.
    # region_id: str # IAM é global na Huawei, mas o cliente SDK é instanciado com uma região para endpoint.

    error_details: Optional[str] = Field(None)

    class Config:
        populate_by_name = True # Para aliases como "areacode_mobile"

# Poderíamos adicionar schemas para Grupos, Roles, Policies se o escopo aumentar.
# Por enquanto, focaremos nos usuários e suas credenciais/MFA.
