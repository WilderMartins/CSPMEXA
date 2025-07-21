import httpx
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class AuditServiceClient:
    def __init__(self):
        self.base_url = settings.AUDIT_SERVICE_URL

    async def create_event(self, actor: str, action: str, resource: str = None, details: dict = None):
        if not self.base_url:
            logger.warning("AUDIT_SERVICE_URL não está configurado. Evento de auditoria não será enviado.")
            return

        event_data = {
            "actor": actor,
            "action": action,
            "resource": resource,
            "details": details,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(f"{self.base_url}/events/", json=event_data)
                response.raise_for_status()
                logger.info(f"Evento de auditoria enviado com sucesso: {action} por {actor}")
            except httpx.RequestError as e:
                logger.error(f"Erro ao enviar evento de auditoria para {e.request.url!r}: {e}")

audit_service_client = AuditServiceClient()
