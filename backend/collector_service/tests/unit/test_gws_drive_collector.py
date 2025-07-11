import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.google_workspace.drive_collector import (
    get_google_drive_shared_drives_data,
    get_google_drive_public_files_data, # Embora MVP seja informativo, testar a chamada
    _get_file_permissions,
    _analyze_file_sharing
)
from app.schemas.google_workspace.google_drive_shared_drive import SharedDriveData, DriveRestrictions, SharedDriveCapabilities
from app.schemas.google_workspace.google_drive_file import DriveFileData, DriveFileOwner
from app.schemas.google_workspace.google_drive_permission import DrivePermission
from app.core.config import Settings # Para mockar settings

# --- Fixtures ---

@pytest.fixture
def mock_gws_drive_settings(): # Similar ao de user_collector, mas pode ser específico se necessário
    return Settings(
        GOOGLE_WORKSPACE_CUSTOMER_ID="test_customer_drive",
        GOOGLE_WORKSPACE_DELEGATED_ADMIN_EMAIL="drive_admin@example.com",
        GOOGLE_SERVICE_ACCOUNT_KEY_PATH="/fake/drive_key.json"
    )

@pytest.fixture
def mock_drive_service_shared_drives():
    service_mock = MagicMock()
    drives_resource_mock = MagicMock()
    drives_list_method_mock = MagicMock()

    mock_drives_response = {
        "drives": [
            {
                "id": "drive1_id", "name": "Marketing Drive", "createdTime": "2023-01-01T10:00:00.000Z",
                "restrictions": {"domainUsersOnly": False, "driveMembersOnly": False},
                "capabilities": {"canShare": True}
            },
            {
                "id": "drive2_id", "name": "Eng Drive", "createdTime": "2023-02-01T10:00:00.000Z",
                "restrictions": {"domainUsersOnly": True, "driveMembersOnly": True}, # Mais restrito
                "capabilities": {"canShare": False}
            }
        ],
        "nextPageToken": None # Sem paginação para drives neste mock
    }
    drives_list_method_mock.execute.return_value = mock_drives_response
    drives_resource_mock.list.return_value = drives_list_method_mock
    service_mock.drives.return_value = drives_resource_mock

    # Mock para files().list() - inicialmente vazio, será configurado por teste se necessário
    files_resource_mock = MagicMock()
    files_list_method_mock = MagicMock()
    files_list_method_mock.execute.return_value = {"files": [], "nextPageToken": None} # Default sem arquivos
    files_resource_mock.list.return_value = files_list_method_mock
    service_mock.files.return_value = files_resource_mock

    # Mock para permissions().list() - inicialmente vazio
    permissions_resource_mock = MagicMock()
    permissions_list_method_mock = MagicMock()
    permissions_list_method_mock.execute.return_value = {"permissions": [], "nextPageToken": None} # Default sem permissões
    permissions_resource_mock.list.return_value = permissions_list_method_mock
    service_mock.permissions.return_value = permissions_resource_mock

    return service_mock

# --- Testes para _get_file_permissions ---
@patch("app.google_workspace.drive_collector.asyncio.to_thread", new_callable=AsyncMock) # Mock to_thread
@pytest.mark.asyncio
async def test_get_file_permissions_success(mock_async_to_thread, mock_drive_service_shared_drives):
    # Configurar o mock para permissions().list().execute()
    mock_permissions_response = {
        "permissions": [
            {"id": "perm1", "type": "user", "role": "writer", "emailAddress": "user@example.com"},
            {"id": "perm2", "type": "anyone", "role": "reader", "allowFileDiscovery": False} # Link shared
        ]
    }
    # mock_drive_service_shared_drives.permissions().list().execute.return_value = mock_permissions_response
    # Precisamos garantir que o mock_async_to_thread retorne o resultado do execute mockado
    mock_async_to_thread.return_value = mock_permissions_response


    permissions, error = await _get_file_permissions(mock_drive_service_shared_drives, "file_id_1")

    assert error is None
    assert len(permissions) == 2
    assert permissions[0].type == "user"
    assert permissions[1].type == "anyone"
    assert permissions[1].allow_file_discovery is False

    # Verificar se a chamada à API foi feita corretamente
    mock_drive_service_shared_drives.permissions().list.assert_called_once_with(
        fileId="file_id_1",
        fields=f"nextPageToken, {PERMISSION_FIELDS}",
        pageSize=100,
        pageToken=None,
        supportsAllDrives=True
    )
    mock_async_to_thread.assert_called_once()


