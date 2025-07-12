import httpx
import json
import logging
from typing import Dict, Any, Optional

from app.core.config import settings # Para WEBHOOK_DEFAULT_URL e outros settings
from app.schemas.notification_schema import AlertDataPayload

logger = logging.getLogger(__name__)

# Default timeout para requisições webhook, pode ser configurável via settings
WEBHOOK_TIMEOUT = 10 # settings.WEBHOOK_TIMEOUT_SECONDS or 10

def send_webhook_notification_sync(
    alert_data: AlertDataPayload,
    target_url: Optional[str] = None
    # custom_headers: Optional[Dict[str, str]] = None # Para futura expansão
) -> bool:
    """
    Envia uma notificação de alerta para uma URL de webhook especificada.
    Usa a URL padrão das settings se nenhuma for fornecida.
    Retorna True se a notificação foi enviada com sucesso (status 2xx), False caso contrário.
    Esta é uma função síncrona (bloqueante), destinada a ser chamada via run_in_threadpool.
    """
    final_target_url = target_url or settings.WEBHOOK_DEFAULT_URL

    if not final_target_url:
        logger.error("Webhook target URL not provided and no default URL is configured. Cannot send webhook.")
        return False

    # Preparar o payload. O AlertDataPayload já é um modelo Pydantic,
    # então podemos convertê-lo para dict para enviar como JSON.
    payload_dict = alert_data.model_dump(by_alias=True) if hasattr(alert_data, 'model_dump') else alert_data.dict(by_alias=True)

    headers = {
        "Content-Type": "application/json",
        # Adicionar quaisquer headers customizados aqui, se configurados
        # Ex: "X-API-Key": settings.WEBHOOK_SECRET_KEY
    }
    # if custom_headers:
    #     headers.update(custom_headers)

    try:
        logger.info(f"Attempting to send webhook notification to: {final_target_url}")
        # Usar httpx.Client para chamadas síncronas
        with httpx.Client(timeout=WEBHOOK_TIMEOUT) as client:
            response = client.post(
                final_target_url,
                json=payload_dict, # httpx.Client.post envia 'json' como application/json
                headers=headers
            )

        # Verificar se a resposta foi bem-sucedida (status code 2xx)
        if 200 <= response.status_code < 300:
            logger.info(f"Webhook notification successfully sent to {final_target_url}. Status: {response.status_code}")
            return True
        else:
            logger.error(f"Failed to send webhook notification to {final_target_url}. Status: {response.status_code}, Response: {response.text[:500]}") # Limita o tamanho do log da resposta
            return False

    except httpx.TimeoutException:
        logger.error(f"Timeout sending webhook notification to {final_target_url}.")
        return False
    except httpx.RequestError as e:
        logger.error(f"RequestError sending webhook to {final_target_url}: {e}")
        return False
    except Exception as e:
        logger.exception(f"Unexpected error sending webhook to {final_target_url}: {e}")
        return False

if __name__ == "__main__":
    # Bloco de teste local (requer configuração de .env ou settings mockadas)

    # Para testar, você precisaria de um endpoint de webhook para receber os dados.
    # Pode usar algo como https://webhook.site/

    # Mockar settings para teste local se config.py não estiver totalmente configurado
    class MockSettings:
        WEBHOOK_DEFAULT_URL = "COLOQUE_SUA_URL_DE_TESTE_WEBHOOK_AQUI" # Ex: de webhook.site
        # Outras settings que possam ser necessárias
        # ...

    # settings = MockSettings() # Descomentar e ajustar para testar

    if not settings.WEBHOOK_DEFAULT_URL:
        print("Skipping webhook test: WEBHOOK_DEFAULT_URL not set in (mocked) settings.")
    else:
        print(f"Preparing to send test webhook to: {settings.WEBHOOK_DEFAULT_URL}")

        import datetime
        mock_alert_for_test = AlertDataPayload(
            resource_id="test-webhook-res",
            resource_type="Test::Webhook::Resource",
            provider="test_webhook_provider",
            severity="HIGH",
            title="High Severity Test Webhook Alert",
            description="This is a test webhook notification sent directly from webhook_service.py script.",
            policy_id="TEST_WEBHOOK_POLICY_001",
            account_id="test-webhook-account",
            region="webhook-region-1",
            details={"key": "value", "reason": "Direct script execution for webhook testing."},
            recommendation="Verify webhook endpoint received the data correctly.",
            original_alert_created_at=datetime.datetime.now(datetime.timezone.utc)
        )

        success = send_webhook_notification_sync(
            alert_data=mock_alert_for_test
            # target_url="outra_url_se_quiser_ignorar_default"
        )

        if success:
            print(f"Test webhook successfully sent to {settings.WEBHOOK_DEFAULT_URL}.")
        else:
            print(f"Failed to send test webhook to {settings.WEBHOOK_DEFAULT_URL}.")
            print("Check logs and settings (WEBHOOK_DEFAULT_URL).")
