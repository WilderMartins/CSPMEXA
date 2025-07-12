from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLAlchemyEnum
from sqlalchemy.sql import func
from app.db.session import Base
import enum


class UserRole(str, enum.Enum):
    USER = "User"
    TECHNICAL_LEAD = "TechnicalLead"
    MANAGER = "Manager"
    ADMINISTRATOR = "Administrator"
    SUPER_ADMINISTRATOR = "SuperAdministrator"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(
        String, nullable=True
    )  # Para login tradicional futuro, não usado no MVP OAuth inicial

    # Google OAuth fields
    google_id = Column(String, unique=True, index=True, nullable=True)

    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)  # Mantido, pode ser redundante com SuperAdministrator ou ter outro propósito
    role = Column(SQLAlchemyEnum(UserRole, name="user_role_enum", create_type=False), default=UserRole.USER, nullable=False)

    # Campos de perfil adicionais (opcionais)
    full_name = Column(String, nullable=True)
    profile_picture_url = Column(String, nullable=True)

    # MFA (TOTP)
    mfa_secret = Column(String, nullable=True)
    is_mfa_enabled = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"
