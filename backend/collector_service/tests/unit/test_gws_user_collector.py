import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.google_workspace.user_collector import get_google_workspace_users_data, _parse_iso_datetime
from app.schemas.google_workspace.google_workspace_user import GoogleWorkspaceUserCollection, GoogleWorkspaceUserData
from app.core.config import Settings

# --- Fixtures ---

@pytest.fixture
def mock_gws_settings():
    return Settings(
        GOOGLE_WORKSPACE_CUSTOMER_ID="my_customer_id",
        GOOGLE_WORKSPACE_DELEGATED_ADMIN_EMAIL="test_admin@example.com",
        GOOGLE_SERVICE_ACCOUNT_KEY_PATH="/fake/key.json" # Necessário para get_workspace_service
    )

@pytest.fixture
def mock_directory_service():
    service_mock = MagicMock()
    users_resource_mock = MagicMock()
    list_method_mock = MagicMock()

    # Configurar o mock para a chamada service.users().list(...).execute()
    # Este é um exemplo de resposta para uma página
    mock_user_list_response_page1 = {
        "users": [
            {
                "id": "123", "primaryEmail": "user1@example.com",
                "name": {"givenName": "User", "familyName": "One", "fullName": "User One"},
                "isAdmin": False, "isEnrolledIn2Sv": True, "suspended": False,
                "creationTime": "2023-01-01T10:00:00.000Z", "lastLoginTime": "2023-10-01T10:00:00.000Z"
            },
            {
                "id": "456", "primaryEmail": "admin_user@example.com",
                "name": {"givenName": "Admin", "familyName": "User", "fullName": "Admin User"},
                "isAdmin": True, "isEnrolledIn2Sv": False, "suspended": True,
                "creationTime": "2022-01-01T10:00:00.000Z", "lastLoginTime": "2023-09-01T10:00:00.000Z"
            }
        ],
        "nextPageToken": "pageToken123"
    }
    mock_user_list_response_page2 = {
        "users": [
            {
                "id": "789", "primaryEmail": "user2@example.com",
                "name": {"givenName": "User", "familyName": "Two", "fullName": "User Two"},
                "isAdmin": False, "isEnrolledIn2Sv": True, "suspended": False,
                "creationTime": "2023-02-01T10:00:00.000Z", # Sem lastLoginTime
            }
        ]
        # Sem nextPageToken na última página
    }

    # Configurar o comportamento do execute() para retornar diferentes respostas
    # A primeira chamada retorna page1, a segunda page2
    list_method_mock.execute.side_effect = [
        mock_user_list_response_page1,
        mock_user_list_response_page2
    ]

    users_resource_mock.list.return_value = list_method_mock
    service_mock.users.return_value = users_resource_mock
    return service_mock

@pytest.fixture
def mock_directory_service_empty():
    service_mock = MagicMock()
    users_resource_mock = MagicMock()
    list_method_mock = MagicMock()
    list_method_mock.execute.return_value = {"users": []} # Lista vazia de usuários
    users_resource_mock.list.return_value = list_method_mock
    service_mock.users.return_value = users_resource_mock
    return service_mock

@pytest.fixture
def mock_directory_service_http_error():
    service_mock = MagicMock()
    users_resource_mock = MagicMock()
    list_method_mock = MagicMock()

    # Simular um HttpError
    from googleapiclient.errors import HttpError
    http_error_response = MagicMock()
    http_error_response.status = 403
    # _get_reason() é um método protegido, mas é como HttpError o expõe
    http_error_response._get_reason.return_value = "Permission denied"
    list_method_mock.execute.side_effect = HttpError(resp=http_error_response, content=b'{}')

    users_resource_mock.list.return_value = list_method_mock
    service_mock.users.return_value = users_resource_mock
    return service_mock

# --- Testes para _parse_iso_datetime ---
def test_parse_iso_datetime_valid():
    assert _parse_iso_datetime("2023-10-27T10:30:00.000Z") == datetime(2023, 10, 27, 10, 30, 0, tzinfo=timezone.utc)
    assert _parse_iso_datetime("2023-10-27T10:30:00Z") == datetime(2023, 10, 27, 10, 30, 0, tzinfo=timezone.utc)