# --- Testes para _analyze_file_sharing ---
@pytest.mark.asyncio # Precisa ser async por causa do await _analyze_file_sharing
async def test_analyze_file_sharing():
    file_data = DriveFileData(id="f1", name="Test File", mimeType="text/plain", owners=[]) # owners é obrigatório

    # Caso 1: Público na web
    perms1 = [DrivePermission(id="p1", type="anyone", role="reader", allowFileDiscovery=True)]
    await _analyze_file_sharing(file_data, perms1)
    assert file_data.is_public_on_web is True
    assert file_data.is_shared_with_link is False
    assert "Public on the web (reader)" in file_data.sharing_summary

    # Caso 2: Qualquer um com link
    file_data = DriveFileData(id="f2", name="Test File Link", mimeType="text/plain", owners=[])
    perms2 = [DrivePermission(id="p2", type="anyone", role="reader", allowFileDiscovery=False)]
    await _analyze_file_sharing(file_data, perms2)
    assert file_data.is_public_on_web is False
    assert file_data.is_shared_with_link is True
    assert "Anyone with the link (reader)" in file_data.sharing_summary

    # Caso 3: Compartilhado com domínio
    file_data = DriveFileData(id="f3", name="Test File Domain", mimeType="text/plain", owners=[])
    perms3 = [DrivePermission(id="p3", type="domain", role="commenter", domain="example.com")]
    await _analyze_file_sharing(file_data, perms3)
    assert file_data.is_shared_with_domain is True
    assert "Shared with domain 'example.com' as commenter" in file_data.sharing_summary

    # Caso 4: Sem compartilhamento público/link/domínio, mas shared=True
    file_data = DriveFileData(id="f4", name="Test File Specific", mimeType="text/plain", owners=[], shared=True)
    perms4 = [DrivePermission(id="p4", type="user", role="writer", emailAddress="user@example.com")]
    await _analyze_file_sharing(file_data, perms4)
    assert file_data.is_public_on_web is False
    assert file_data.is_shared_with_link is False
    assert file_data.is_shared_with_domain is False
    assert "Shared with specific users/groups." in file_data.sharing_summary


# --- Testes para get_google_drive_shared_drives_data ---
@patch("app.google_workspace.drive_collector.get_workspace_service")
@patch("app.google_workspace.drive_collector._get_file_permissions") # Mockar a função interna
@patch("app.google_workspace.drive_collector.settings")
@pytest.mark.asyncio
async def test_get_gws_shared_drives_success(mock_collector_settings, mock_get_perms, mock_get_ws_service, mock_gws_drive_settings, mock_drive_service_shared_drives):
    mock_collector_settings.GOOGLE_WORKSPACE_CUSTOMER_ID = mock_gws_drive_settings.GOOGLE_WORKSPACE_CUSTOMER_ID
    mock_get_ws_service.return_value = mock_drive_service_shared_drives

    # Simular que _get_file_permissions não encontra permissões problemáticas
    mock_get_perms.return_value = ([], None)

    # Configurar mock para files().list() para retornar um arquivo por drive
    mock_file_response = {
        "files": [{"id": "file_in_drive_1", "name": "Doc in Drive1", "mimeType": "application/vnd.google-apps.document", "owners": [{"emailAddress":"owner@example.com"}]}],
        "nextPageToken": None
    }
    mock_drive_service_shared_drives.files().list().execute.return_value = mock_file_response

    result = await get_google_drive_shared_drives_data(customer_id="test_customer")

    assert len(result) == 2
    drive1 = result[0]
    assert drive1.id == "drive1_id"
    assert drive1.name == "Marketing Drive"
    assert drive1.restrictions.domain_users_only is False
    assert len(drive1.files_with_problematic_sharing) == 0 # Porque _get_file_permissions mockado não retorna perms problemáticas

    drive2 = result[1]
    assert drive2.id == "drive2_id"
    assert drive2.name == "Eng Drive"
    assert drive2.restrictions.domain_users_only is True

    assert mock_get_ws_service.call_count == 1 # Chamado uma vez para o serviço drive
    # mock_drive_service_shared_drives.drives().list().execute.assert_called_once()
    assert mock_drive_service_shared_drives.drives().list().call_count == 1 # Chamado para listar drives
    # mock_drive_service_shared_drives.files().list().execute.call_count deve ser 2 (um por drive)
    assert mock_drive_service_shared_drives.files().list().call_count == 2
    # mock_get_perms.call_count deve ser 2 (um por arquivo mockado em cada drive)
    assert mock_get_perms.call_count == 2


