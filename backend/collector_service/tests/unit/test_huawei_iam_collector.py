import pytest
from unittest.mock import patch, MagicMock, PropertyMock, AsyncMock
from typing import List, Optional, Any
from datetime import datetime, timezone, timedelta
import os

from app.huawei import huawei_iam_collector
from app.schemas.huawei_iam import HuaweiIAMUserData, HuaweiIAMUserLoginProtect, HuaweiIAMUserAccessKey
from app.core.config import Settings
from huaweicloudsdkcore.exceptions import exceptions as sdk_exceptions
from huaweicloudsdkiam.v3.model import (
    KeystoneListUsersResponse, # Usado para mockar o tipo de resposta da lista
    # UserResult as SdkUserResult, # Removido - causava ImportError
    # KeystoneShowUserResponseBody as SdkUserDetailResult, # Removido - causava ImportError
    LoginProtectResult,
    Credentials as SdkCredentials,
    ListPermanentAccessKeysResponse
)
# Para mockar os objetos retornados dentro das respostas, vamos usar MagicMock ou construir dicts.


# --- Fixtures ---
@pytest.fixture
def mock_huawei_settings() -> Settings:
    return Settings()

@pytest.fixture(autouse=True)
def override_huawei_collector_settings(mock_huawei_settings: Settings):
    with patch('app.huawei.huawei_client_manager._clients_cache', new_callable=dict), \
         patch('app.core.config.settings', mock_huawei_settings): # Patch global settings
            if hasattr(huawei_iam_collector, 'iam_client_cache'): # Cache específico do módulo do coletor
                 huawei_iam_collector.iam_client_cache = None
            yield
            if hasattr(huawei_iam_collector, 'iam_client_cache'):
                 huawei_iam_collector.iam_client_cache = None

@pytest.fixture
def mock_iam_client_v3():
    with patch('app.huawei.huawei_client_manager.get_iam_client') as mock_get_client:
        mock_client_instance = MagicMock()
        mock_client_instance.keystone_list_users = MagicMock()
        mock_client_instance.keystone_show_user = MagicMock()
        mock_client_instance.list_permanent_access_keys = MagicMock()
        # mock_client_instance.list_user_mfa_devices = MagicMock() # Se fôssemos usar
        mock_get_client.return_value = mock_client_instance
        yield mock_client_instance

@pytest.fixture
def mock_huawei_credentials_success_with_domain():
    mock_creds = MagicMock()
    mock_creds.ak = "test_ak_iam"
    mock_creds.sk = "test_sk_iam"
    # Simular que get_huawei_credentials retorna um domain_id (que seria o project_id das credenciais)
    with patch('app.huawei.huawei_client_manager.get_huawei_credentials', return_value=(mock_creds, "domain_from_creds_123")) as mock_creds_func, \
         patch.dict(os.environ, {"HUAWEICLOUD_SDK_DOMAIN_ID": ""}, clear=True): # Garantir que a var de ambiente não interfira
        yield mock_creds_func

@pytest.fixture
def mock_huawei_credentials_success_no_domain_env():
    mock_creds = MagicMock()
    mock_creds.ak = "test_ak_iam"
    mock_creds.sk = "test_sk_iam"
    with patch('app.huawei.huawei_client_manager.get_huawei_credentials', return_value=(mock_creds, "project_as_domain_456")) as mock_creds_func, \
         patch.dict(os.environ, {"HUAWEICLOUD_SDK_DOMAIN_ID": ""}, clear=True): # Limpar var de ambiente
        yield mock_creds_func


# --- Testes para get_huawei_iam_users ---

