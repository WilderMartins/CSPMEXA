import httpx
import json
import logging
from typing import Dict, Any, Optional, Union

from app.core.config import settings # Para GOOGLE_CHAT_WEBHOOK_URL
from app.schemas.notification_schema import AlertDataPayload

logger = logging.getLogger(__name__)

# Default timeout para requisições Google Chat
GOOGLE_CHAT_TIMEOUT = 10

def format_alert_for_google_chat(alert_data: AlertDataPayload) -> Dict[str, Any]:
    """
    Formata os dados do alerta para o formato de mensagem de CardV2 do Google Chat.
    """
    card_id = f"alert-{alert_data.policy_id}-{alert_data.resource_id}-{alert_data.original_alert_created_at.timestamp() if alert_data.original_alert_created_at else 'no_ts'}"

    # Montar descrição com os campos principais
    description_html = f"<b>Recurso:</b> {alert_data.resource_id} ({alert_data.resource_type})<br>"
    description_html += f"<b>Provedor:</b> {alert_data.provider.upper()}<br>"
    if alert_data.account_id:
        description_html += f"<b>Conta/Projeto:</b> {alert_data.account_id}<br>"
    if alert_data.region:
        description_html += f"<b>Região:</b> {alert_data.region}<br>"
    description_html += f"<br><b>Descrição do Alerta:</b><br>{alert_data.description}"

    if alert_data.recommendation:
        description_html += f"<br><br><b>Recomendação:</b><br>{alert_data.recommendation}"

    # Adicionar detalhes se existirem, formatados como string simples para o card
    if alert_data.details:
        try:
            details_str = json.dumps(alert_data.details, indent=2)
            description_html += f"<br><br><b>Detalhes Adicionais:</b><br><font face=\"monospace\">{details_str.replace(' ', '&nbsp;').replace('\\n', '<br>')}</font>"
        except Exception:
            description_html += f"<br><br><b>Detalhes Adicionais:</b><br>{str(alert_data.details)}"


    # Mapear severidade para cores (aproximação, Google Chat não tem cores ricas como Slack)
    # Podemos usar emojis ou prefixos no título.
    severity_prefix = ""
    if alert_data.severity == "CRITICAL":
        severity_prefix = "🔴 CRITICAL: "
    elif alert_data.severity == "HIGH":
        severity_prefix = "🟠 HIGH: "
    elif alert_data.severity == "MEDIUM":
        severity_prefix = "🟡 MEDIUM: "
    elif alert_data.severity == "LOW":
        severity_prefix = "🔵 LOW: "

    message = {
        "cardsV2": [{
            "cardId": card_id,
            "card": {
                "header": {
                    "title": f"{severity_prefix}{alert_data.title}",
                    "subtitle": f"Política: {alert_data.policy_id}",
                    # "imageUrl": "URL_DE_UM_ICONE_DE_ALERTA_SE_TIVER" # Opcional
                },
                "sections": [{
                    "widgets": [{
                        "textParagraph": {
                            "text": description_html
                        }
                    }]
                }]
            }
        }]
    }
    # Para mensagens simples de texto:
    # simple_text = f"*{severity_prefix}{alert_data.title}*\n" \
    #               f"Recurso: {alert_data.resource_id} ({alert_data.resource_type})\n" \
    #               f"Descrição: {alert_data.description}\n" \
    #               f"Política: {alert_data.policy_id}"
    # message = {"text": simple_text}
    return message


def send_google_chat_notification_sync(
    alert_data: AlertDataPayload,
    target_webhook_url: Optional[str] = None
) -> bool:
    """
    Envia uma notificação de alerta para uma URL de webhook do Google Chat.
    Usa a URL padrão das settings se nenhuma for fornecida.
    Retorna True se a notificação foi enviada com sucesso, False caso contrário.
    """
    final_target_url = target_webhook_url or settings.GOOGLE_CHAT_WEBHOOK_URL

    if not final_target_url:
        logger.error("Google Chat webhook URL not provided and no default URL is configured. Cannot send message.")
        return False

    message_payload = format_alert_for_google_chat(alert_data)

    headers = {"Content-Type": "application/json; charset=UTF-8"}

    try:
        logger.info(f"Attempting to send Google Chat notification to webhook for alert: {alert_data.title}")
        with httpx.Client(timeout=GOOGLE_CHAT_TIMEOUT) as client:
            response = client.post(
                final_target_url,
                json=message_payload,
                headers=headers
            )

        if 200 <= response.status_code < 300:
            # Google Chat retorna um JSON com detalhes da mensagem enviada em caso de sucesso.
            # Ex: {"name":"spaces/.../messages/...", "sender":{...}, "text":"...", ...}
            logger.info(f"Google Chat notification successfully sent for alert '{alert_data.title}'. Status: {response.status_code}, Response: {response.text[:200]}")
            return True
        else:
            logger.error(f"Failed to send Google Chat notification for alert '{alert_data.title}'. Status: {response.status_code}, Response: {response.text[:500]}")
            return False

    except httpx.TimeoutException:
        logger.error(f"Timeout sending Google Chat notification for alert '{alert_data.title}'.")
        return False
    except httpx.RequestError as e:
        logger.error(f"RequestError sending Google Chat notification for alert '{alert_data.title}': {e}")
        return False
    except Exception as e:
        logger.exception(f"Unexpected error sending Google Chat notification for alert '{alert_data.title}': {e}")
        return False

if __name__ == "__main__":
    # Bloco de teste local
    class MockSettingsGSC:
        GOOGLE_CHAT_WEBHOOK_URL = "COLOQUE_A_URL_DO_SEU_WEBHOOK_GOOGLE_CHAT_AQUI"
        # Outras settings
        AWS_REGION = "us-east-1"
        EMAILS_FROM_EMAIL = "test@example.com"


    # settings = MockSettingsGSC() # Descomentar para testar

    if not settings.GOOGLE_CHAT_WEBHOOK_URL:
        print("Skipping Google Chat test: GOOGLE_CHAT_WEBHOOK_URL not set in (mocked) settings.")
    else:
        print(f"Preparing to send test Google Chat message to default webhook for alert.")

        import datetime
        mock_alert_gsc = AlertDataPayload(
            resource_id="test-gsc-res",
            resource_type="Test::GSC::Resource",
            provider="test_gsc_provider",
            severity="CRITICAL",
            title="Critical Test Google Chat Alert",
            description="This is a test Google Chat notification sent via script.",
            policy_id="TEST_GSC_POLICY_003",
            account_id="test-gsc-account",
            region="gsc-region-1",
            details={"gsc_key": "gsc_value", "reason": "Direct script execution for GSC testing."},
            recommendation="Verify Google Chat room received the card message.",
            original_alert_created_at=datetime.datetime.now(datetime.timezone.utc)
        )

        success = send_google_chat_notification_sync(
            alert_data=mock_alert_gsc
        )

        if success:
            print(f"Test Google Chat message successfully sent.")
        else:
            print(f"Failed to send test Google Chat message.")
            print("Check logs and settings (GOOGLE_CHAT_WEBHOOK_URL).")

```
