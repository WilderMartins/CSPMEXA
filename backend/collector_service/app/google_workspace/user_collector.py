from typing import List, Optional
from googleapiclient.errors import HttpError
from app.google_workspace.google_workspace_client_manager import get_workspace_service
from app.schemas.google_workspace.google_workspace_user import (
    GoogleWorkspaceUserData,
    GoogleWorkspaceUserName,
    GoogleWorkspaceUserEmail,
    GoogleWorkspaceUserCollection
)
from app.core.config import settings # Para obter customer_id default
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

def _parse_iso_datetime(timestamp_str: Optional[str]) -> Optional[datetime]:
    if not timestamp_str:
        return None
    try:
        # Exemplo de formato: "2023-10-27T10:30:00.000Z"
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError) as e:
        logger.warning(f"Could not parse Google Workspace timestamp string '{timestamp_str}': {e}")
        return None

async def get_google_workspace_users_data(
    customer_id: Optional[str] = None,
    delegated_admin_email: Optional[str] = None,
    max_results_per_page: int = 100 # Default da API é 100, max é 500
) -> GoogleWorkspaceUserCollection:
    """
    Coleta dados de usuários do Google Workspace para um determinado customer_id.
    """
    final_customer_id = customer_id or settings.GOOGLE_WORKSPACE_CUSTOMER_ID
    # delegated_admin_email e service_account_key_path serão pegos das settings
    # se não forem fornecidos aqui, pelo get_workspace_service.

    users_list: List[GoogleWorkspaceUserData] = []
    page_token: Optional[str] = None
    error_msg: Optional[str] = None

    try:
        service = get_workspace_service(
            service_name='admin',
            service_version='directory_v1',
            delegated_admin_email=delegated_admin_email # Passa para o client manager
        )
        if not service:
            error_msg = "Falha ao inicializar o serviço Google Workspace Directory."
            logger.error(error_msg)
            return GoogleWorkspaceUserCollection(users=[], error_message=error_msg)

        logger.info(f"Coletando usuários do Google Workspace para o cliente: {final_customer_id}")

        while True:
            request = service.users().list(
                customer=final_customer_id,
                maxResults=max_results_per_page,
                pageToken=page_token,
                orderBy='email' # Ordenar para resultados consistentes na paginação
            )
            response = await asyncio.to_thread(request.execute) # Executar a chamada bloqueante em um thread

            gws_users = response.get('users', [])
            for user_native in gws_users:
                user_emails_data = []
                if user_native.get('emails'):
                    for email_native in user_native.get('emails', []):
                        user_emails_data.append(GoogleWorkspaceUserEmail(
                            address=email_native.get('address'),
                            primary=email_native.get('primary')
                        ))

                user_data = GoogleWorkspaceUserData(
                    id=user_native.get('id'),
                    primary_email=user_native.get('primaryEmail'),
                    name=GoogleWorkspaceUserName(
                        given_name=user_native.get('name', {}).get('givenName'),
                        family_name=user_native.get('name', {}).get('familyName'),
                        full_name=user_native.get('name', {}).get('fullName')
                    ),
                    is_admin=user_native.get('isAdmin', False),
                    is_delegated_admin=user_native.get('isDelegatedAdmin'),
                    last_login_time=_parse_iso_datetime(user_native.get('lastLoginTime')),
                    creation_time=_parse_iso_datetime(user_native.get('creationTime')),
                    suspended=user_native.get('suspended', False),
                    archived=user_native.get('archived', False),
                    org_unit_path=user_native.get('orgUnitPath'),
                    is_enrolled_in_2sv=user_native.get('isEnrolledIn2Sv', False),
                    emails=user_emails_data if user_emails_data else None
                    # Adicionar mais campos conforme necessário (groups, roles)
                )
                users_list.append(user_data)

            page_token = response.get('nextPageToken')
            if not page_token:
                break

        logger.info(f"Coletados {len(users_list)} usuários do Google Workspace para o cliente {final_customer_id}.")

    except HttpError as e:
        error_msg = f"Erro HTTP da API Google Workspace ao listar usuários: {e.resp.status} {e._get_reason()}"
        logger.error(error_msg, exc_info=True)
    except Exception as e:
        error_msg = f"Erro inesperado ao coletar usuários do Google Workspace: {str(e)}"
        logger.error(error_msg, exc_info=True)

    return GoogleWorkspaceUserCollection(
        users=users_list,
        next_page_token=page_token, # Será None se a coleta terminou ou falhou antes da primeira página
        error_message=error_msg
    )

