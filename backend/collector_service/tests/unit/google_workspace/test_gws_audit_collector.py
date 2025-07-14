import pytest
from unittest.mock import patch, MagicMock
import datetime

from app.google_workspace.gws_audit_collector import get_gws_audit_logs, _convert_sdk_activity_to_schema
from app.schemas.google_workspace.gws_audit_log_schemas import GWSAuditLogCollection, GWSAuditLogItem
from app.core.config import settings # Para mockar as settings globais

@pytest.fixture(autouse=True)
def mock_gws_settings(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_WORKSPACE_CUSTOMER_ID", "test_customer_id")
    monkeypatch.setattr(settings, "GOOGLE_WORKSPACE_DELEGATED_ADMIN_EMAIL", "test_admin@example.com")
    # GOOGLE_SERVICE_ACCOUNT_KEY_PATH é usado pelo get_gws_service_client, que será mockado

@pytest.fixture
def mock_gws_reports_service():
    with patch("app.google_workspace.gws_audit_collector.get_gws_service_client") as mock_get_service:
        mock_service_instance = MagicMock()
        mock_activities_list = MagicMock()
        mock_activities_list_execute = MagicMock()

        mock_service_instance.activities.return_value.list.return_value = mock_activities_list
        mock_activities_list.execute.return_value = mock_activities_list_execute # Este será o response final

        mock_get_service.return_value = mock_service_instance # get_gws_service_client retorna o service
        yield mock_service_instance, mock_activities_list_execute # Retorna o mock da chamada execute()


def test_convert_sdk_activity_to_schema():
    sdk_activity_dict = {
        "kind": "admin#reports#activity",
        "id": {
            "time": "2023-11-15T10:00:00.123Z",
            "uniqueQualifier": "qualifier123",
            "applicationName": "login",
            "customerId": "C_test_customer"
        },
        "actor": {"email": "user@example.com", "profileId": "pid123", "callerType": "USER"},
        "ipAddress": "1.2.3.4",
        "events": [{
            "type": "login_type", "name": "login_success",
            "parameters": [{"name": "login_challenge_method", "value": "password"}]
        }]
    }
    schema_item = _convert_sdk_activity_to_schema(sdk_activity_dict)
    assert schema_item is not None
    assert schema_item.id_application_name == "login"
    assert schema_item.actor.email == "user@example.com"
    assert len(schema_item.events) == 1
    assert schema_item.events[0].name == "login_success"

@pytest.mark.asyncio
async def test_get_gws_audit_logs_success(mock_gws_reports_service, mock_gws_settings):
    mock_service, mock_execute_call = mock_gws_reports_service

    # Simular resposta da API Google Reports
    mock_response_page1 = {
        "kind": "admin#reports#activities",
        "items": [
            {"id": {"time": "2023-11-15T10:00:00.000Z", "applicationName": "login"}, "actor": {"email": "user1@test.com"}, "events": [{"name": "login_success"}]},
            {"id": {"time": "2023-11-15T10:05:00.000Z", "applicationName": "login"}, "actor": {"email": "user2@test.com"}, "events": [{"name": "logout"}]},
        ],
        "nextPageToken": "token_next_page"
    }
    mock_response_page2 = {
        "kind": "admin#reports#activities",
        "items": [
            {"id": {"time": "2023-11-15T10:10:00.000Z", "applicationName": "login"}, "actor": {"email": "user3@test.com"}, "events": [{"name": "login_failure"}]},
        ]
        # Sem nextPageToken para indicar a última página
    }
    mock_execute_call.side_effect = [mock_response_page1, mock_response_page2]

    # A função get_gws_audit_logs é síncrona, mas o teste é marcado como asyncio
    # porque o run_in_threadpool é usado no controller. Aqui testamos a lógica síncrona.
    result = get_gws_audit_logs(
        application_name="login",
        max_total_results=5
    )

    assert isinstance(result, GWSAuditLogCollection)
    assert result.error_message is None
    assert len(result.items) == 3
    assert result.items[0].actor.email == "user1@test.com"
    assert result.items[2].actor.email == "user3@test.com"
    assert result.next_page_token is None # Última página foi alcançada

    # Verificar se activities().list().execute() foi chamado duas vezes
    assert mock_service.activities().list().execute.call_count == 2


@pytest.mark.asyncio
async def test_get_gws_audit_logs_api_error(mock_gws_reports_service, mock_gws_settings):
    mock_service, mock_execute_call = mock_gws_reports_service
    # Simular um erro da API do Google
    # from googleapiclient.errors import HttpError
    # mock_execute_call.side_effect = HttpError(MagicMock(status=500, reason="Server error"), b"Server error content")
    # Por simplicidade, apenas uma Exception genérica:
    mock_execute_call.side_effect = Exception("Google API Error")

    result = get_gws_audit_logs(application_name="drive")

    assert result.error_message is not None
    assert "Google API Error" in result.error_message
    assert len(result.items) == 0

def test_get_gws_audit_logs_missing_config(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_WORKSPACE_DELEGATED_ADMIN_EMAIL", None)

    result = get_gws_audit_logs(application_name="admin")
    assert result.error_message is not None
    assert "Delegated Admin Email not configured" in result.error_message

@patch("app.google_workspace.gws_audit_collector.get_gws_service_client", side_effect=Exception("Client init failed"))
def test_get_gws_audit_logs_client_init_failure(mock_get_service_fail, mock_gws_settings):
    # Este teste verifica o try-except ao redor de get_gws_service_client
    result = get_gws_audit_logs(application_name="token")
    assert result.error_message is not None
    assert "Failed to get Google Workspace service client" in result.error_message
