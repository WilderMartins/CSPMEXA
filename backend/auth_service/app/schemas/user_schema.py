from pydantic import BaseModel, EmailStr
from typing import Optional
import datetime


# Propriedades básicas do usuário
class UserBase(BaseModel):
    email: EmailStr
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False
    role: Optional[str] = "user" # Adicionado role
    google_id: Optional[str] = None
    full_name: Optional[str] = None # Adicionado full_name
    profile_picture_url: Optional[str] = None # Adicionado profile_picture_url


# Propriedades para criar um usuário via API (se necessário, menos relevante para OAuth inicial)
class UserCreate(UserBase):
    password: Optional[str] = None  # Para login tradicional futuro


# Propriedades para ler um usuário via API
class User(UserBase): # UserBase já inclui email, is_active, is_superuser, role, google_id, full_name, profile_picture_url
    id: int
    # mfa_secret: Optional[str] = None # Não expor o segredo por padrão, a menos que seja para um admin específico
    is_mfa_enabled: bool = False
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None

    class Config:
        orm_mode = True  # Pydantic v1
        # from_attributes = True # Pydantic v2


# Propriedades para atualizar um usuário
class UserUpdate(BaseModel): # Para uso por admins ou pelo próprio usuário para certos campos
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None # Apenas admin pode mudar isso
    role: Optional[str] = None # Apenas admin pode mudar isso
    full_name: Optional[str] = None
    profile_picture_url: Optional[str] = None


# Schema para um admin atualizar outro usuário
class UserUpdateByAdmin(UserUpdate):
    # Admins podem modificar tudo de UserUpdate
    pass


# Schema para o usuário atualizar seu próprio perfil (campos limitados)
class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    profile_picture_url: Optional[str] = None


# Schema para habilitar MFA
class MFAEnableSchema(BaseModel):
    totp_code: str


# Schema para o setup do MFA (retorna o QR code URI)
class MFASetupSchema(BaseModel):
    secret_key: str
    otp_uri: str