@patch("app.google_workspace.drive_collector.get_workspace_service")
@patch("app.google_workspace.drive_collector.settings")
@pytest.mark.asyncio
async def test_get_gws_shared_drives_service_init_fail(mock_collector_settings, mock_get_ws_service, mock_gws_drive_settings):
    mock_collector_settings.GOOGLE_WORKSPACE_CUSTOMER_ID = mock_gws_drive_settings.GOOGLE_WORKSPACE_CUSTOMER_ID
    mock_get_ws_service.return_value = None # Falha ao criar serviço

    result = await get_google_drive_shared_drives_data()
    assert len(result) == 1
    assert result[0].id == "ERROR_SERVICE_INIT"

# --- Testes para get_google_drive_public_files_data (MVP informativo) ---
@patch("app.google_workspace.drive_collector.get_workspace_service")
@patch("app.google_workspace.drive_collector.settings")
@pytest.mark.asyncio
async def test_get_gws_public_files_mvp_info_message(mock_collector_settings, mock_get_ws_service, mock_gws_drive_settings, mock_drive_service_shared_drives):
    mock_collector_settings.GOOGLE_WORKSPACE_CUSTOMER_ID = mock_gws_drive_settings.GOOGLE_WORKSPACE_CUSTOMER_ID
    mock_get_ws_service.return_value = mock_drive_service_shared_drives # Mock do serviço, embora não seja muito usado

    result = await get_google_drive_public_files_data()
    assert len(result) == 1
    assert result[0].id == "INFO_DOMAIN_WIDE_PUBLIC_FILES"
    assert "Coleta de todos os arquivos públicos do domínio não implementada otimamente no MVP" in result[0].error_details

# Adicionar mais testes:
# - Erros HTTP ao listar drives ou arquivos.
# - Paginação para arquivos dentro de drives.
# - Arquivos com diferentes tipos de permissões para testar _analyze_file_sharing mais a fundo
#   quando chamado por get_google_drive_shared_drives_data.
# - Caso onde _get_file_permissions retorna um erro.
#
# Estes testes focam no coletor do Drive. Os testes para o client_manager e para as políticas do Drive
# são/serão em arquivos separados.
#
# Nota sobre `asyncio.to_thread`:
# Os testes mockam a chamada `execute()` que é passada para `asyncio.to_thread`.
# Se `execute()` for um mock síncrono, `asyncio.to_thread(mock.execute)` ainda será assíncrono.
# Para simplificar mocks de funções que usam `to_thread`, pode-se mockar `asyncio.to_thread`
# para que ele chame a função mockada diretamente e retorne seu resultado (ou um `Awaitable`).
# Por exemplo, `mock_async_to_thread.side_effect = lambda func, *args, **kwargs: func(*args, **kwargs)`
# se a func mockada já for uma corrotina ou retornar um Future/Task.
# Se func é síncrona e retorna um valor, e o código faz `await asyncio.to_thread(func)`,
# o mock de `asyncio.to_thread` deve retornar um `Awaitable` que resolva para o valor.
# Ex: `mock_async_to_thread.return_value = asyncio.Future()` e depois `mock_async_to_thread.return_value.set_result(...)`.
# No teste `test_get_file_permissions_success`, `mock_async_to_thread.return_value = mock_permissions_response`
# faz com que `await asyncio.to_thread(...)` retorne diretamente `mock_permissions_response`,
# o que é suficiente para testar a lógica de parseamento após a chamada.
#
# A importação de PERMISSION_FIELDS de onde? Se for uma constante global no módulo, ok.
# Ah, `PERMISSION_FIELDS` é definido no próprio `drive_collector.py`.
#
# Fim do arquivo.