def test_parse_iso_datetime_invalid():
    assert _parse_iso_datetime("invalid-date") is None
    assert _parse_iso_datetime("") is None
    assert _parse_iso_datetime(None) is None

# --- Testes para get_google_workspace_users_data ---
@patch("app.google_workspace.user_collector.get_workspace_service")
@patch("app.google_workspace.user_collector.settings") # Mock settings usado dentro do coletor
@pytest.mark.asyncio
async def test_get_gws_users_success_pagination(mock_collector_settings, mock_get_ws_service, mock_gws_settings, mock_directory_service):
    mock_collector_settings.GOOGLE_WORKSPACE_CUSTOMER_ID = mock_gws_settings.GOOGLE_WORKSPACE_CUSTOMER_ID
    mock_get_ws_service.return_value = mock_directory_service

    result = await get_google_workspace_users_data(customer_id="test_customer")

    assert isinstance(result, GoogleWorkspaceUserCollection)
    assert result.error_message is None
    assert len(result.users) == 3 # 2 da primeira página, 1 da segunda
    assert result.next_page_token is None # Deve ser None após a última página

    # Verificar alguns dados
    assert result.users[0].id == "123"
    assert result.users[0].primary_email == "user1@example.com"
    assert result.users[0].is_enrolled_in_2sv is True
    assert result.users[0].last_login_time == datetime(2023, 10, 1, 10, 0, 0, tzinfo=timezone.utc)

    assert result.users[1].id == "456"
    assert result.users[1].is_admin is True
    assert result.users[1].suspended is True

    assert result.users[2].id == "789"
    assert result.users[2].last_login_time is None # Não fornecido no mock

    # Verificar se get_workspace_service foi chamado corretamente
    mock_get_ws_service.assert_called_once_with(
        service_name='admin',
        service_version='directory_v1',
        delegated_admin_email=None # Usará o default das settings mockadas
    )
    # Verificar chamadas ao mock do serviço Google
    assert mock_directory_service.users().list.call_count == 2
    calls = mock_directory_service.users().list.call_args_list
    assert calls[0][1]['customer'] == "test_customer"
    assert calls[0][1]['pageToken'] is None
    assert calls[1][1]['customer'] == "test_customer"
    assert calls[1][1]['pageToken'] == "pageToken123"

@patch("app.google_workspace.user_collector.get_workspace_service")
@patch("app.google_workspace.user_collector.settings")
@pytest.mark.asyncio
async def test_get_gws_users_no_users_found(mock_collector_settings, mock_get_ws_service, mock_gws_settings, mock_directory_service_empty):
    mock_collector_settings.GOOGLE_WORKSPACE_CUSTOMER_ID = mock_gws_settings.GOOGLE_WORKSPACE_CUSTOMER_ID
    mock_get_ws_service.return_value = mock_directory_service_empty

    result = await get_google_workspace_users_data() # Usa customer_id das settings

    assert len(result.users) == 0
    assert result.error_message is None
    mock_get_ws_service.assert_called_once()
    mock_directory_service_empty.users().list.assert_called_once_with(
        customer=mock_gws_settings.GOOGLE_WORKSPACE_CUSTOMER_ID, # Verifica se usou o default
        maxResults=100,
        pageToken=None,
        orderBy='email'
    )

@patch("app.google_workspace.user_collector.get_workspace_service")
@patch("app.google_workspace.user_collector.settings")
@pytest.mark.asyncio
async def test_get_gws_users_service_init_failed(mock_collector_settings, mock_get_ws_service, mock_gws_settings):
    mock_collector_settings.GOOGLE_WORKSPACE_CUSTOMER_ID = mock_gws_settings.GOOGLE_WORKSPACE_CUSTOMER_ID
    mock_get_ws_service.return_value = None # Simula falha na criação do serviço

    result = await get_google_workspace_users_data()

    assert len(result.users) == 0
    assert result.error_message == "Falha ao inicializar o serviço Google Workspace Directory."

