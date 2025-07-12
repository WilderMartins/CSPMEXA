import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import datetime

# Importar o app FastAPI do notification_service para o TestClient
from notification_service.app.main import app
from notification_service.app.schemas.notification_schema import AlertDataPayload, EmailNotificationRequest

client = TestClient(app)

# Mock das settings globais
@pytest.fixture(autouse=True) # Aplicar automaticamente a todas as funcs de teste neste módulo
def mock_controller_settings(monkeypatch):
    mock_settings_obj = MagicMock()
    mock_settings_obj.DEFAULT_CRITICAL_ALERT_RECIPIENT_EMAIL = "default_recipient@test.com"
    mock_settings_obj.WEBHOOK_DEFAULT_URL = "http://default.webhook.test/controller-hook"
    mock_settings_obj.GOOGLE_CHAT_WEBHOOK_URL = "http://default.gchat.test/controller-hook" # Adicionado
    # API_V1_STR é usado no main.py para prefixar o router, o TestClient lida com isso.

    # Monkeypatch as settings nos módulos relevantes
    monkeypatch.setattr("notification_service.app.api.v1.notification_controller.settings", mock_settings_obj)
    monkeypatch.setattr("notification_service.app.services.email_service.settings", mock_settings_obj)
    monkeypatch.setattr("notification_service.app.services.webhook_service.settings", mock_settings_obj)
    monkeypatch.setattr("notification_service.app.services.google_chat_service.settings", mock_settings_obj) # Adicionado
    return mock_settings_obj

@pytest.fixture
def sample_alert_payload_dict():
    # Usar um dicionário para o payload, pois será convertido para JSON
    return {
        "resource_id": "res-api-test",
        "resource_type": "Test::API::Resource",
        "provider": "test_api_provider",
        "severity": "CRITICAL",
        "title": "API Test Critical Alert",
        "description": "This is an API test alert description.",
        "policy_id": "API_TEST_POLICY_001",
        "account_id": "api-test-account",
        "region": "api-test-region",
        "details": {"api_info": "some api details"},
        "recommendation": "API Test recommendation.",
        "original_alert_created_at": datetime.datetime.now(datetime.timezone.utc).isoformat() # Enviar como string ISO
    }

# Mockar a função que é realmente chamada pela BackgroundTask
# Neste caso, é send_email_background, que então chama run_in_threadpool(send_email_notification_sync)
@patch("notification_service.app.api.v1.notification_controller.send_email_background", new_callable=MagicMock)
def test_trigger_email_notification_success_with_to_email(mock_send_email_bg_task, sample_alert_payload_dict):
    """Testa o endpoint /notify/email com um 'to_email' fornecido."""

    request_payload = {
        "to_email": "specific_recipient@example.com",
        "subject": "Specific Subject for API Test",
        "alert_data": sample_alert_payload_dict
    }

    response = client.post("/api/v1/notify/email", json=request_payload)

    assert response.status_code == 202 # Accepted
    response_data = response.json()
    assert response_data["status"] == "accepted"
    assert response_data["recipient"] == "specific_recipient@example.com"
    assert response_data["notification_type"] == "email"

    # Verificar se background_tasks.add_task foi chamado (indiretamente, pela chamada a send_email_background)
    # O mock_send_email_bg_task é o que BackgroundTasks.add_task chamaria.
    # Precisamos verificar se o add_task no controller foi chamado com os args corretos.
    # Como add_task é um método de uma instância de BackgroundTasks, precisamos mockar BackgroundTasks.add_task.
    # O patch atual em send_email_background é mais simples se queremos apenas verificar se ele foi chamado.

    mock_send_email_bg_task.assert_called_once()
    call_args = mock_send_email_bg_task.call_args[0] # Args posicionais

    assert call_args[0] == "specific_recipient@example.com" # recipient_email
    assert call_args[1] == "Specific Subject for API Test"  # subject
    # O AlertDataPayload é o terceiro argumento
    assert call_args[2].resource_id == sample_alert_payload_dict["resource_id"]
    assert call_args[2].title == sample_alert_payload_dict["title"]


