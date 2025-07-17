from sqlalchemy import Column, Integer, String, DateTime, func, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()

class CloudProviderEnum(str, enum.Enum):
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"
    HUAWEI = "huawei"
    GOOGLE_WORKSPACE = "google_workspace"
    MICROSOFT_365 = "microsoft_365"

class LinkedAccount(Base):
    __tablename__ = "linked_accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, comment="Nome amigável para a conta, definido pelo usuário.")
    provider = Column(SQLEnum(CloudProviderEnum), nullable=False)
    account_id = Column(String, nullable=False, unique=True, comment="ID da conta no provedor (ex: AWS Account ID, GCP Project ID).")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
