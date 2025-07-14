import pytest
from unittest.mock import patch, MagicMock
import datetime
from dotenv import load_dotenv

load_dotenv(dotenv_path="backend/notification_service/.env.test")

from notification_service.app.services.email_service import send_email_notification_sync
from notification_service.app.schemas.notification_schema import AlertDataPayload
from botocore.exceptions import ClientError, NoCredentialsError

# Mock das settings globais usadas pelo email_service.py, agora para SES
@pytest.fixture
def mock_ses_email_settings(monkeypatch):
    with patch('app.core.config.get_settings') as mock_get_settings:
        mock_settings_obj = MagicMock()
        mock_settings_obj.AWS_REGION = "us-east-1"
        mock_settings_obj.EMAILS_FROM_EMAIL = "sender@ses-verified.com"
        mock_settings_obj.EMAILS_FROM_NAME = "CSPMEXA SES Test"
        # Opcionais, podem ser None ou não existir no objeto settings
        mock_settings_obj.SES_FROM_EMAIL_ARN = None
        mock_settings_obj.SES_CONFIGURATION_SET_NAME = None
        # DEFAULT_CRITICAL_ALERT_RECIPIENT_EMAIL não é usado diretamente por send_email_notification_sync
        # mas é bom ter para consistência se o config real o tiver.
        mock_settings_obj.DEFAULT_CRITICAL_ALERT_RECIPIENT_EMAIL = "default_ses_recipient@test.com"
        mock_get_settings.return_value = mock_settings_obj
        yield mock_settings_obj

@pytest.fixture
def sample_alert_data_payload(): # Mantido como estava
    return AlertDataPayload(
        resource_id="res-123-ses",
        resource_type="Test::SES::Resource",
        provider="test_ses_provider",
        severity="CRITICAL",
        title="Test SES Critical Alert",
        description="This is a test SES alert description.",
        policy_id="TEST_SES_POLICY_001",
        account_id="test-ses-account",
        region="test-ses-region",
        details={"info_ses": "some ses details"},
        recommendation="Test SES recommendation.",
        original_alert_created_at=datetime.datetime.now(datetime.timezone.utc)
    )

@patch("notification_service.app.services.email_service.boto3.client")
def test_send_email_notification_sync_ses_success(mock_boto_client, mock_ses_email_settings, sample_alert_data_payload):
    """Testa o envio de e-mail bem-sucedido via SES."""
    mock_ses_instance = MagicMock()
    mock_ses_instance.send_email.return_value = {"MessageId": "test-message-id"}
    mock_boto_client.return_value = mock_ses_instance

    recipient = "receiver_ses@example.com"
    subject = "Test SES Alert Email"

    success = send_email_notification_sync(
        recipient_email=recipient,
        subject=subject,
        alert_data=sample_alert_data_payload
    )

    assert success is True
    mock_boto_client.assert_called_once_with("ses", region_name=mock_ses_email_settings.AWS_REGION)

    mock_ses_instance.send_email.assert_called_once()
    _, send_email_kwargs = mock_ses_instance.send_email.call_args

    expected_sender = f"{mock_ses_email_settings.EMAILS_FROM_NAME} <{mock_ses_email_settings.EMAILS_FROM_EMAIL}>"
    assert send_email_kwargs['Source'] == expected_sender
    assert send_email_kwargs['Destination'] == {"ToAddresses": [recipient]}
    assert send_email_kwargs['Message']['Subject']['Data'] == subject
    assert "<h2>Critical Security Alert: Test SES Critical Alert</h2>" in send_email_kwargs['Message']['Body']['Html']['Data']

@patch("notification_service.app.services.email_service.boto3.client")
def test_send_email_notification_sync_ses_client_error(mock_boto_client, mock_ses_email_settings, sample_alert_data_payload):
    """Testa falha no envio de e-mail via SES devido a ClientError."""
    mock_ses_instance = MagicMock()
    # Simular um ClientError do Boto3
    error_response = {'Error': {'Code': 'MessageRejected', 'Message': 'Email address is not verified.'}}
    mock_ses_instance.send_email.side_effect = ClientError(error_response, "send_email")
    mock_boto_client.return_value = mock_ses_instance

    success = send_email_notification_sync(
        recipient_email="unverified_receiver@example.com",
        subject="Test SES Alert Email Failure",
        alert_data=sample_alert_data_payload
    )
    assert success is False

