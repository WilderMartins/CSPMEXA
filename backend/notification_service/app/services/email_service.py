from emails import Message
from emails.template import JinjaTemplate
from app.core.config import settings
from app.schemas.notification_schema import AlertDataPayload
import logging
from typing import Optional, Union, List # Added List
import datetime # Added datetime

logger = logging.getLogger(__name__)

# Synchronous function for sending email, as 'emails' library is blocking.
# In FastAPI, this should be called via `run_in_threadpool` from an async endpoint
# or used within a BackgroundTask.
def send_email_notification_sync(
    recipient_email: Union[str, List[str]], # Can be a single email or list of emails
    subject: str,
    alert_data: AlertDataPayload,
    # template_name: str = "alert_notification.html" # Template string is now inline
) -> bool:
    """
    Sends an email notification (synchronous blocking call).
    Returns True if email was sent successfully, False otherwise.
    """
    if not all([settings.SMTP_HOST, settings.SMTP_PORT, settings.EMAILS_FROM_EMAIL]):
        logger.error("SMTP settings (SMTP_HOST, SMTP_PORT, EMAILS_FROM_EMAIL) are not fully configured. Cannot send email.")
        return False

    # HTML Body Template
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

    # Ensure alert_data is a dict for rendering, using by_alias for Pydantic model fields
    alert_data_dict = alert_data.model_dump(by_alias=True) if hasattr(alert_data, 'model_dump') else alert_data.dict(by_alias=True)

    message_params = {"alert": alert_data_dict}
    html_content = html_body_template.render(**message_params)

    msg = Message(
        html=html_content,
        subject=subject,
        mail_from=(settings.EMAILS_FROM_NAME or "CSPMEXA Platform", settings.EMAILS_FROM_EMAIL)
    )

    smtp_options = {
        "host": settings.SMTP_HOST,
        "port": int(settings.SMTP_PORT), # Ensure port is int
        "tls": settings.SMTP_TLS,
        "ssl": settings.SMTP_SSL,
        "user": settings.SMTP_USER or None, # Ensure None if empty string
        "password": settings.SMTP_PASSWORD or None, # Ensure None if empty string
        "timeout": 20, # Increased timeout
    }
    # Clean up None values for user/password as 'emails' lib might not handle empty strings well
    if not smtp_options["user"]: del smtp_options["user"]
    if not smtp_options["password"]: del smtp_options["password"]

    try:
        logger.info(f"Attempting to send email to {recipient_email} via {settings.SMTP_HOST}:{settings.SMTP_PORT}")
        response = msg.send(to=recipient_email, smtp=smtp_options)

        # msg.send returns a Response object which might not have status_code directly in all cases or versions.
        # Success is often indicated by the absence of an exception and a valid response.
        # A common check for 'emails' library is that response is not None and no error in response.message
        if response is not None: # Basic check, specific success codes depend on SMTP server and library version
             # Example: response.status_code might be available if it's an SMTPResponse object
            if hasattr(response, 'status_code') and response.status_code in [250, 251, 252]:
                 logger.info(f"Email successfully sent to {recipient_email}. SMTP Response: {getattr(response, 'message', 'No message')}")
                 return True
            elif not hasattr(response, 'status_code'): # If no status_code, assume success if no exception
                 logger.info(f"Email accepted for delivery to {recipient_email}. SMTP Response: {getattr(response, 'message', 'No message')}")
                 return True
            else: # Had status_code but not a success one
                 error_msg = getattr(response, 'message', 'Unknown error (bad status code)')
                 logger.error(f"Failed to send email to {recipient_email}. SMTP Status: {getattr(response, 'status_code', 'N/A')}, Message: {error_msg}")
                 return False
        else: # Response was None
            logger.error(f"Failed to send email to {recipient_email}. No response from SMTP server or send method.")
            return False

    except Exception as e:
        logger.exception(f"Error sending email to {recipient_email} via {settings.SMTP_HOST}: {e}")
        return False

if __name__ == "__main__":
    # This block is for local testing of the email sending functionality.
    # It requires the .env file to be correctly set up at the root of this service,
    # or relevant environment variables to be available.

    # Adjust path for dotenv to load from backend/notification_service/.env if it exists for local testing
    # from dotenv import load_dotenv
    # load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../.env'))
    # Re-initialize settings if you load .env here for a standalone test
    # settings = get_settings(load_custom_env=True) # You'd need to modify get_settings for this

    if not settings.DEFAULT_CRITICAL_ALERT_RECIPIENT_EMAIL:
        print("Skipping email test: DEFAULT_CRITICAL_ALERT_RECIPIENT_EMAIL not set in config.")
    elif not all([settings.SMTP_HOST, settings.SMTP_PORT, settings.EMAILS_FROM_EMAIL]):
        print("Skipping email test: SMTP settings (HOST, PORT, FROM_EMAIL) are not fully configured.")
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
