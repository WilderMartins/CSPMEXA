from pydantic import BaseModel, Field
from typing import Optional
import datetime
from app.models.linked_account_model import CloudProviderEnum

class LinkedAccountBase(BaseModel):
    name: str = Field(..., description="Nome amigável para a conta.")
    provider: CloudProviderEnum
    account_id: str = Field(..., description="ID da conta no provedor.")

class LinkedAccountCreate(LinkedAccountBase):
    credentials: dict = Field(..., description="Dicionário com as credenciais a serem salvas no Vault.")

class LinkedAccountUpdate(BaseModel):
    name: Optional[str] = None

class LinkedAccountSchema(LinkedAccountBase):
    id: int
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True
