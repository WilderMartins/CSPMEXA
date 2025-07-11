from typing import List, Optional, Dict
from pydantic import BaseModel, Field

class AzureStorageAccountNetworkRuleSet(BaseModel):
    default_action: str = Field(alias="defaultAction") # Allow or Deny
    # bypass: Optional[str] = None # Comma separated
    # ip_rules: List[Any] = Field(default_factory=list)
    # virtual_network_rules: List[Any] = Field(default_factory=list)

class AzureStorageAccountBlobProperties(BaseModel):
    # Configurações a nível de Blob Service
    delete_retention_policy_enabled: Optional[bool] = Field(default=None, alias="deleteRetentionPolicy.enabled")
    container_delete_retention_policy_enabled: Optional[bool] = Field(default=None, alias="containerDeleteRetentionPolicy.enabled")
    is_versioning_enabled: Optional[bool] = Field(default=None, alias="isVersioningEnabled")
    # Adicionar mais se necessário, como automatic_snapshot_policy_enabled, change_feed, etc.

class AzureStorageAccountSku(BaseModel):
    name: str # e.g., Standard_LRS, Premium_LRS
    tier: Optional[str] = None # e.g., Standard, Premium

class AzureStorageAccountData(BaseModel):
    id: str = Field(..., description="Azure Resource ID for the Storage Account")
    name: str = Field(..., description="Name of the Storage Account")
    location: str = Field(..., description="Azure region where the Storage Account is located")
    resource_group_name: Optional[str] = Field(default=None, description="Name of the Resource Group")
    kind: Optional[str] = Field(default=None, description="Kind of account (e.g., StorageV2, BlobStorage)")
    sku: Optional[AzureStorageAccountSku] = None

    # Security related properties
    allow_blob_public_access: Optional[bool] = Field(default=None, alias="allowBlobPublicAccess", description="Allows or disallows public access to all blobs or containers in the storage account.")
    minimum_tls_version: Optional[str] = Field(default=None, alias="minimumTlsVersion", description="The minimum TLS version to be permitted on requests to storage.")
    supports_https_traffic_only: Optional[bool] = Field(default=None, alias="supportsHttpsTrafficOnly", description="Requires HTTPS traffic for requests.")

    network_rule_set: Optional[AzureStorageAccountNetworkRuleSet] = Field(default=None, alias="networkAcls") # Renomeado para network_rule_set para consistência com a API

    # Blob service properties (se coletado separadamente ou parte do get_properties)
    blob_properties: Optional[AzureStorageAccountBlobProperties] = Field(default=None, description="Properties of the Blob service.")

    tags: Optional[Dict[str, str]] = Field(default=None, description="Tags associated with the Storage Account")
    error_details: Optional[str] = Field(default=None, description="Details of any error encountered during data collection for this Storage Account")

    class Config:
        populate_by_name = True
        # Pydantic V2:
        # model_config = {
        #     "populate_by_name": True,
        #     "json_schema_extra": { ... } # (example omitted for brevity)
        # }

# Se precisarmos de detalhes de contêineres no futuro:
# class AzureBlobContainerData(BaseModel):
#     name: str
#     public_access: Optional[str] = None # e.g., None, Blob, Container
#     # ... outras propriedades do contêiner
