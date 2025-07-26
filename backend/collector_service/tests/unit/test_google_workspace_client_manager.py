import pytest
from unittest.mock import patch, MagicMock
import os

# Importar o módulo a ser testado
from ..app.google_workspace.google_workspace_client_manager import get_workspace_service, DEFAULT_SCOPES
from app.core.config import Settings # Para mockar settings

# Simular as settings
@pytest.fixture
def mock_settings_valid():
    settings = Settings(
        GOOGLE_SERVICE_ACCOUNT_KEY_PATH="/fake/path/to/key.json",
        GOOGLE_WORKSPACE_DELEGATED_ADMIN_EMAIL="admin@example.com"
    )
    return settings

@pytest.fixture
def mock_settings_invalid_path():
    settings = Settings(
        GOOGLE_SERVICE_ACCOUNT_KEY_PATH="/invalid/path/key.json", # Caminho não existe
        GOOGLE_WORKSPACE_DELEGATED_ADMIN_EMAIL="admin@example.com"
    )
    return settings

@pytest.fixture
def mock_settings_missing_email():
    settings = Settings(
        GOOGLE_SERVICE_ACCOUNT_KEY_PATH="/fake/path/to/key.json",
        GOOGLE_WORKSPACE_DELEGATED_ADMIN_EMAIL=None # Email ausente
    )
    return settings

@pytest.fixture
def mock_settings_missing_key_path():
    settings = Settings(
        GOOGLE_SERVICE_ACCOUNT_KEY_PATH=None, # Caminho da chave ausente
        GOOGLE_WORKSPACE_DELEGATED_ADMIN_EMAIL="admin@example.com"
    )
    return settings

# Testes para get_workspace_service
@patch("app.google_workspace.google_workspace_client_manager.settings")
@patch("google.oauth2.service_account.Credentials.from_service_account_file")
@patch("googleapiclient.discovery.build")
@patch("os.path.exists")
def test_get_workspace_service_success(mock_os_path_exists, mock_build, mock_from_service_account_file, mock_app_settings, mock_settings_valid):
    mock_app_settings.return_value = mock_settings_valid # Mock global das settings
    # Precisa mockar o settings importado diretamente no google_workspace_client_manager
    with patch('app.google_workspace.google_workspace_client_manager.settings', mock_settings_valid):
        mock_os_path_exists.return_value = True # Simula que o arquivo de chave existe
        mock_creds = MagicMock()
        mock_from_service_account_file.return_value = mock_creds
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        service = get_workspace_service("admin", "directory_v1")

        assert service == mock_service
        mock_from_service_account_file.assert_called_once_with(
            mock_settings_valid.GOOGLE_SERVICE_ACCOUNT_KEY_PATH,
            scopes=DEFAULT_SCOPES,
            subject=mock_settings_valid.GOOGLE_WORKSPACE_DELEGATED_ADMIN_EMAIL
        )
        mock_build.assert_called_once_with("admin", "directory_v1", credentials=mock_creds, cache_discovery=False)

@patch("app.google_workspace.google_workspace_client_manager.settings")
@patch("os.path.exists")
def test_get_workspace_service_key_path_not_configured(mock_os_path_exists, mock_app_settings, mock_settings_missing_key_path):
    with patch('app.google_workspace.google_workspace_client_manager.settings', mock_settings_missing_key_path):
        service = get_workspace_service("admin", "directory_v1")
        assert service is None
        mock_os_path_exists.assert_not_called() # Não deve nem tentar verificar o caminho

@patch("app.google_workspace.google_workspace_client_manager.settings")
@patch("os.path.exists")
def test_get_workspace_service_key_file_not_found(mock_os_path_exists, mock_app_settings, mock_settings_valid):
    with patch('app.google_workspace.google_workspace_client_manager.settings', mock_settings_valid):
        mock_os_path_exists.return_value = False # Simula que o arquivo de chave NÃO existe
        service = get_workspace_service("admin", "directory_v1")
        assert service is None
        mock_os_path_exists.assert_called_once_with(mock_settings_valid.GOOGLE_SERVICE_ACCOUNT_KEY_PATH)