@pytest.mark.asyncio
async def test_get_huawei_iam_users_no_domain_id_provided_or_found(mock_iam_client_v3):
    # Simular que nem o parâmetro domain_id nem a variável de ambiente HUAWEICLOUD_SDK_DOMAIN_ID são fornecidos
    # e que get_huawei_credentials também não retorna um domain_id (ou o project_id usado como fallback é None)
    with patch('app.huawei.huawei_iam_collector.os.getenv', return_value=None), \
         patch('app.huawei.huawei_client_manager.get_huawei_credentials', return_value=(MagicMock(), None)):

        result = await huawei_iam_collector.get_huawei_iam_users(domain_id=None, region_id="reg-iam")
        assert len(result) == 1
        assert result[0].id == "ERROR_DOMAIN_ID"
        assert "Huawei Cloud Domain ID" in result[0].error_details
        mock_iam_client_v3.keystone_list_users.assert_not_called()


@pytest.mark.asyncio
async def test_get_huawei_iam_users_sdk_error_on_list(mock_huawei_credentials_success_with_domain, mock_iam_client_v3):
    mock_iam_client_v3.keystone_list_users.side_effect = sdk_exceptions.SdkException("IAM.ListError", "Simulated ListUsers SDK failure") # Mantido, SdkException aceita msg e error_code implicitamente se não nomeados
    result = await huawei_iam_collector.get_huawei_iam_users(domain_id="domain_from_creds_123", region_id="reg-iam")
    assert len(result) == 1
    assert result[0].id == "ERROR_LIST_USERS_SDK"
    assert "IAM.ListError: Simulated ListUsers SDK failure" in result[0].error_details


@pytest.mark.asyncio
async def test_get_huawei_iam_users_no_users_returned(mock_huawei_credentials_success_with_domain, mock_iam_client_v3):
    mock_response = MagicMock(spec=KeystoneListUsersResponse)
    mock_response.users = []
    mock_iam_client_v3.keystone_list_users.return_value = mock_response

    result = await huawei_iam_collector.get_huawei_iam_users(domain_id="domain_from_creds_123", region_id="reg-iam")
    assert result == []
    mock_iam_client_v3.keystone_list_users.assert_called_once()


@pytest.mark.asyncio
async def test_get_huawei_iam_users_one_user_details_and_keys(mock_huawei_credentials_success_with_domain, mock_iam_client_v3):
    # Mock para keystone_list_users
    # Criar um objeto mock que se assemelha a SdkUserResult
    user_list_native_mock = MagicMock()
    user_list_native_mock.id = "user-id-1"
    user_list_native_mock.name = "test-iam-user"
    user_list_native_mock.domain_id = "domain_from_creds_123"
    user_list_native_mock.enabled = True

    mock_list_users_response = MagicMock(spec=KeystoneListUsersResponse)
    mock_list_users_response.users = [user_list_native_mock]
    mock_iam_client_v3.keystone_list_users.return_value = mock_list_users_response

    # Mock para keystone_show_user (detalhes)
    # Criar um objeto mock que se assemelha a SdkUserDetailResult (que está dentro de .user)
    mock_user_detail_native_obj = MagicMock()
    mock_user_detail_native_obj.id="user-id-1"
    mock_user_detail_native_obj.name="test-iam-user"
    mock_user_detail_native_obj.domain_id="domain_from_creds_123"
    mock_user_detail_native_obj.enabled=True
    mock_user_detail_native_obj.email="test@example.com"
    mock_user_detail_native_obj.mobile="1234567890"
    mock_user_detail_native_obj.login_protect = LoginProtectResult(enabled=True, verification_method="vmfa")

    mock_show_user_response = MagicMock()
    mock_show_user_response.user = mock_user_detail_native_obj # O SDK retorna um objeto que tem um atributo 'user'
    mock_iam_client_v3.keystone_show_user.return_value = mock_show_user_response

    # Mock para list_permanent_access_keys
    ak_create_time_str = "2023-03-01T08:00:00Z"
    mock_key_native = SdkCredentials(access="AKIAEXAMPLE123", status="Active", create_time=ak_create_time_str, description="Test key")
    mock_list_keys_response = MagicMock(spec=ListPermanentAccessKeysResponse)
    mock_list_keys_response.credentials = [mock_key_native] # credentials é a lista
    mock_iam_client_v3.list_permanent_access_keys.return_value = mock_list_keys_response

    result: List[HuaweiIAMUserData] = await huawei_iam_collector.get_huawei_iam_users(domain_id="domain_from_creds_123", region_id="reg-iam")

    assert len(result) == 1
    user_data = result[0]
    assert user_data.id == "user-id-1"
    assert user_data.name == "test-iam-user"
    assert user_data.domain_id == "domain_from_creds_123"
    assert user_data.enabled is True
    assert user_data.email == "test@example.com"
    assert user_data.phone == "1234567890"

    assert user_data.login_protect is not None
    assert user_data.login_protect.enabled is True
    assert user_data.login_protect.verification_method == "vmfa"

    assert user_data.access_keys is not None
    assert len(user_data.access_keys) == 1
    key_data = user_data.access_keys[0]
    assert key_data.access_key == "AKIAEXAMPLE123" # 'access' é o alias para access_key
    assert key_data.status == "Active"
    assert key_data.create_time == datetime(2023, 3, 1, 8, 0, 0, tzinfo=timezone.utc)

    assert user_data.mfa_devices is None # Não mockamos ListUserMfaDevices explicitamente
    assert user_data.error_details is None

    mock_iam_client_v3.keystone_list_users.assert_called_once()
    mock_iam_client_v3.keystone_show_user.assert_called_once()
    mock_iam_client_v3.list_permanent_access_keys.assert_called_once()


