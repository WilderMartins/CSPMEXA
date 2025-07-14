import pytest
from unittest.mock import patch, MagicMock
import datetime
import httpx # Para mockar respostas HTTP
from dotenv import load_dotenv

load_dotenv(dotenv_path="backend/notification_service/.env.test")

from notification_service.app.services.webhook_service import send_webhook_notification_sync
from notification_service.app.schemas.notification_schema import AlertDataPayload

@pytest.fixture
def mock_webhook_settings(monkeypatch):
    with patch('app.core.config.get_settings') as mock_get_settings:
        mock_settings_obj = MagicMock()
        mock_settings_obj.WEBHOOK_DEFAULT_URL = "http://default.webhook.test/hook"
        # Adicionar outras settings relacionadas a webhook se forem usadas no futuro
        # mock_settings_obj.WEBHOOK_TIMEOUT_SECONDS = 15
        mock_get_settings.return_value = mock_settings_obj
        yield mock_settings_obj

@pytest.fixture
def sample_alert_payload_for_webhook(): # Similar ao de email, mas pode ser customizado se necessário
    return AlertDataPayload(
        resource_id="res-wh-456",
        resource_type="Test::Webhook::Resource",
        provider="test_webhook_provider",
        severity="MEDIUM",
        title="Test Webhook Medium Alert",
        description="This is a test webhook alert description.",
        policy_id="TEST_WEBHOOK_POLICY_002",
        account_id="test-webhook-account",
        region="webhook-region-2",
        details={"webhook_info": "some webhook data"},
        recommendation="Test webhook recommendation.",
        original_alert_created_at=datetime.datetime.now(datetime.timezone.utc)
    )

@patch("notification_service.app.services.webhook_service.httpx.Client")
def test_send_webhook_notification_sync_success_default_url(mock_httpx_client_class, mock_webhook_settings, sample_alert_payload_for_webhook):
    """Testa o envio de webhook bem-sucedido usando a URL padrão."""
    mock_http_client_instance = MagicMock()
    mock_http_client_instance.post.return_value = httpx.Response(200, json={"status": "ok"}) # Sucesso (2xx)
    # Configurar o context manager do cliente mockado
    mock_enter_method = MagicMock(return_value=mock_http_client_instance)
    mock_exit_method = MagicMock()
    mock_httpx_client_class.return_value.__enter__ = mock_enter_method
    mock_httpx_client_class.return_value.__exit__ = mock_exit_method


    success = send_webhook_notification_sync(
        alert_data=sample_alert_payload_for_webhook
        # target_url não fornecido, deve usar o default
    )

    assert success is True
    mock_httpx_client_class.assert_called_once_with(timeout=10) # Verifica o timeout padrão (10s)
    mock_http_client_instance.post.assert_called_once()

    call_args = mock_http_client_instance.post.call_args
    assert call_args[0][0] == mock_webhook_settings.WEBHOOK_DEFAULT_URL # Verifica a URL

    expected_payload = sample_alert_payload_for_webhook.model_dump(by_alias=True) if hasattr(sample_alert_payload_for_webhook, 'model_dump') else sample_alert_payload_for_webhook.dict(by_alias=True)
    assert call_args[1]['json'] == expected_payload # Verifica o payload JSON
    assert call_args[1]['headers'] == {"Content-Type": "application/json"}


@patch("notification_service.app.services.webhook_service.httpx.Client")
def test_send_webhook_notification_sync_success_specific_url(mock_httpx_client_class, mock_webhook_settings, sample_alert_payload_for_webhook):
    """Testa o envio de webhook bem-sucedido usando uma URL específica."""
    mock_http_client_instance = MagicMock()
    mock_http_client_instance.post.return_value = httpx.Response(202, json={"status": "accepted"})
    mock_enter_method = MagicMock(return_value=mock_http_client_instance)
    mock_exit_method = MagicMock()
    mock_httpx_client_class.return_value.__enter__ = mock_enter_method
    mock_httpx_client_class.return_value.__exit__ = mock_exit_method

    specific_url = "http://specific.webhook.test/target"

    success = send_webhook_notification_sync(
        alert_data=sample_alert_payload_for_webhook,
        target_url=specific_url
    )

    assert success is True
    mock_http_client_instance.post.assert_called_once()
    assert mock_http_client_instance.post.call_args[0][0] == specific_url


@patch("notification_service.app.services.webhook_service.httpx.Client")
def test_send_webhook_notification_sync_http_error(mock_httpx_client_class, mock_webhook_settings, sample_alert_payload_for_webhook):
    """Testa falha no envio de webhook devido a um erro HTTP (status não 2xx)."""
    mock_http_client_instance = MagicMock()
    mock_http_client_instance.post.return_value = httpx.Response(500, text="Internal Server Error")
    mock_enter_method = MagicMock(return_value=mock_http_client_instance)
    mock_exit_method = MagicMock()
    mock_httpx_client_class.return_value.__enter__ = mock_enter_method
    mock_httpx_client_class.return_value.__exit__ = mock_exit_method

    success = send_webhook_notification_sync(alert_data=sample_alert_payload_for_webhook)
    assert success is False

@patch("notification_service.app.services.webhook_service.httpx.Client")
def test_send_webhook_notification_sync_request_error(mock_httpx_client_class, mock_webhook_settings, sample_alert_payload_for_webhook):
    """Testa falha no envio de webhook devido a um RequestError do httpx."""
    mock_http_client_instance = MagicMock()
    mock_http_client_instance.post.side_effect = httpx.RequestError("Connection failed", request=MagicMock())
    mock_enter_method = MagicMock(return_value=mock_http_client_instance)
    mock_exit_method = MagicMock()
    mock_httpx_client_class.return_value.__enter__ = mock_enter_method
    mock_httpx_client_class.return_value.__exit__ = mock_exit_method

    success = send_webhook_notification_sync(alert_data=sample_alert_payload_for_webhook)
    assert success is False

@patch("notification_service.app.services.webhook_service.httpx.Client")
def test_send_webhook_notification_sync_timeout(mock_httpx_client_class, mock_webhook_settings, sample_alert_payload_for_webhook):
    """Testa falha no envio de webhook devido a um Timeout."""
    mock_http_client_instance = MagicMock()
    mock_http_client_instance.post.side_effect = httpx.TimeoutException("Timeout occurred", request=MagicMock())
    mock_enter_method = MagicMock(return_value=mock_http_client_instance)
    mock_exit_method = MagicMock()
    mock_httpx_client_class.return_value.__enter__ = mock_enter_method
    mock_httpx_client_class.return_value.__exit__ = mock_exit_method

    success = send_webhook_notification_sync(alert_data=sample_alert_payload_for_webhook)
    assert success is False


def test_send_webhook_notification_sync_no_url_configured(monkeypatch, sample_alert_payload_for_webhook):
    """Testa o caso onde nenhuma URL de webhook (específica ou default) está configurada."""
    mock_no_url_settings = MagicMock()
    mock_no_url_settings.WEBHOOK_DEFAULT_URL = None # ou ""
    monkeypatch.setattr("notification_service.app.services.webhook_service.settings", mock_no_url_settings)

    success = send_webhook_notification_sync(
        alert_data=sample_alert_payload_for_webhook
        # target_url não fornecido
    )
    assert success is False