@patch("notification_service.app.api.v1.notification_controller.send_email_background", new_callable=MagicMock)
def test_trigger_email_notification_success_default_recipient(mock_send_email_bg_task, mock_controller_settings, sample_alert_payload_dict):
    """Testa o endpoint /notify/email usando o destinatário padrão das settings."""
    request_payload = {
        # to_email não fornecido
        "alert_data": sample_alert_payload_dict
    }

    response = client.post("/api/v1/notify/email", json=request_payload)

    assert response.status_code == 202
    response_data = response.json()
    assert response_data["status"] == "accepted"
    assert response_data["recipient"] == mock_controller_settings.DEFAULT_CRITICAL_ALERT_RECIPIENT_EMAIL

    mock_send_email_bg_task.assert_called_once()
    call_args = mock_send_email_bg_task.call_args[0]
    assert call_args[0] == mock_controller_settings.DEFAULT_CRITICAL_ALERT_RECIPIENT_EMAIL
    # O assunto também será o padrão
    expected_subject = f"CSPMEXA Critical Alert: {sample_alert_payload_dict['title']}"
    assert call_args[1] == expected_subject


def test_trigger_email_notification_no_recipient_and_no_default(monkeypatch, sample_alert_payload_dict):
    """Testa o caso onde nem 'to_email' nem o default recipient estão configurados."""
    # Mock settings para que DEFAULT_CRITICAL_ALERT_RECIPIENT_EMAIL seja None ou string vazia
    mock_settings_no_default = MagicMock()
    mock_settings_no_default.DEFAULT_CRITICAL_ALERT_RECIPIENT_EMAIL = None
    monkeypatch.setattr("notification_service.app.api.v1.notification_controller.settings", mock_settings_no_default)

    request_payload = {
        # to_email não fornecido
        "alert_data": sample_alert_payload_dict
    }

    response = client.post("/api/v1/notify/email", json=request_payload)

    assert response.status_code == 400 # Bad Request
    assert "Recipient email address is missing" in response.json()["detail"]


def test_trigger_email_notification_invalid_payload_missing_alert_data(sample_alert_payload_dict):
    """Testa o endpoint com payload inválido (faltando alert_data)."""
    invalid_payload = {
        "to_email": "recipient@example.com"
        # alert_data faltando
    }
    response = client.post("/api/v1/notify/email", json=invalid_payload)
    assert response.status_code == 422 # Unprocessable Entity (erro de validação Pydantic)

def test_trigger_email_notification_invalid_alert_data_field(sample_alert_payload_dict):
    """Testa o endpoint com um campo inválido dentro de alert_data."""
    invalid_alert_data = sample_alert_payload_dict.copy()
    invalid_alert_data["severity"] = "EXTREMELY_CRITICAL" # Valor inválido para o enum

    request_payload = {
        "to_email": "recipient@example.com",
        "alert_data": invalid_alert_data
    }
    response = client.post("/api/v1/notify/email", json=request_payload)
    assert response.status_code == 422 # Unprocessable Entity

# Teste para o health check do main.py
def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    # Pode-se mockar settings no main.py para verificar PROJECT_NAME e APP_VERSION se necessário
    # Mas para este teste, apenas o status ok é geralmente suficiente.

# --- Testes para o endpoint de Webhook ---

@patch("notification_service.app.api.v1.notification_controller.send_webhook_background", new_callable=MagicMock)
def test_trigger_webhook_notification_success_specific_url(mock_send_webhook_bg_task, sample_alert_payload_dict):
    """Testa o endpoint /notify/webhook com uma URL específica fornecida."""
    specific_webhook_url = "http://specific.webhook.test/target"
    request_payload = {
        "webhook_url": specific_webhook_url,
        "alert_data": sample_alert_payload_dict
    }

    response = client.post("/api/v1/notify/webhook", json=request_payload)

    assert response.status_code == 202 # Accepted
    response_data = response.json()
    assert response_data["status"] == "accepted"
    assert response_data["recipient"] == specific_webhook_url
    assert response_data["notification_type"] == "webhook"

    mock_send_webhook_bg_task.assert_called_once()
    call_args = mock_send_webhook_bg_task.call_args[0]
    assert call_args[0] == specific_webhook_url # target_url
    assert call_args[1].resource_id == sample_alert_payload_dict["resource_id"] # alert_data

@patch("notification_service.app.api.v1.notification_controller.send_webhook_background", new_callable=MagicMock)
def test_trigger_webhook_notification_success_default_url(mock_send_webhook_bg_task, mock_controller_settings, sample_alert_payload_dict):
    """Testa o endpoint /notify/webhook usando a URL padrão das settings."""
    request_payload = {
        # webhook_url não fornecido
        "alert_data": sample_alert_payload_dict
    }

    response = client.post("/api/v1/notify/webhook", json=request_payload)

    assert response.status_code == 202
    response_data = response.json()
    assert response_data["recipient"] == mock_controller_settings.WEBHOOK_DEFAULT_URL

    mock_send_webhook_bg_task.assert_called_once()
    call_args = mock_send_webhook_bg_task.call_args[0]
    assert call_args[0] == mock_controller_settings.WEBHOOK_DEFAULT_URL