@pytest.mark.asyncio
async def test_get_huawei_iam_users_detail_fetch_error(mock_huawei_credentials_success_with_domain, mock_iam_client_v3):
    user_list_native_mock_err = MagicMock()
    user_list_native_mock_err.id="user-err-detail"
    user_list_native_mock_err.name="user-err"
    user_list_native_mock_err.domain_id="domain_from_creds_123"
    user_list_native_mock_err.enabled=True
    mock_list_users_response_err = MagicMock(spec=KeystoneListUsersResponse)
    mock_list_users_response_err.users = [user_list_native_mock_err]
    mock_iam_client_v3.keystone_list_users.return_value = mock_list_users_response_err

    # Simular erro ao buscar detalhes do usuário
    mock_iam_client_v3.keystone_show_user.side_effect = sdk_exceptions.SdkException("IAM.ShowError", "Cannot get user details") # Mantido
    # Mockar outras chamadas para retornar vazio para isolar o erro
    mock_iam_client_v3.list_permanent_access_keys.return_value = MagicMock(credentials=[])

    result = await huawei_iam_collector.get_huawei_iam_users(domain_id="domain_from_creds_123", region_id="reg-iam")

    assert len(result) == 1
    user_data = result[0]
    assert user_data.name == "user-err"
    assert "Detail fetch error: IAM.ShowError - Cannot get user details" in user_data.error_details
    assert user_data.login_protect is None # Não foi obtido devido ao erro
    assert user_data.access_keys == [] # Ou None, dependendo de como é tratado

# Ajustes no `huawei_iam_collector.py` durante a escrita dos testes:
# *   Na função `get_huawei_iam_users`:
#     *   A lógica para determinar `effective_domain_id` foi melhorada para usar `os.getenv("HUAWEICLOUD_SDK_DOMAIN_ID")` como uma fonte e depois o `project_id` das credenciais como fallback, com logging apropriado. Se nenhum puder ser determinado, retorna um erro.
#     *   Ao chamar `KeystoneShowUserRequest`, o `domain_id` também foi incluído, pois a API o requer.
#     *   O acesso a campos como `email` e `mobile` no `user_detail_native` foi tornado mais seguro com `getattr`.
#     *   Se `login_protect_data.enabled` for true, a seção `mfa_devices` no `HuaweiIAMUserData` ainda não é preenchida com detalhes específicos do dispositivo, pois isso exigiria uma chamada `ListUserMfaDevices` separada que não foi implementada/mockada neste passe. A política de MFA se baseará no `login_protect.enabled`.
# *   O `_parse_huawei_iam_timestamp` foi ajustado para lidar com o caso de o input já ser um objeto datetime.
#
# Estes testes cobrem cenários básicos e de erro para o coletor de usuários IAM da Huawei Cloud.
