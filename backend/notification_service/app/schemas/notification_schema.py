from pydantic import BaseModel, EmailStr, HttpUrl
from typing import Optional, Dict, Any, List, Union
import datetime

# Este é o payload de dados do alerta que é comum a diferentes tipos de notificação.
# Ele deve ser compatível com o que o policy_engine_service envia.
class AlertDataPayload(BaseModel):
    resource_id: str
    resource_type: str
    provider: str
    severity: str # Poderia ser um Enum (CRITICAL, HIGH, etc.)
    title: str
    description: str
    policy_id: str
    account_id: Optional[str] = None
    region: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    recommendation: Optional[str] = None
    # O policy_engine envia created_at e updated_at, que podem ser mapeados para original_alert_created_at
    # Se o nome do campo for diferente no policy_engine, o notification_client.py no policy_engine
    # já faz um mapeamento para este schema (ou um compatível).
    # Vamos manter os nomes consistentes com o que o email_service espera para o template.
    original_alert_created_at: Optional[datetime.datetime] = None
    # Adicionar outros campos que o policy_engine possa enviar e que sejam úteis no payload da notificação.
    # Ex: status (OPEN, RESOLVED etc.), tags, etc.
    # Por enquanto, mantendo simples e alinhado com o template de e-mail existente.

# Schema para requisição de notificação por e-mail
class EmailNotificationRequest(BaseModel):
    to_email: Optional[EmailStr] = None # Se não fornecido, usa o default das settings
    subject: Optional[str] = None
    alert_data: AlertDataPayload

# Schema para requisição de notificação por webhook
class WebhookNotificationRequest(BaseModel):
    webhook_url: Optional[HttpUrl] = None # Se não fornecido, usa o default das settings
    alert_data: AlertDataPayload
    # custom_headers: Optional[Dict[str, str]] = None # Para futura expansão

# Schema para requisição de notificação por Google Chat
class GoogleChatNotificationRequest(BaseModel):
    webhook_url: Optional[HttpUrl] = None # URL específica do webhook do Google Chat, se diferente do default
    alert_data: AlertDataPayload
    # thread_key: Optional[str] = None # Para agrupar mensagens em threads no Google Chat (futuro)

# Schema de resposta genérico para endpoints de notificação
from app.models.notification_channel_model import ChannelTypeEnum
from app.models.notification_rule_model import CloudProviderEnum, AlertSeverityEnum

class NotificationResponse(BaseModel):
    status: str # ex: "accepted", "failed"
    message: str
    recipient: Optional[Union[str, List[str]]] = None # Email, URL do webhook, ID do canal do Chat, etc.
    notification_type: str # ex: "email", "webhook", "google_chat"
    error_details: Optional[str] = None

# --- Schemas para NotificationChannel ---
class NotificationChannelBase(BaseModel):
    name: str
    type: ChannelTypeEnum
    configuration: str

class NotificationChannelCreate(NotificationChannelBase):
    pass

class NotificationChannelSchema(NotificationChannelBase):
    id: int
    class Config:
        from_attributes = True

# --- Schemas para NotificationRule ---
class NotificationRuleBase(BaseModel):
    name: str
    provider: CloudProviderEnum
    severity: AlertSeverityEnum
    channel_id: int

class NotificationRuleCreate(NotificationRuleBase):
    pass

class NotificationRuleSchema(NotificationRuleBase):
    id: int
    channel: NotificationChannelSchema # Incluir os detalhes do canal
    class Config:
        from_attributes = True
