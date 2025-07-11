import os
from google.oauth2 import service_account
from googleapiclient.discovery import build, Resource
from app.core.config import settings # Usar as settings do collector_service
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

# Escopos OAuth 2.0 necessários para as funcionalidades do MVP
# É uma boa prática definir os escopos mínimos necessários.
DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/admin.directory.user.readonly", # Para coletor de usuários
    "https://www.googleapis.com/auth/admin.reports.audit.readonly",  # Para futuros coletores de logs/atividades
    "https://www.googleapis.com/auth/apps.alerts",                   # Para futuro coletor do Alert Center
    "https://www.googleapis.com/auth/drive.readonly"                 # Para coletor do Google Drive (ler arquivos, drives compartilhados, permissões)
]

@lru_cache(maxsize=10) # Cache para combinações de admin_email, service_name e tuple(scopes)
def get_workspace_service(
    service_name: str, # e.g., 'admin', 'alertcenter'
    service_version: str, # e.g., 'directory_v1', 'v1beta1' (para alertcenter)
    delegated_admin_email: Optional[str] = None,
    service_account_key_path: Optional[str] = None,
    scopes: Optional[List[str]] = None
) -> Optional[Resource]:
    """
    Cria e retorna um objeto de serviço Google API autenticado.

    :param service_name: Nome do serviço API (ex: 'admin', 'alertcenter').
    :param service_version: Versão da API (ex: 'directory_v1', 'reports_v1', 'v1beta1').
    :param delegated_admin_email: Email do administrador para impersonação. Se None, usa o da config.
    :param service_account_key_path: Caminho para o arquivo JSON da chave da Service Account. Se None, usa o da config.
    :param scopes: Lista de escopos OAuth. Se None, usa DEFAULT_SCOPES.
    :return: Objeto de serviço Google API autenticado ou None em caso de erro.
    """
    sa_key_path = service_account_key_path or settings.GOOGLE_SERVICE_ACCOUNT_KEY_PATH
    admin_email = delegated_admin_email or settings.GOOGLE_WORKSPACE_DELEGATED_ADMIN_EMAIL
    final_scopes = scopes or DEFAULT_SCOPES

    if not sa_key_path:
        logger.error("Caminho para a chave da Service Account do Google Workspace não configurado (GOOGLE_SERVICE_ACCOUNT_KEY_PATH).")
        return None
    if not os.path.exists(sa_key_path):
        logger.error(f"Arquivo da chave da Service Account não encontrado em: {sa_key_path}")
        return None
    if not admin_email:
        logger.error("E-mail do administrador delegado do Google Workspace não configurado (GOOGLE_WORKSPACE_DELEGATED_ADMIN_EMAIL).")
        return None
    if not final_scopes:
        logger.error("Nenhum escopo OAuth foi definido para o Google Workspace.")
        return None

    try:
        creds = service_account.Credentials.from_service_account_file(
            sa_key_path,
            scopes=final_scopes,
            subject=admin_email  # Email do usuário para impersonar
        )

        google_service = build(service_name, service_version, credentials=creds, cache_discovery=False)
        logger.info(f"Cliente Google Workspace para {service_name} v{service_version} criado com sucesso para {admin_email}.")
        return google_service
    except Exception as e:
        logger.error(f"Erro ao criar cliente Google Workspace para {service_name} v{service_version} (admin: {admin_email}): {e}", exc_info=True)
        return None

# Exemplo de uso (não executar diretamente aqui):
# directory_service = get_workspace_service('admin', 'directory_v1')
# reports_service = get_workspace_service('admin', 'reports_v1')
# alertcenter_service = get_workspace_service('alertcenter', 'v1beta1')

# Para garantir que o módulo Optional seja importado se não estiver já em uso global
from typing import Optional, List
```

E criar os diretórios e arquivos `__init__.py` necessários.
