# Removida a importação de 'emails.Message' pois não será mais usada diretamente para envio SMTP.
# from emails import Message
from emails.template import JinjaTemplate # Mantido para renderização de HTML
from app.core.config import settings # Supondo que settings agora inclua AWS_REGION e SES_FROM_EMAIL
from app.schemas.notification_schema import AlertDataPayload
import logging
from typing import Optional, Union, List
import datetime
import boto3
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError

logger = logging.getLogger(__name__)

# HTML Body Template (mantido como estava)
html_body_template_str = """
<html>
    <head>
        <style>
            body { font-family: sans-serif; margin: 20px; background-color: #f4f4f4; color: #333; }
            .container { border: 1px solid #ddd; padding: 20px; border-radius: 8px; max-width: 650px; margin: 20px auto; background-color: #fff; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            h2 { color: #c9302c; border-bottom: 2px solid #c9302c; padding-bottom: 10px; } /* Bootstrap danger-like red */
            .alert-field { margin-bottom: 12px; line-height: 1.6; }
            .alert-field strong { color: #555; min-width: 150px; display: inline-block; }
            .details { background-color: #f9f9f9; border: 1px solid #eee; padding: 15px; margin-top:20px; border-radius: 4px; }
            pre { white-space: pre-wrap; word-wrap: break-word; background-color: #efefef; padding: 10px; border-radius: 3px; }
            hr { border: 0; border-top: 1px solid #eee; margin: 20px 0; }
            .footer { font-size: 0.9em; color: #777; text-align: center; margin-top: 20px;}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Critical Security Alert: {{ alert.title }}</h2>

            <div class="alert-field"><strong>Severity:</strong> <span style="color: {% if alert.severity == 'CRITICAL' %}#c9302c{% elif alert.severity == 'HIGH' %}#f0ad4e{% else %}#333{% endif %}; font-weight: bold;">{{ alert.severity }}</span></div>
            <div class="alert-field"><strong>Provider:</strong> {{ alert.provider.upper() if alert.provider else 'N/A' }}</div>
            <div class="alert-field"><strong>Account ID:</strong> {{ alert.account_id or 'N/A' }}</div>
            <div class="alert-field"><strong>Region:</strong> {{ alert.region or 'N/A' }}</div>
            <div class="alert-field"><strong>Resource Type:</strong> {{ alert.resource_type }}</div>
            <div class="alert-field"><strong>Resource ID:</strong> {{ alert.resource_id }}</div>

            <div class="alert-field">
                <strong>Description:</strong>
                <p>{{ alert.description }}</p>
            </div>

            {% if alert.recommendation %}
            <div class="alert-field">
                <strong>Recommendation:</strong>
                <p>{{ alert.recommendation }}</p>
            </div>
            {% endif %}

            {% if alert.details %}
            <div class="details">
                <strong>Additional Details:</strong>
                <pre>{{ alert.details | tojson(indent=2) if alert.details is mapping else alert.details }}</pre>
            </div>
            {% endif %}

            <hr>
            <p><small>Policy ID: {{ alert.policy_id }}</small></p>
            <p><small>Alert Detected At: {{ alert.original_alert_created_at.strftime('%Y-%m-%d %H:%M:%S %Z') if alert.original_alert_created_at else 'N/A' }}</small></p>
            <div class="footer">This is an automated notification from CSPMEXA.</div>
        </div>
    </body>
</html>
"""
html_body_template = JinjaTemplate(html_body_template_str)


