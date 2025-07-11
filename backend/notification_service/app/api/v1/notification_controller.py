from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.concurrency import run_in_threadpool # To run blocking IO in a thread pool
from typing import List

from app.schemas.notification_schema import EmailNotificationRequest, NotificationResponse, AlertDataPayload
from app.services.email_service import send_email_notification_sync # Import the synchronous version
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

async def send_email_background(
    recipient_email: str,
    subject: str,
    alert_data: AlertDataPayload
):
    """
    Helper function to be run in a background task.
    This wraps the synchronous email sending logic.
    """
    logger.info(f"Background task: Sending email to {recipient_email} for alert: {alert_data.title}")
    try:
        # success = send_email_notification_sync( # Direct call for sync function
        #     recipient_email=recipient_email,
        #     subject=subject,
        #     alert_data=alert_data
        # )
        # Using run_in_threadpool to ensure non-blocking behavior even if send_email_notification_sync
        # had some unexpected blocking parts or if the library itself uses threads internally badly.
        # However, for a purely CPU-bound or well-behaved blocking IO, direct call in background task is often fine.
        # For robust non-blocking of the event loop with blocking IO, run_in_threadpool is safer.
        success = await run_in_threadpool(
            send_email_notification_sync, # Pass the callable
            recipient_email=recipient_email, # Pass arguments
            subject=subject,
            alert_data=alert_data
        )

        if success:
            logger.info(f"Email successfully dispatched to {recipient_email} for alert: {alert_data.title}")
        else:
            logger.error(f"Failed to dispatch email to {recipient_email} for alert: {alert_data.title}")
    except Exception as e:
        logger.exception(f"Exception in background email task for {recipient_email}: {e}")


@router.post("/notify/email", response_model=NotificationResponse, status_code=202) # 202 Accepted
async def trigger_email_notification(
    notification_request: EmailNotificationRequest,
    background_tasks: BackgroundTasks
):
    """
    Receives an alert payload and triggers an email notification.
    For MVP, it sends to a default recipient if `to_email` is not provided.
    The email sending is done as a background task.
    """
    recipient = notification_request.to_email or settings.DEFAULT_CRITICAL_ALERT_RECIPIENT_EMAIL
    if not recipient:
        logger.error("No recipient email address provided and no default recipient configured.")
        raise HTTPException(status_code=400, detail="Recipient email address is missing and no default is configured.")

    subject = notification_request.subject or f"CSPMEXA Critical Alert: {notification_request.alert_data.title}"

    # Add the email sending task to the background
    background_tasks.add_task(
        send_email_background, # Use the async wrapper for the background task
        recipient_email=recipient,
        subject=subject,
        alert_data=notification_request.alert_data
    )

    logger.info(f"Email notification task for '{subject}' to '{recipient}' has been scheduled.")

    return NotificationResponse(
        status="accepted",
        message="Email notification task accepted and will be processed in the background.",
        recipient=recipient,
        notification_type="email"
    )

# Example of a simple health check for this router if needed
# @router.get("/notify/health", tags=["Notification Health"])
# async def notification_health():
#     return {"status": "ok", "service": "Notification Endpoints"}
