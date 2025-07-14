import msal
import httpx
import logging
from typing import Optional, Dict, Any
from app.core.config import settings # Supondo que settings terá M365_CLIENT_ID, M365_CLIENT_SECRET, M365_TENANT_ID

logger = logging.getLogger(__name__)

# Constantes para Microsoft Graph API
GRAPH_API_BASE_URL = "https://graph.microsoft.com/v1.0"
# Para escopos de permissão de aplicativo (client credentials flow)
DEFAULT_GRAPH_SCOPES = ["https://graph.microsoft.com/.default"]


class M365ClientManager:
    _instance = None
    _app = None
    _access_token_info: Optional[Dict[str, Any]] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(M365ClientManager, cls).__new__(cls)
            try:
                cls._app = msal.ConfidentialClientApplication(
                    client_id=settings.M365_CLIENT_ID,
                    authority=f"https://login.microsoftonline.com/{settings.M365_TENANT_ID}",
                    client_credential=settings.M365_CLIENT_SECRET,
                    # token_cache=msal.SerializableTokenCache() # Opcional: para cache de token persistente
                )
                logger.info("MSAL ConfidentialClientApplication initialized for M365.")
            except AttributeError as e:
                logger.error(f"M365 settings (M365_CLIENT_ID, M365_TENANT_ID, M365_CLIENT_SECRET) missing or msal not available: {e}")
                cls._app = None # Garante que não tentaremos usar um app não inicializado
            except Exception as e:
                logger.error(f"Failed to initialize MSAL ConfidentialClientApplication: {e}")
                cls._app = None
        return cls._instance

    def get_access_token(self) -> Optional[str]:
        """
        Obtém um token de acesso para a API Microsoft Graph usando client credentials flow.
        Gerencia o cache de token simples (apenas em memória para esta instância).
        """
        if not self._app:
            logger.error("M365ClientManager not properly initialized. Cannot get access token.")
            return None

        if self._access_token_info and msal. সময়ের.is_token_expired(self._access_token_info):
            logger.info("M365 access token expired. Attempting to refresh/acquire new one.")
            self._access_token_info = None # Forçar aquisição de novo token

        if not self._access_token_info:
            logger.info("No valid M365 access token found, acquiring new one.")
            # Tenta obter da cache primeiro (se configurado e o token estiver lá)
            # accounts = self._app.get_accounts() # Não relevante para client_credentials
            # if accounts:
            #     result = self._app.acquire_token_silent(scopes=DEFAULT_GRAPH_SCOPES, account=accounts[0])
            #     if result:
            #         self._access_token_info = result
            #         logger.info("M365 access token acquired silently from cache.")

            # Se não estiver na cache ou o fluxo silencioso falhar, adquirir novo
            if not self._access_token_info:
                result = self._app.acquire_token_for_client(scopes=DEFAULT_GRAPH_SCOPES)
                if "access_token" in result:
                    self._access_token_info = result
                    # expires_in = result.get("expires_in", 3600)
                    # logger.info(f"New M365 access token acquired, expires in {expires_in} seconds.")
                    logger.info("New M365 access token acquired.")
                else:
                    error_details = result.get("error_description", "No error description provided.")
                    logger.error(f"Failed to acquire M365 access token: {result.get('error')} - {error_details}")
                    return None

        return self._access_token_info.get("access_token")

    async def get_graph_client(self) -> Optional[httpx.AsyncClient]:
        """
        Retorna um cliente httpx.AsyncClient configurado com o token de acesso do Graph API.
        Retorna None se o token não puder ser obtido.
        """
        access_token = self.get_access_token()
        if not access_token:
            return None

        return httpx.AsyncClient(
            base_url=GRAPH_API_BASE_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            timeout=settings.M365_HTTP_CLIENT_TIMEOUT or 20.0, # Adicionar M365_HTTP_CLIENT_TIMEOUT às settings
        )

# Instância singleton
m365_client_manager = M365ClientManager()

# Exemplo de como usar (em um coletor):
# async def example_graph_call():
#     graph_client = await m365_client_manager.get_graph_client()
#     if not graph_client:
#         # Lidar com erro de autenticação
#         return None
#     try:
#         async with graph_client: # Garante que o cliente é fechado
#             response = await graph_client.get("/users?$select=displayName,userPrincipalName")
#             response.raise_for_status()
#             return response.json()
#     except httpx.HTTPStatusError as e:
#         logger.error(f"Graph API request failed: {e.response.status_code} - {e.response.text}")
#         return None
#     except Exception as e:
#         logger.error(f"Unexpected error during Graph API call: {e}")
#         return None

if __name__ == "__main__":
    # Teste local rápido (requer M365_CLIENT_ID, M365_TENANT_ID, M365_CLIENT_SECRET nas settings)
    # E que as settings sejam carregáveis aqui (ex: via .env na raiz do collector_service)

    # Mock settings para teste local se config.py não estiver totalmente configurado ou .env não presente
    class MockM365Settings:
        M365_CLIENT_ID = "SEU_M365_CLIENT_ID"
        M365_TENANT_ID = "SEU_M365_TENANT_ID"
        M365_CLIENT_SECRET = "SEU_M365_CLIENT_SECRET"
        M365_HTTP_CLIENT_TIMEOUT = 30

    # Descomentar e preencher para testar localmente:
    # settings.M365_CLIENT_ID = MockM365Settings.M365_CLIENT_ID
    # settings.M365_TENANT_ID = MockM365Settings.M365_TENANT_ID
    # settings.M365_CLIENT_SECRET = MockM365Settings.M365_CLIENT_SECRET
    # settings.M365_HTTP_CLIENT_TIMEOUT = MockM365Settings.M365_HTTP_CLIENT_TIMEOUT

    if not all([settings.M365_CLIENT_ID, settings.M365_TENANT_ID, settings.M365_CLIENT_SECRET]):
        print("M365 settings (M365_CLIENT_ID, M365_TENANT_ID, M365_CLIENT_SECRET) not configured in settings. Skipping M365 client test.")
    else:
        print("Attempting to get M365 access token...")
        token = m365_client_manager.get_access_token()
        if token:
            print(f"Successfully obtained M365 access token (first ~20 chars): {token[:20]}...")
            # Teste adicional: tentar uma chamada simples (requer permissões apropriadas no App Registration)
            # import asyncio
            # async def main_test():
            #     data = await example_graph_call()
            #     if data:
            #         print("Successfully called Graph API. Sample data:")
            #         print(data.get("value", [])[:2]) # Primeiros 2 usuários
            #     else:
            #         print("Failed to call Graph API.")
            # asyncio.run(main_test())
        else:
            print("Failed to obtain M365 access token. Check credentials and MSAL App Registration permissions.")
