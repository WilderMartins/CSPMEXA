import httpx
from app.core.config import settings
from app.schemas.alert_schema import AlertSchema # Para tipar o alerta que será enviado
# Ou um schema específico para o payload de notificação, se for diferente
# from app.schemas.notification_payload_schema import NotificationPayload
import logging

logger = logging.getLogger(__name__)

class NotificationServiceClient:
    def __init__(self, base_url: str, timeout: int = 10):
        self.base_url = base_url
        self.timeout = timeout
        # Criar um cliente HTTPX que pode ser reutilizado
        # No entanto, para chamadas únicas ou infrequentes, um cliente temporário é ok.
        # Para uso intensivo, gerenciar um cliente persistente via lifespan events do FastAPI é melhor.
        # Por simplicidade no MVP, criaremos um cliente por chamada ou o manteremos simples.

    async def send_critical_alert_notification(self, alert: AlertSchema) -> bool:
        """
        Envia uma notificação para o Notification Service sobre um alerta crítico.
        Retorna True se a notificação foi aceita pelo Notification Service, False caso contrário.
        """
        if not self.base_url:
            logger.warning("NOTIFICATION_SERVICE_URL not configured. Skipping notification.")
            return False

        notification_endpoint = f"{self.base_url}/notify/email" # Endpoint no Notification Service

        # O Notification Service espera um payload do tipo EmailNotificationRequest,
        # que contém um campo `alert_data` do tipo AlertDataPayload.
        # Precisamos mapear nosso AlertSchema (ou o AlertModel do DB) para AlertDataPayload.
        # Para MVP, vamos assumir que AlertSchema é suficientemente compatível ou que
        # o NotificationService é flexível com campos extras se AlertDataPayload for um subconjunto.
        # O ideal seria ter um schema NotificationPayload no Policy Engine que corresponda
        # exatamente ao AlertDataPayload esperado pelo NotificationService.

        # Mapeamento de AlertSchema para o formato esperado por AlertDataPayload
        # (principalmente para `original_alert_created_at`)
        alert_data_for_notification = {
            "resource_id": alert.resource_id,
            "resource_type": alert.resource_type,
            "account_id": alert.account_id,
            "region": alert.region,
            "provider": alert.provider,
            "severity": alert.severity.value, # Enviar o valor do enum
            "title": alert.title,
            "description": alert.description,
            "policy_id": alert.policy_id,
            "status": alert.status.value if alert.status else None, # Enviar o valor do enum
            "details": alert.details,
            "recommendation": alert.recommendation,
            "created_at": alert.created_at, # Renomeado para original_alert_created_at no payload
            "updated_at": alert.updated_at, # Renomeado para original_alert_updated_at no payload
        }

        payload_to_send = {
            # "to_email": None, # Deixar o Notification Service usar o default por enquanto
            # "subject": f"CRITICAL Alert: {alert.title}", # Ou deixar o Notification Service gerar
            "alert_data": alert_data_for_notification
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(notification_endpoint, json=payload_to_send)

            if response.status_code == 202: # Accepted
                logger.info(f"Notification for alert '{alert.title}' (ID: {alert.id}) accepted by Notification Service.")
                return True
            else:
                logger.error(f"Failed to send notification for alert ID {alert.id} to Notification Service. "
                             f"Status: {response.status_code}, Response: {response.text}")
                return False
        except httpx.RequestError as e:
            logger.error(f"HTTPX RequestError sending notification for alert ID {alert.id}: {e}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected error sending notification for alert ID {alert.id}: {e}")
            return False

# Instância do cliente para ser usada no serviço
notification_client = NotificationServiceClient(base_url=settings.NOTIFICATION_SERVICE_URL)
