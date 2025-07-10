from pydantic import BaseModel, EmailStr
from typing import Optional
import datetime


# Propriedades básicas do usuário
class UserBase(BaseModel):
    email: EmailStr
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False
    google_id: Optional[str] = None


# Propriedades para criar um usuário via API (se necessário, menos relevante para OAuth inicial)
class UserCreate(UserBase):
    password: Optional[str] = None  # Para login tradicional futuro


# Propriedades para ler um usuário via API
class User(UserBase):
    id: int
    mfa_secret: Optional[str] = None  # Não expor o segredo por padrão
    is_mfa_enabled: bool = False
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None

    class Config:
        orm_mode = True  # Pydantic v1
        # from_attributes = True # Pydantic v2


# Propriedades para atualizar um usuário
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


# Schema para habilitar MFA
class MFAEnableSchema(BaseModel):
    totp_code: str


# Schema para o setup do MFA (retorna o QR code URI)
class MFASetupSchema(BaseModel):
    secret_key: str
    otp_uri: str
