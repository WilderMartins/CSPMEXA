import pytest
from unittest.mock import MagicMock, patch
from app.services.audit_service_client import AuditServiceClient

@pytest.fixture
def audit_service_client():
    with patch('app.services.audit_service_client.settings.AUDIT_SERVICE_URL', 'http://test-audit-service.com'):
        yield AuditServiceClient()

@patch('app.services.audit_service_client.httpx.AsyncClient.post')
@pytest.mark.asyncio
async def test_create_event_success(mock_post, audit_service_client):
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_post.return_value = mock_response

    await audit_service_client.create_event(
        actor="test_actor",
        action="test_action",
        resource="test_resource",
        details={"key": "value"}
    )
    mock_post.assert_called_once()

@patch('app.services.audit_service_client.httpx.AsyncClient.post')
@pytest.mark.asyncio
async def test_create_event_failure(mock_post, audit_service_client):
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_post.return_value = mock_response

    await audit_service_client.create_event(
        actor="test_actor",
        action="test_action",
        resource="test_resource",
        details={"key": "value"}
    )
    mock_post.assert_called_once()