@patch("notification_service.app.services.email_service.boto3.client")
def test_send_email_notification_sync_ses_no_credentials(mock_boto_client, mock_ses_email_settings, sample_alert_data_payload):
    """Testa falha na criação do cliente SES por falta de credenciais."""
    mock_boto_client.side_effect = NoCredentialsError()

    success = send_email_notification_sync(
        recipient_email="receiver@example.com",
        subject="Test SES No Credentials",
        alert_data=sample_alert_data_payload
    )
    assert success is False

def test_send_email_notification_sync_ses_missing_settings(monkeypatch, sample_alert_data_payload):
    """Testa o comportamento quando as configurações SES essenciais (AWS_REGION) estão faltando."""
    mock_partial_settings = MagicMock()
    mock_partial_settings.AWS_REGION = None # AWS_REGION faltando
    mock_partial_settings.EMAILS_FROM_EMAIL = "sender@ses-verified.com"
    # ...
    monkeypatch.setattr("notification_service.app.services.email_service.settings", mock_partial_settings)

    success = send_email_notification_sync(
        recipient_email="receiver@example.com",
        subject="Test SES Missing Settings",
        alert_data=sample_alert_data_payload
    )
    assert success is False


@patch("notification_service.app.services.email_service.boto3.client")
def test_send_email_to_list_of_recipients_ses(mock_boto_client, mock_ses_email_settings, sample_alert_data_payload):
    """Testa o envio para uma lista de destinatários via SES."""
    mock_ses_instance = MagicMock()
    mock_ses_instance.send_email.return_value = {"MessageId": "test-message-id-list"}
    mock_boto_client.return_value = mock_ses_instance

    recipients = ["receiver1_ses@example.com", "receiver2_ses@example.com"]
    subject = "Test SES Alert Email to List"

    success = send_email_notification_sync(
        recipient_email=recipients,
        subject=subject,
        alert_data=sample_alert_data_payload
    )
    assert success is True
    mock_ses_instance.send_email.assert_called_once()
    _, send_email_kwargs = mock_ses_instance.send_email.call_args
    assert send_email_kwargs['Destination'] == {"ToAddresses": recipients}


# O teste de conteúdo do e-mail (test_email_content_render) pode ser mantido,
# mas o mock precisa ser ajustado para capturar os argumentos de ses_client.send_email.
@patch("notification_service.app.services.email_service.boto3.client")
def test_ses_email_content_render(mock_boto_client, mock_ses_email_settings, sample_alert_data_payload):
    mock_ses_instance = MagicMock()
    mock_ses_instance.send_email.return_value = {"MessageId": "test-content-message-id"}
    mock_boto_client.return_value = mock_ses_instance

    send_email_notification_sync(
        recipient_email="receiver_content_ses@example.com",
        subject="SES Content Test",
        alert_data=sample_alert_data_payload
    )

    mock_ses_instance.send_email.assert_called_once()
    _, send_email_kwargs = mock_ses_instance.send_email.call_args
    html_content = send_email_kwargs['Message']['Body']['Html']['Data']

    # As mesmas asserções de conteúdo do teste SMTP original
    assert f"<h2>Critical Security Alert: {sample_alert_data_payload.title}</h2>" in html_content
    assert f"<strong>Severity:</strong> <span style=\"color: #c9302c; font-weight: bold;\">{sample_alert_data_payload.severity}</span>" in html_content
    assert f"<strong>Provider:</strong> {sample_alert_data_payload.provider.upper()}" in html_content
    assert f"<pre>{{\"{'info_ses'}\": \"{'some ses details'}\"}}</pre>" in html_content.replace(" ", "")
    assert f"<small>Policy ID: {sample_alert_data_payload.policy_id}</small>" in html_content