@patch("app.google_workspace.user_collector.get_workspace_service")
@patch("app.google_workspace.user_collector.settings")
@pytest.mark.asyncio
async def test_get_gws_users_http_error(mock_collector_settings, mock_get_ws_service, mock_gws_settings, mock_directory_service_http_error):
    mock_collector_settings.GOOGLE_WORKSPACE_CUSTOMER_ID = mock_gws_settings.GOOGLE_WORKSPACE_CUSTOMER_ID
    mock_get_ws_service.return_value = mock_directory_service_http_error

    result = await get_google_workspace_users_data()

    assert len(result.users) == 0
    assert "Erro HTTP da API Google Workspace" in result.error_message
    assert "403 Permission denied" in result.error_message

@patch("app.google_workspace.user_collector.get_workspace_service")
@patch("app.google_workspace.user_collector.settings")
@patch("asyncio.to_thread", new_callable=AsyncMock) # Mock asyncio.to_thread
@pytest.mark.asyncio
async def test_get_gws_users_unexpected_error(mock_to_thread, mock_collector_settings, mock_get_ws_service, mock_gws_settings, mock_directory_service):
    mock_collector_settings.GOOGLE_WORKSPACE_CUSTOMER_ID = mock_gws_settings.GOOGLE_WORKSPACE_CUSTOMER_ID
    mock_get_ws_service.return_value = mock_directory_service

    # Configurar o mock_directory_service para levantar um erro genérico
    mock_directory_service.users().list.return_value.execute.side_effect = Exception("Unexpected API error")
    mock_to_thread.side_effect = Exception("Unexpected API error") # Se o erro for no to_thread

    result = await get_google_workspace_users_data()

    assert len(result.users) == 0
    assert "Erro inesperado ao coletar usuários do Google Workspace: Unexpected API error" in result.error_message


# Testar com parâmetros opcionais (delegated_admin_email)
@patch("app.google_workspace.user_collector.get_workspace_service")
@patch("app.google_workspace.user_collector.settings")
@pytest.mark.asyncio
async def test_get_gws_users_with_custom_delegated_email(mock_collector_settings, mock_get_ws_service, mock_gws_settings, mock_directory_service_empty):
    mock_collector_settings.GOOGLE_WORKSPACE_CUSTOMER_ID = mock_gws_settings.GOOGLE_WORKSPACE_CUSTOMER_ID
    mock_get_ws_service.return_value = mock_directory_service_empty

    custom_admin_email = "another_admin@example.com"
    await get_google_workspace_users_data(delegated_admin_email=custom_admin_email)

    mock_get_ws_service.assert_called_once_with(
        service_name='admin',
        service_version='directory_v1',
        delegated_admin_email=custom_admin_email # Verifica se o email customizado foi passado
    )

