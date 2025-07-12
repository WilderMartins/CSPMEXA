import hvac
from typing import List, Dict, Any
from app.core.config import get_vault_client

class CredentialsService:
    def __init__(self):
        self.vault_client: hvac.Client = get_vault_client()
        if not self.vault_client:
            raise ConnectionError("Não foi possível conectar ao Vault. O serviço de credenciais não pode operar.")

    def save_credentials(self, provider: str, credentials: Dict[str, Any]) -> None:
        """
        Salva as credenciais de um provedor no Vault.

        Args:
            provider: O nome do provedor (ex: 'aws').
            credentials: Um dicionário com as credenciais.
        """
        path = f"secret/data/{provider}_credentials"
        print(f"Salvando credenciais no Vault em: {path}")
        try:
            self.vault_client.secrets.kv.v2.create_or_update_secret(
                path=f"{provider}_credentials",
                secret=credentials,
            )
        except Exception as e:
            print(f"Erro ao salvar credenciais para '{provider}' no Vault: {e}")
            raise

    def get_configured_providers(self) -> List[Dict[str, Any]]:
        """
        Lista os segredos de credenciais configurados no Vault.
        """
        try:
            # Lista todos os segredos no backend 'secret/'
            list_response = self.vault_client.secrets.kv.v2.list_secrets(path='')

            configured_providers = []
            for key in list_response.get('data', {}).get('keys', []):
                if key.endswith('_credentials'):
                    provider_name = key.replace('_credentials', '')
                    configured_providers.append({"provider": provider_name, "configured": True})
            return configured_providers
        except Exception as e:
            print(f"Erro ao listar provedores configurados no Vault: {e}")
            return []

    def delete_credentials(self, provider: str) -> None:
        """
        Deleta as credenciais de um provedor do Vault.
        """
        path = f"{provider}_credentials"
        print(f"Deletando credenciais do Vault em: {path}")
        try:
            self.vault_client.secrets.kv.v2.delete_metadata_and_all_versions(path=path)
        except Exception as e:
            print(f"Erro ao deletar credenciais para '{provider}' no Vault: {e}")
            raise

# Instância do serviço para ser usada pelos controllers
credentials_service = CredentialsService()
