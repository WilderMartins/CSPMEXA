from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from fastapi.concurrency import run_in_threadpool
from typing import List, Union

from app.schemas.notification_schema import (
    EmailNotificationRequest,
    WebhookNotificationRequest,
    GoogleChatNotificationRequest, # Adicionado
    NotificationResponse,
    AlertDataPayload
)
from app.services.email_service import send_email_notification_sync
from app.services.webhook_service import send_webhook_notification_sync
from app.services.google_chat_service import send_google_chat_notification_sync # Adicionado
from app.core.config import settings
from app.core.security import verify_internal_api_key
import logging

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(verify_internal_api_key)])

# --- Email Notification ---
async def send_email_background(
    recipient_email: Union[str, List[str]], # Atualizado para aceitar lista
    subject: str,
    alert_data: AlertDataPayload
):
    logger.info(f"Background task: Sending email to {recipient_email} for alert: {alert_data.title}")
    try:
        success = await run_in_threadpool(
            send_email_notification_sync,
            recipient_email=recipient_email,
            subject=subject,
            alert_data=alert_data
        )
        if success:
            logger.info(f"Email successfully dispatched to {recipient_email} for alert: {alert_data.title}")
        else:
            logger.error(f"Failed to dispatch email to {recipient_email} for alert: {alert_data.title}")
    except Exception as e:
        logger.exception(f"Exception in background email task for {recipient_email}: {e}")

@router.post("/notify/email", response_model=NotificationResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_email_notification(
    notification_request: EmailNotificationRequest,
    background_tasks: BackgroundTasks
):
    recipient = notification_request.to_email or settings.DEFAULT_CRITICAL_ALERT_RECIPIENT_EMAIL
    if not recipient:
        logger.error("No recipient email address provided and no default recipient configured for email.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Recipient email address is missing and no default is configured.")

    subject = notification_request.subject or f"CSPMEXA Critical Alert: {notification_request.alert_data.title}"
    background_tasks.add_task(
        send_email_background,
        recipient_email=recipient,
        subject=subject,
        alert_data=notification_request.alert_data
    )
    logger.info(f"Email notification task for '{subject}' to '{recipient}' has been scheduled.")
    return NotificationResponse(
        status="accepted",
        message="Email notification task accepted and will be processed in the background.",
        recipient=str(recipient), # Garantir que seja string para o schema
        notification_type="email"
    )

# --- Webhook Notification ---
async def send_webhook_background(
    target_url: str, # URL já resolvida (específica ou default)
    alert_data: AlertDataPayload
):
    logger.info(f"Background task: Sending webhook to {target_url} for alert: {alert_data.title}")
    try:
        success = await run_in_threadpool(
            send_webhook_notification_sync,
            alert_data=alert_data,
            target_url=target_url # Passar a URL resolvida
        )
        if success:
            logger.info(f"Webhook successfully dispatched to {target_url} for alert: {alert_data.title}")
        else:
            logger.error(f"Failed to dispatch webhook to {target_url} for alert: {alert_data.title}")
    except Exception as e:
        logger.exception(f"Exception in background webhook task for {target_url}: {e}")

@router.post("/notify/webhook", response_model=NotificationResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_webhook_notification(
    notification_request: WebhookNotificationRequest,
    background_tasks: BackgroundTasks
):
    """
    Receives an alert payload and triggers a webhook notification.
    Uses a default webhook URL from settings if `webhook_url` is not provided.
    The webhook sending is done as a background task.
    """
    target_url = str(notification_request.webhook_url) if notification_request.webhook_url else settings.WEBHOOK_DEFAULT_URL

    if not target_url:
        logger.error("No webhook URL provided and no default webhook URL is configured.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Webhook URL is missing and no default is configured.")

    background_tasks.add_task(
        send_webhook_background,
        target_url=target_url,
        alert_data=notification_request.alert_data
    )

    logger.info(f"Webhook notification task for alert '{notification_request.alert_data.title}' to '{target_url}' has been scheduled.")
    return NotificationResponse(
        status="accepted",
        message="Webhook notification task accepted and will be processed in the background.",
        recipient=target_url,
        notification_type="webhook"
    )

# --- Google Chat Notification ---
async def send_google_chat_background(
    target_webhook_url: str, # URL já resolvida
    alert_data: AlertDataPayload
):
    logger.info(f"Background task: Sending Google Chat message to webhook for alert: {alert_data.title}")
    try:
        success = await run_in_threadpool(
            send_google_chat_notification_sync,
            alert_data=alert_data,
            target_webhook_url=target_webhook_url
        )
        if success:
            logger.info(f"Google Chat message successfully dispatched for alert: {alert_data.title} to URL ending with ...{target_webhook_url[-20:]}")
        else:
            logger.error(f"Failed to dispatch Google Chat message for alert: {alert_data.title} to URL ending with ...{target_webhook_url[-20:]}")
    except Exception as e:
        logger.exception(f"Exception in background Google Chat task for alert {alert_data.title}: {e}")

@router.post("/notify/google-chat", response_model=NotificationResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_google_chat_notification(
    notification_request: GoogleChatNotificationRequest,
    background_tasks: BackgroundTasks
):
    """
    Receives an alert payload and triggers a Google Chat notification.
    Uses a default webhook URL from settings if `webhook_url` is not provided.
    """
    target_url = str(notification_request.webhook_url) if notification_request.webhook_url else settings.GOOGLE_CHAT_WEBHOOK_URL

    if not target_url:
        logger.error("No Google Chat webhook URL provided and no default URL is configured.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google Chat webhook URL is missing and no default is configured.")

    background_tasks.add_task(
        send_google_chat_background,
        target_webhook_url=target_url,
        alert_data=notification_request.alert_data
    )

    logger.info(f"Google Chat notification task for alert '{notification_request.alert_data.title}' to webhook URL ending with ...{target_url[-20:]} has been scheduled.")
    return NotificationResponse(
        status="accepted",
        message="Google Chat notification task accepted and will be processed in the background.",
        recipient=f"Google Chat Webhook (ends ...{target_url[-20:]})", # Não expor URL completa
        notification_type="google_chat"
    )