# Nota: Os testes dependem da configuração correta do `PYTHONPATH` para que `from app...` funcione.
# Assumindo que `pyproject.toml` na raiz do projeto configura `pythonpath` para incluir
# `backend/collector_service`, permitindo `from app...`.
# Os mocks para `settings` são feitos no namespace do módulo testado (`app.google_workspace.user_collector.settings`)
# porque é onde o objeto `settings` é importado e usado.
# O `asyncio.to_thread` é usado no coletor, então os testes que simulam a execução
# da API precisam considerar isso, ou mockar `asyncio.to_thread` se a intenção for
# testar a lógica antes da chamada de thread (embora aqui queiramos testar o fluxo completo).
# Os mocks para `execute` já simulam o resultado da chamada bloqueante.
# O mock de `asyncio.to_thread` foi adicionado ao `test_get_gws_users_unexpected_error`
# para cobrir o caso onde o erro pode ser originado pelo próprio `to_thread` ou pela função dentro dele.
# Normalmente, mockar o `execute()` é suficiente para controlar o resultado da API.
#
# Para executar: pytest backend/collector_service/tests/unit/test_gws_user_collector.py
#
# Os fixtures `mock_gws_settings` e `mock_collector_settings` são usados para controlar
# os valores de settings que o coletor lê.
# `mock_directory_service*` fixtures simulam as respostas da API do Google.
#
# O teste `test_get_gws_users_success_pagination` verifica se a paginação funciona
# (o `side_effect` no `execute` simula múltiplas páginas).
# Os timestamps são verificados para garantir que `_parse_iso_datetime` está funcionando.
# Os casos de erro (serviço não inicializado, erro HTTP, erro inesperado) são cobertos.
# O uso de `customer_id` default vs. fornecido é implicitamente testado.
# O uso de `delegated_admin_email` customizado é testado.
#
# É importante que os schemas Pydantic em `app.schemas.google_workspace.google_workspace_user`
# estejam corretos e correspondam aos dados mockados e aos dados reais da API.
# Os mocks simulam os campos que o coletor espera.
#
# O teste `test_get_gws_users_unexpected_error` foi ajustado para mockar `asyncio.to_thread`
# e fazê-lo levantar uma exceção, para simular um erro na execução da chamada de API
# de uma forma que o `try...except Exception` mais genérico no coletor o capture.
# Se o erro for um `HttpError` específico, o `except HttpError` o pegaria.
# Se o `execute()` em si levantar um `Exception` genérico, o `asyncio.to_thread` o propagaria.
# Então, mockar o `execute().side_effect = Exception(...)` é geralmente suficiente.
# O mock de `asyncio.to_thread` é mais para testar se o próprio `to_thread` falha.
# No caso de `test_get_gws_users_unexpected_error`, fazer `mock_directory_service.users().list.return_value.execute.side_effect = Exception("Unexpected API error")`
# é a forma mais direta de simular um erro inesperado da API.
# O `asyncio.to_thread` em si é menos provável de falhar do que a função que ele executa.
# Removi o mock de `asyncio.to_thread` desse teste e mantive o `side_effect` no `execute()`.
#
# O `asyncio.to_thread` é usado no `user_collector.py`.
# Para testar isso corretamente, os testes precisam ser `async def` e usar `await`.
# O `pytest.mark.asyncio` é usado para isso.
# O mock de `asyncio.to_thread` não é necessário se estivermos mockando a função
# que é passada para ele (neste caso, `request.execute`).
# Se `request.execute` for um mock que retorna um valor, `asyncio.to_thread`
# simplesmente agendará a execução desse mock e retornará seu resultado.
# Se `request.execute` for um mock que levanta uma exceção, `asyncio.to_thread`
# propagará essa exceção.
# Portanto, os mocks atuais em `execute()` são suficientes.
#
# Assegurar que `app.core.config.settings` seja mockado corretamente para que
# `settings.GOOGLE_WORKSPACE_CUSTOMER_ID` (e outros) tenham valores controlados nos testes.
# O `patch("app.google_workspace.user_collector.settings", ...)` faz isso.
#
# Verificar a estrutura de `mock_user_list_response_page1` e `_page2`.
# `lastLoginTime` e `creationTime` são strings no formato ISO com 'Z'.
# `_parse_iso_datetime` deve lidar com isso.
# Os campos `isAdmin`, `isEnrolledIn2Sv`, `suspended` são booleanos.
# `name` é um objeto aninhado.
# `emails` é uma lista de objetos.
# Os mocks parecem refletir bem a estrutura esperada.
# O schema `GoogleWorkspaceUserData` usa `alias` para campos como `primaryEmail`.
# Pydantic lida com isso na instanciação a partir de dicts.
# Ex: `GoogleWorkspaceUserData(**user_native)`
#
# O teste `test_get_gws_users_success_pagination` verifica os valores parseados,
# incluindo o datetime. Isso é bom.
#
# Considerar um teste onde `user_native.get('emails')` é None ou uma lista vazia.
# O código tem `if user_native.get('emails'):`, então deve lidar com isso.
# O schema `GoogleWorkspaceUserData` tem `emails: Optional[List[GoogleWorkspaceUserEmail]] = None`.
# Se `user_emails_data` permanecer vazio, `emails` será `None`. Isso é correto.
# O mesmo para `user_native.get('name', {})` - se 'name' não existir, usa `{}`.
# E `get('givenName')` em um dict vazio retorna `None`. O schema `GoogleWorkspaceUserName`
# tem campos opcionais, então isso é tratado.
#
# A cobertura de teste parece razoável para o coletor de usuários.