def test_trigger_webhook_notification_no_url_and_no_default(monkeypatch, sample_alert_payload_dict):
    """Testa o caso onde nem 'webhook_url' nem o default estão configurados."""
    mock_settings_no_default_webhook = MagicMock()
    mock_settings_no_default_webhook.WEBHOOK_DEFAULT_URL = None # ou ""
    # Manter DEFAULT_CRITICAL_ALERT_RECIPIENT_EMAIL para não afetar outros testes se o fixture for compartilhado
    mock_settings_no_default_webhook.DEFAULT_CRITICAL_ALERT_RECIPIENT_EMAIL = "default@example.com"
    monkeypatch.setattr("notification_service.app.api.v1.notification_controller.settings", mock_settings_no_default_webhook)

    request_payload = {
        "alert_data": sample_alert_payload_dict
    }

    response = client.post("/api/v1/notify/webhook", json=request_payload)

    assert response.status_code == 400 # Bad Request
    assert "Webhook URL is missing" in response.json()["detail"]

def test_trigger_webhook_notification_invalid_payload(sample_alert_payload_dict):
    """Testa o endpoint /notify/webhook com payload inválido (alert_data faltando)."""
    invalid_payload = {
        "webhook_url": "http://some.url/hook"
        # alert_data faltando
    }
    response = client.post("/api/v1/notify/webhook", json=invalid_payload)
    assert response.status_code == 422 # Unprocessable Entity

# --- Testes para o endpoint de Google Chat ---

@patch("notification_service.app.api.v1.notification_controller.send_google_chat_background", new_callable=MagicMock)
def test_trigger_gchat_notification_success_specific_url(mock_send_gchat_bg_task, sample_alert_payload_dict):
    """Testa o endpoint /notify/google-chat com uma URL específica."""
    specific_gchat_url = "http://specific.gchat.test/target"
    request_payload = {
        "webhook_url": specific_gchat_url, # O schema GoogleChatNotificationRequest usa webhook_url
        "alert_data": sample_alert_payload_dict
    }

    response = client.post("/api/v1/notify/google-chat", json=request_payload)

    assert response.status_code == 202
    response_data = response.json()
    assert response_data["status"] == "accepted"
    assert f"...{specific_gchat_url[-20:]}" in response_data["recipient"] # Verifica parte da URL
    assert response_data["notification_type"] == "google_chat"

    mock_send_gchat_bg_task.assert_called_once()
    call_args = mock_send_gchat_bg_task.call_args[0]
    assert call_args[0] == specific_gchat_url # target_webhook_url
    assert call_args[1].resource_id == sample_alert_payload_dict["resource_id"] # alert_data


@patch("notification_service.app.api.v1.notification_controller.send_google_chat_background", new_callable=MagicMock)
def test_trigger_gchat_notification_success_default_url(mock_send_gchat_bg_task, mock_controller_settings, sample_alert_payload_dict):
    """Testa o endpoint /notify/google-chat usando a URL padrão."""
    request_payload = {
        "alert_data": sample_alert_payload_dict
    }

    response = client.post("/api/v1/notify/google-chat", json=request_payload)

    assert response.status_code == 202
    response_data = response.json()
    assert f"...{mock_controller_settings.GOOGLE_CHAT_WEBHOOK_URL[-20:]}" in response_data["recipient"]

    mock_send_gchat_bg_task.assert_called_once()
    call_args = mock_send_gchat_bg_task.call_args[0]
    assert call_args[0] == mock_controller_settings.GOOGLE_CHAT_WEBHOOK_URL


def test_trigger_gchat_notification_no_url_and_no_default(monkeypatch, sample_alert_payload_dict):
    """Testa o caso onde nem 'webhook_url' (para GChat) nem o default estão configurados."""
    mock_settings_no_default_gchat = MagicMock()
    mock_settings_no_default_gchat.GOOGLE_CHAT_WEBHOOK_URL = None
    mock_settings_no_default_gchat.DEFAULT_CRITICAL_ALERT_RECIPIENT_EMAIL = "default@example.com"
    mock_settings_no_default_gchat.WEBHOOK_DEFAULT_URL = "http://default.webhook.test"
    monkeypatch.setattr("notification_service.app.api.v1.notification_controller.settings", mock_settings_no_default_gchat)

    request_payload = {
        "alert_data": sample_alert_payload_dict
    }
    response = client.post("/api/v1/notify/google-chat", json=request_payload)
    assert response.status_code == 400
    assert "Google Chat webhook URL is missing" in response.json()["detail"]
