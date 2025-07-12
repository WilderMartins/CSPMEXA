from pydantic import BaseModel
from typing import Optional

class AWSCredentials(BaseModel):
    aws_access_key_id: str
    aws_secret_access_key: str

class AzureCredentials(BaseModel):
    azure_client_id: str
    azure_client_secret: str
    azure_tenant_id: str
    azure_subscription_id: str

# Adicionar outros provedores conforme necessário

class ProviderCredentials(BaseModel):
    provider: str
    credentials: dict # Será um dos modelos acima

class StoredCredentialInfo(BaseModel):
    provider: str
    configured: bool
    keys: Optional[list[str]] = None # Nomes das chaves, não os valores
