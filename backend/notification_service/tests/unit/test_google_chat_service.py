import pytest
from unittest.mock import patch, MagicMock
import datetime
import httpx # Para mockar respostas HTTP
import json
from dotenv import load_dotenv

load_dotenv(dotenv_path="backend/notification_service/.env.test")

from notification_service.app.services.google_chat_service import send_google_chat_notification_sync, format_alert_for_google_chat
from notification_service.app.schemas.notification_schema import AlertDataPayload

@pytest.fixture
def mock_gchat_settings(monkeypatch):
    with patch('app.core.config.get_settings') as mock_get_settings:
        mock_settings_obj = MagicMock()
        mock_settings_obj.GOOGLE_CHAT_WEBHOOK_URL = "http://default.gchat.test/hook"
        # Outras settings se o serviço as usar
        mock_get_settings.return_value = mock_settings_obj
        yield mock_settings_obj

@pytest.fixture
def sample_alert_payload_for_gchat():
    return AlertDataPayload(
        resource_id="res-gc-789",
        resource_type="Test::GChat::Resource",
        provider="test_gchat_provider",
        severity="CRITICAL",
        title="Test GChat Critical Alert",
        description="This is a test GChat alert description for card formatting.",
        policy_id="TEST_GCHAT_POLICY_003",
        account_id="test-gchat-account",
        region="gchat-region-3",
        details={"gchat_info": "some gchat data", "more_data": {"nested": True}},
        recommendation="Test GChat recommendation for card.",
        original_alert_created_at=datetime.datetime(2023, 10, 26, 10, 30, 0, tzinfo=datetime.timezone.utc)
    )

def test_format_alert_for_google_chat(sample_alert_payload_for_gchat):
    """Testa a formatação da mensagem do Google Chat."""
    formatted_message = format_alert_for_google_chat(sample_alert_payload_for_gchat)

    assert "cardsV2" in formatted_message
    assert len(formatted_message["cardsV2"]) == 1
    card = formatted_message["cardsV2"][0]["card"]

    assert card["header"]["title"] == "🔴 CRITICAL: Test GChat Critical Alert"
    assert card["header"]["subtitle"] == "Política: TEST_GCHAT_POLICY_003"

    assert len(card["sections"]) == 1
    widget_text = card["sections"][0]["widgets"][0]["textParagraph"]["text"]

    assert "<b>Recurso:</b> res-gc-789 (Test::GChat::Resource)" in widget_text
    assert "<b>Provedor:</b> TEST_GCHAT_PROVIDER" in widget_text
    assert "<b>Conta/Projeto:</b> test-gchat-account" in widget_text
    assert "<b>Região:</b> gchat-region-3" in widget_text
    assert "<b>Descrição do Alerta:</b><br>This is a test GChat alert description for card formatting." in widget_text
    assert "<b>Recomendação:</b><br>Test GChat recommendation for card." in widget_text
    assert "<b>Detalhes Adicionais:</b>" in widget_text
    assert "&nbsp;&nbsp;\"gchat_info\":&nbsp;\"some&nbsp;gchat&nbsp;data\"" in widget_text # Checa json string formatada
    assert "&nbsp;&nbsp;\"more_data\":&nbsp;{&nbsp;<br>&nbsp;&nbsp;&nbsp;&nbsp;\"nested\":&nbsp;true<br>&nbsp;&nbsp;}<br>}" in widget_text # Checa json string formatada


@patch("notification_service.app.services.google_chat_service.httpx.Client")
def test_send_gchat_notification_sync_success_default_url(mock_httpx_client_class, mock_gchat_settings, sample_alert_payload_for_gchat):
    mock_http_client_instance = MagicMock()
    mock_http_client_instance.post.return_value = httpx.Response(200, json={"name": "spaces/ लड़कियों/messages/XYZ"}) # Exemplo de resposta do GChat
    mock_enter_method = MagicMock(return_value=mock_http_client_instance)
    mock_exit_method = MagicMock()
    mock_httpx_client_class.return_value.__enter__ = mock_enter_method
    mock_httpx_client_class.return_value.__exit__ = mock_exit_method

    success = send_google_chat_notification_sync(alert_data=sample_alert_payload_for_gchat)

    assert success is True
    mock_httpx_client_class.assert_called_once_with(timeout=10)
    mock_http_client_instance.post.assert_called_once()

    call_args = mock_http_client_instance.post.call_args
    assert call_args[0][0] == mock_gchat_settings.GOOGLE_CHAT_WEBHOOK_URL

    expected_payload = format_alert_for_google_chat(sample_alert_payload_for_gchat)
    assert call_args[1]['json'] == expected_payload
    assert call_args[1]['headers'] == {"Content-Type": "application/json; charset=UTF-8"}


@patch("notification_service.app.services.google_chat_service.httpx.Client")
def test_send_gchat_notification_sync_http_error(mock_httpx_client_class, mock_gchat_settings, sample_alert_payload_for_gchat):
    mock_http_client_instance = MagicMock()
    mock_http_client_instance.post.return_value = httpx.Response(400, text="Bad Request to GChat")
    mock_enter_method = MagicMock(return_value=mock_http_client_instance)
    mock_exit_method = MagicMock()
    mock_httpx_client_class.return_value.__enter__ = mock_enter_method
    mock_httpx_client_class.return_value.__exit__ = mock_exit_method

    success = send_google_chat_notification_sync(alert_data=sample_alert_payload_for_gchat)
    assert success is False


def test_send_gchat_notification_sync_no_url_configured(monkeypatch, sample_alert_payload_for_gchat):
    mock_no_url_settings = MagicMock()
    mock_no_url_settings.GOOGLE_CHAT_WEBHOOK_URL = None
    monkeypatch.setattr("notification_service.app.services.google_chat_service.settings", mock_no_url_settings)

    success = send_google_chat_notification_sync(alert_data=sample_alert_payload_for_gchat)
    assert success is False
