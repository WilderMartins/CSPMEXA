import pytest
from unittest.mock import patch, AsyncMock, MagicMock # Adicionado AsyncMock
import httpx # Para simular respostas HTTPStatusError

from app.m365.m365_tenant_security_collector import get_m365_users_mfa_status, get_m365_conditional_access_policies
from app.schemas.m365.m365_security_schemas import M365UserMFAStatusCollection, M365ConditionalAccessPolicyCollection

# Mock para o m365_client_manager e seu método get_graph_client
# Este mock será usado por todos os testes neste arquivo.
@pytest.fixture(autouse=True)
def mock_m365_client_manager(monkeypatch):
    mock_manager_instance = MagicMock()
    mock_graph_client_instance = AsyncMock(spec=httpx.AsyncClient) # Usar AsyncMock para o cliente

    # Configurar o context manager para o AsyncMock
    mock_graph_client_instance.__aenter__.return_value = mock_graph_client_instance
    mock_graph_client_instance.__aexit__.return_value = None # ou mock_graph_client_instance para retornar o próprio mock

    mock_manager_instance.get_graph_client = AsyncMock(return_value=mock_graph_client_instance)

    monkeypatch.setattr("app.m365.m365_tenant_security_collector.m365_client_manager", mock_manager_instance)
    return mock_manager_instance, mock_graph_client_instance


@pytest.mark.asyncio
async def test_get_m365_users_mfa_status_success(mock_m365_client_manager):
    _, mock_graph_client = mock_m365_client_manager

    # Simular resposta da API Graph para /reports/credentialUserRegistrationDetails
    mock_graph_response_page1 = MagicMock(spec=httpx.Response)
    mock_graph_response_page1.status_code = 200
    mock_graph_response_page1.json.return_value = {
        "value": [
            {"id": "user1_id", "userPrincipalName": "user1@contoso.com", "isRegistered": True, "isEnabled": True, "authMethods": ["microsoftAuthenticatorPush"]},
            {"id": "user2_id", "userPrincipalName": "user2@contoso.com", "isRegistered": False, "isEnabled": False, "authMethods": []},
        ],
        "@odata.nextLink": "https://graph.microsoft.com/v1.0/reports/credentialUserRegistrationDetails?$skipToken=123"
    }
    mock_graph_response_page2 = MagicMock(spec=httpx.Response)
    mock_graph_response_page2.status_code = 200
    mock_graph_response_page2.json.return_value = {
        "value": [
            {"id": "user3_id", "userPrincipalName": "user3@contoso.com", "isRegistered": True, "isEnabled": False, "authMethods": ["sms"]},
        ]
        # Sem @odata.nextLink para indicar a última página
    }
    mock_graph_client.get.side_effect = [mock_graph_response_page1, mock_graph_response_page2]

    result = await get_m365_users_mfa_status()

    assert isinstance(result, M365UserMFAStatusCollection)
    assert result.error_message is None
    assert result.total_users_scanned == 3
    assert result.total_users_with_mfa_issues == 2 # user2 (not registered) + user3 (registered but not enabled by policy, counts as issue by current logic)
    assert len(result.users_mfa_status) == 3

    assert result.users_mfa_status[0].user_principal_name == "user1@contoso.com"
    assert result.users_mfa_status[0].mfa_state == "Enforced"
    assert result.users_mfa_status[1].user_principal_name == "user2@contoso.com"
    assert result.users_mfa_status[1].mfa_state == "NotRegistered"
    assert result.users_mfa_status[2].user_principal_name == "user3@contoso.com"
    assert result.users_mfa_status[2].mfa_state == "RegisteredNotEnforcedBySecurityDefaults"

    assert mock_graph_client.get.call_count == 2
    first_call_args = mock_graph_client.get.call_args_list[0][0][0]
    assert "/reports/credentialUserRegistrationDetails" in first_call_args
    second_call_args = mock_graph_client.get.call_args_list[1][0][0]
    assert "https://graph.microsoft.com/v1.0/reports/credentialUserRegistrationDetails?$skipToken=123" in second_call_args


@pytest.mark.asyncio
async def test_get_m365_users_mfa_status_api_error(mock_m365_client_manager):
    _, mock_graph_client = mock_m365_client_manager
    mock_graph_client.get.return_value = MagicMock(status_code=500, text="Internal Server Error")

    result = await get_m365_users_mfa_status()
    assert result.error_message is not None
    assert "Error fetching MFA registration details: 500" in result.error_message
    assert result.total_users_scanned == 0

@pytest.mark.asyncio
async def test_get_m365_conditional_access_policies_success(mock_m365_client_manager):
    _, mock_graph_client = mock_m365_client_manager
    mock_graph_response = MagicMock(spec=httpx.Response)
    mock_graph_response.status_code = 200
    mock_graph_response.json.return_value = {
        "value": [
            {"id": "policy1_id", "displayName": "Policy 1 - Enabled", "state": "enabled"},
            {"id": "policy2_id", "displayName": "Policy 2 - Disabled", "state": "disabled"},
            {"id": "policy3_id", "displayName": "Policy 3 - ReportOnly", "state": "enabledForReportingButNotEnforced"},
        ]
    }
    mock_graph_client.get.return_value = mock_graph_response

    result = await get_m365_conditional_access_policies()

    assert isinstance(result, M365ConditionalAccessPolicyCollection)
    assert result.error_message is None
    assert result.total_policies_found == 3
    assert len(result.policies) == 3
    assert result.policies[0].display_name == "Policy 1 - Enabled"
    assert result.policies[0].state == "enabled"
    assert result.policies[1].state == "disabled"

    mock_graph_client.get.assert_called_once()
    call_args = mock_graph_client.get.call_args_list[0][0][0]
    assert "/identity/conditionalAccess/policies" in call_args

@pytest.mark.asyncio
async def test_get_m365_ca_policies_api_error(mock_m365_client_manager):
    _, mock_graph_client = mock_m365_client_manager
    mock_graph_client.get.return_value = MagicMock(status_code=403, text="Forbidden")

    result = await get_m365_conditional_access_policies()
    assert result.error_message is not None
    assert "Error fetching CA policies: 403" in result.error_message
    assert result.total_policies_found == 0

@pytest.mark.asyncio
async def test_get_m365_client_manager_failure(monkeypatch):
    # Testar o caso onde o m365_client_manager não consegue obter um cliente
    mock_manager_instance_fail = MagicMock()
    mock_manager_instance_fail.get_graph_client = AsyncMock(return_value=None) # Simula falha ao obter cliente
    monkeypatch.setattr("app.m365.m365_tenant_security_collector.m365_client_manager", mock_manager_instance_fail)

    mfa_result = await get_m365_users_mfa_status()
    assert "Failed to get authenticated Graph API client" in mfa_result.error_message

    ca_result = await get_m365_conditional_access_policies()
    assert "Failed to get authenticated Graph API client" in ca_result.error_message