def send_email_notification_sync(
    recipient_email: Union[str, List[str]],
    subject: str,
    alert_data: AlertDataPayload,
) -> bool:
    """
    Sends an email notification using AWS SES.
    Returns True if email was sent successfully, False otherwise.
    """
    # Verificar configurações essenciais para SES
    if not all([settings.AWS_REGION, settings.EMAILS_FROM_EMAIL]): # EMAILS_FROM_EMAIL é o remetente verificado no SES
        logger.error("AWS SES settings (AWS_REGION, EMAILS_FROM_EMAIL) are not fully configured. Cannot send email.")
        return False

    # Converter recipient_email para lista se for string única
    if isinstance(recipient_email, str):
        destination_emails = [recipient_email]
    else:
        destination_emails = recipient_email

    if not destination_emails:
        logger.error("No recipient emails provided.")
        return False

    # Renderizar o corpo HTML do e-mail
    alert_data_dict = alert_data.model_dump(by_alias=True) if hasattr(alert_data, 'model_dump') else alert_data.dict(by_alias=True)
    message_params = {"alert": alert_data_dict}
    html_content = html_body_template.render(**message_params)

    # Criar um cliente SES
    # As credenciais (Access Key, Secret Key) devem estar configuradas no ambiente
    # ou via role IAM se rodando em um ambiente AWS (EC2, ECS, Lambda).
    try:
        ses_client = boto3.client("ses", region_name=settings.AWS_REGION)
    except (NoCredentialsError, PartialCredentialsError) as e:
        logger.error(f"AWS credentials for SES not found or incomplete in region {settings.AWS_REGION}: {e}")
        return False
    except Exception as e: # Outros erros ao criar o cliente, como região inválida
        logger.error(f"Error creating SES client for region {settings.AWS_REGION}: {e}")
        return False

    # Construir o payload para a API send_email do SES
    # O remetente formatado (ex: "Nome <email@example.com>") pode ser usado se SES_FROM_EMAIL_ARN não for usado.
    sender_formatted = f"{settings.EMAILS_FROM_NAME or 'CSPMEXA Platform'} <{settings.EMAILS_FROM_EMAIL}>"

    try:
        response = ses_client.send_email(
            Source=sender_formatted, # Ou apenas settings.EMAILS_FROM_EMAIL se o nome não for desejado aqui
            Destination={"ToAddresses": destination_emails},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Html": {"Data": html_content, "Charset": "UTF-8"}},
            },
            # SourceArn=settings.SES_FROM_EMAIL_ARN, # Opcional, para usar configurações de autorização de envio
            # ConfigurationSetName=settings.SES_CONFIGURATION_SET_NAME # Opcional, para rastreamento de eventos
        )
        message_id = response.get("MessageId")
        logger.info(f"Email successfully sent to {', '.join(destination_emails)} via AWS SES. Message ID: {message_id}")
        return True
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        error_message = e.response.get("Error", {}).get("Message")
        logger.error(f"AWS SES ClientError sending email to {', '.join(destination_emails)}: [{error_code}] {error_message}")
        return False
    except Exception as e:
        logger.exception(f"Unexpected error sending email via AWS SES to {', '.join(destination_emails)}: {e}")
        return False

if __name__ == "__main__":
    # Este bloco de teste local precisará ser ajustado para SES.
    # Requer que as variáveis de ambiente AWS (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN opcional)
    # e AWS_REGION estejam configuradas, e que settings.EMAILS_FROM_EMAIL seja um endereço verificado no SES.

    # Exemplo de como carregar settings para teste local se config.py existir e for configurável:
    # from app.core.config import get_settings # Supondo que get_settings pode ser usado
    # settings = get_settings() # Isso pode precisar de um .env na pasta do serviço

    # Para testar, você precisaria mockar as settings ou ter um .env funcional.
    # Exemplo simplificado (assumindo que `settings` já está carregado com os valores corretos):
    if not settings.DEFAULT_CRITICAL_ALERT_RECIPIENT_EMAIL:
        print("Skipping SES email test: DEFAULT_CRITICAL_ALERT_RECIPIENT_EMAIL not set in config.")
    elif not all([settings.AWS_REGION, settings.EMAILS_FROM_EMAIL]):
        print("Skipping SES email test: AWS_REGION or EMAILS_FROM_EMAIL not configured.")
    else:
        print(f"Preparing to send test email to: {settings.DEFAULT_CRITICAL_ALERT_RECIPIENT_EMAIL}")
        print(f"From: {settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>")
        print(f"SMTP Server: {settings.SMTP_HOST}:{settings.SMTP_PORT} (TLS: {settings.SMTP_TLS}, SSL: {settings.SMTP_SSL})")
        if settings.SMTP_USER:
            print(f"SMTP User: {settings.SMTP_USER}")

        mock_alert_for_test = AlertDataPayload(
            resource_id="test-resource-smtp",
            resource_type="Test::Resource::Type",
            provider="test_provider",
            severity="CRITICAL",
            title="Critical Test Alert via SMTP",
            description="This is a test email notification sent directly from email_service.py script.",
            policy_id="TEST_SMTP_POLICY_001",
            account_id="test-account-123",
            region="test-region-1",
            details={"test_key": "test_value", "reason": "Direct script execution for testing."},
            recommendation="Verify SMTP configuration and email content.",
            original_alert_created_at=datetime.datetime.now(datetime.timezone.utc)
        )

        success = send_email_notification_sync(
            recipient_email=settings.DEFAULT_CRITICAL_ALERT_RECIPIENT_EMAIL,
            subject=f"[CSPMEXA TEST] Critical Alert: {mock_alert_for_test.title}",
            alert_data=mock_alert_for_test
        )

        if success:
            print(f"Test email successfully sent (or accepted by SMTP server) to {settings.DEFAULT_CRITICAL_ALERT_RECIPIENT_EMAIL}.")
        else:
            print(f"Failed to send test email to {settings.DEFAULT_CRITICAL_ALERT_RECIPIENT_EMAIL}.")
            print("Check logs and .env configuration.")
```
