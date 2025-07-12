from pydantic import BaseModel, EmailStr, Field
from typing import Optional
import datetime
from auth_service.app.models.user_model import UserRole # Importar o Enum UserRole


# Propriedades básicas do usuário
class UserBase(BaseModel):
    email: EmailStr
    is_active: Optional[bool] = Field(True)
    is_superuser: Optional[bool] = Field(False) # Mantido para consistência, mas SuperAdministrator é o principal
    role: Optional[UserRole] = Field(UserRole.USER) # Usar o Enum e definir default
    google_id: Optional[str] = None
    full_name: Optional[str] = None
    profile_picture_url: Optional[str] = None


# Propriedades para criar um usuário via API (se necessário, menos relevante para OAuth inicial)
class UserCreate(UserBase):
    password: Optional[str] = None  # Para login tradicional futuro


# Propriedades para ler um usuário via API
class User(UserBase):
    id: int
    is_mfa_enabled: bool = Field(False)
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True # Pydantic v2 (orm_mode é para v1)
        use_enum_values = True # Para que o Enum seja serializado para seu valor string


# Propriedades para atualizar um usuário
class UserUpdate(BaseModel): # Para uso por admins ou pelo próprio usuário para certos campos
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None # Apenas SuperAdministrator pode mudar isso
    role: Optional[UserRole] = None # Apenas admin/superadmin pode mudar isso
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