# Para rodar em um loop asyncio (necessário para asyncio.to_thread)
import asyncio

# Exemplo de como chamar (para teste local, se necessário):
# async def main_test():
#     # Configurar GOOGLE_SERVICE_ACCOUNT_KEY_PATH e GOOGLE_WORKSPACE_DELEGATED_ADMIN_EMAIL
#     # nas settings ou via variáveis de ambiente.
#     # customer_id pode ser 'my_customer' ou um ID específico.
#     customer_id_test = settings.GOOGLE_WORKSPACE_CUSTOMER_ID
#     admin_email_test = settings.GOOGLE_WORKSPACE_DELEGATED_ADMIN_EMAIL
#
#     if not settings.GOOGLE_SERVICE_ACCOUNT_KEY_PATH or not admin_email_test:
#         print("Por favor, configure GOOGLE_SERVICE_ACCOUNT_KEY_PATH e GOOGLE_WORKSPACE_DELEGATED_ADMIN_EMAIL para teste.")
#         return
#
#     print(f"Testando coletor de usuários do Google Workspace para cliente: {customer_id_test} com admin: {admin_email_test}")
#     collection_result = await get_google_workspace_users_data(customer_id=customer_id_test, delegated_admin_email=admin_email_test)
#
#     if collection_result.error_message:
#         print(f"Erro na coleta: {collection_result.error_message}")
#
#     print(f"Total de usuários coletados: {len(collection_result.users)}")
#     for user in collection_result.users[:5]: # Printar os primeiros 5 para exemplo
#         print(f"  ID: {user.id}, Email: {user.primary_email}, Nome: {user.name.full_name}, Admin: {user.is_admin}, 2SV: {user.is_enrolled_in_2sv}")
#
# if __name__ == "__main__":
#     # Para rodar este teste localmente, você precisaria de um loop de eventos asyncio.
#     # Exemplo:
#     # loop = asyncio.get_event_loop()
#     # try:
#     #     loop.run_until_complete(main_test())
#     # finally:
#     #     loop.close()
#     # Ou simplesmente:
#     # asyncio.run(main_test()) # Python 3.7+
#     pass

# Observações:
# - O client manager (`google_workspace_client_manager.py`) já lida com a criação do serviço
#   Google API usando Service Account com impersonação.
# - A função `get_google_workspace_users_data` usa `asyncio.to_thread` para executar a chamada
#   bloqueante `request.execute()` da biblioteca cliente do Google em um thread separado,
#   para não bloquear o loop de eventos do FastAPI.
# - A paginação é tratada com `pageToken` e `nextPageToken`.
# - O schema `GoogleWorkspaceUserCollection` é usado para encapsular a lista de usuários
#   e qualquer mensagem de erro global ou token de paginação.
# - A função `_parse_iso_datetime` foi adicionada para converter timestamps da API do Google.
# - Escopos necessários estão definidos no client manager. O coletor de usuários precisa
#   principalmente de `https.www.googleapis.com/auth/admin.directory.user.readonly`.
# - O `customer_id` e `delegated_admin_email` podem ser passados como argumentos ou
#   serão pegos das `settings` (que, por sua vez, podem vir de variáveis de ambiente).
# - O `error_details` no `GoogleWorkspaceUserData` seria para erros ao processar um usuário específico
#   após a listagem, o que é menos comum para este tipo de coleta de lista. O `error_message`
#   no `GoogleWorkspaceUserCollection` é para erros mais globais na chamada da API.
#
# Este coletor forma a base para obter dados de usuários do Google Workspace.
# Próximos passos poderiam incluir coletores para Drive, Gmail, etc.
# e as respectivas políticas no policy-engine-service.
#
# É importante garantir que a Service Account usada tenha a "Delegação em todo o Domínio"
# habilitada no Google Workspace Admin Console e que os escopos OAuth necessários
# estejam autorizados para essa Service Account.
# O `delegated_admin_email` deve ser um e-mail de um superadministrador ou um administrador
# com as permissões necessárias para ler os dados dos usuários.
# O arquivo de chave JSON da Service Account (`GOOGLE_SERVICE_ACCOUNT_KEY_PATH`) deve estar
# acessível para a aplicação.
#
# Fim do arquivo.