@patch("app.google_workspace.google_workspace_client_manager.settings")
@patch("os.path.exists")
def test_get_workspace_service_admin_email_not_configured(mock_os_path_exists, mock_app_settings, mock_settings_missing_email):
     with patch('app.google_workspace.google_workspace_client_manager.settings', mock_settings_missing_email):
        mock_os_path_exists.return_value = True # Assume que o path da chave é válido
        service = get_workspace_service("admin", "directory_v1")
        assert service is None

@patch("app.google_workspace.google_workspace_client_manager.settings")
@patch("google.oauth2.service_account.Credentials.from_service_account_file")
@patch("googleapiclient.discovery.build")
@patch("os.path.exists")
def test_get_workspace_service_build_exception(mock_os_path_exists, mock_build, mock_from_service_account_file, mock_app_settings, mock_settings_valid):
    with patch('app.google_workspace.google_workspace_client_manager.settings', mock_settings_valid):
        mock_os_path_exists.return_value = True
        mock_from_service_account_file.return_value = MagicMock()
        mock_build.side_effect = Exception("API build failed")

        service = get_workspace_service("admin", "directory_v1")
        assert service is None

@patch("app.google_workspace.google_workspace_client_manager.settings")
@patch("google.oauth2.service_account.Credentials.from_service_account_file")
@patch("googleapiclient.discovery.build")
@patch("os.path.exists")
def test_get_workspace_service_uses_provided_params_over_settings(mock_os_path_exists, mock_build, mock_from_service_account_file, mock_app_settings, mock_settings_valid):
    # As settings globais são mock_settings_valid (admin@example.com, /fake/path/to/key.json)
    with patch('app.google_workspace.google_workspace_client_manager.settings', mock_settings_valid):
        mock_os_path_exists.return_value = True
        mock_creds = MagicMock()
        mock_from_service_account_file.return_value = mock_creds
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        custom_key_path = "/custom/key.json"
        custom_admin_email = "custom_admin@example.com"
        custom_scopes = ["https://www.googleapis.com/auth/drive.readonly"]

        service = get_workspace_service(
            "drive", "v3",
            delegated_admin_email=custom_admin_email,
            service_account_key_path=custom_key_path,
            scopes=custom_scopes
        )

        assert service == mock_service
        mock_from_service_account_file.assert_called_once_with(
            custom_key_path, # Deve usar o custom_key_path
            scopes=custom_scopes, # Deve usar os custom_scopes
            subject=custom_admin_email # Deve usar o custom_admin_email
        )
        mock_build.assert_called_once_with("drive", "v3", credentials=mock_creds, cache_discovery=False)
        mock_os_path_exists.assert_called_once_with(custom_key_path)

# Testar o cache lru_cache
@patch("app.google_workspace.google_workspace_client_manager.settings")
@patch("google.oauth2.service_account.Credentials.from_service_account_file")
@patch("googleapiclient.discovery.build")
@patch("os.path.exists")
def test_get_workspace_service_caching(mock_os_path_exists, mock_build, mock_from_service_account_file, mock_app_settings, mock_settings_valid):
    with patch('app.google_workspace.google_workspace_client_manager.settings', mock_settings_valid):
        mock_os_path_exists.return_value = True
        mock_from_service_account_file.return_value = MagicMock()

        # Limpar o cache antes do teste para garantir que está testando o cache da função
        get_workspace_service.cache_clear()

        # Chamada 1
        mock_build.return_value = MagicMock(name="service1")
        service1 = get_workspace_service("admin", "directory_v1")
        assert mock_build.call_count == 1

        # Chamada 2 (mesmos args, deve usar cache)
        service2 = get_workspace_service("admin", "directory_v1")
        assert mock_build.call_count == 1 # Não deve ter chamado build novamente
        assert service1 == service2

        # Chamada 3 (args diferentes, não deve usar cache)
        mock_build.return_value = MagicMock(name="service3")
        service3 = get_workspace_service("drive", "v3")
        assert mock_build.call_count == 2 # Deve ter chamado build novamente
        assert service3 is not service1

        # Chamada 4 (mesmos args da chamada 3, deve usar cache)
        service4 = get_workspace_service("drive", "v3")
        assert mock_build.call_count == 2
        assert service3 == service4

        get_workspace_service.cache_clear() # Limpar após o teste
