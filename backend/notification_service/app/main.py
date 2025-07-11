from fastapi import FastAPI
from app.core.config import settings
from app.api.v1.notification_controller import router as notification_router
import logging

# Configure logging based on settings
logging.basicConfig(level=settings.LOG_LEVEL.upper() if settings.LOG_LEVEL else logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
)

@app.on_event("startup")
async def startup_event():
    logger.info(f"'{settings.PROJECT_NAME} - v{settings.APP_VERSION}' starting up...")
    logger.info(f"Log level set to: {logging.getLevelName(logger.getEffectiveLevel())}")
    if not all([settings.SMTP_HOST, settings.SMTP_PORT, settings.EMAILS_FROM_EMAIL, settings.DEFAULT_CRITICAL_ALERT_RECIPIENT_EMAIL]):
        logger.warning("SMTP email notification settings are not fully configured. Email sending might fail.")
    else:
        logger.info(f"Email notifications configured to send from: {settings.EMAILS_FROM_EMAIL} via {settings.SMTP_HOST}:{settings.SMTP_PORT}")
        logger.info(f"Default critical alert recipient: {settings.DEFAULT_CRITICAL_ALERT_RECIPIENT_EMAIL}")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"'{settings.PROJECT_NAME}' shutting down...")

@app.get("/health", tags=["Health Check"])
async def health_check():
    # Basic health check. Could be expanded to check SMTP connectivity if needed.
    return {"status": "ok", "service_name": settings.PROJECT_NAME, "version": settings.APP_VERSION}

# Include the notification router
# All endpoints in notification_controller.py will be prefixed with /api/v1
# (e.g., /api/v1/notify/email)
app.include_router(
    notification_router,
    prefix=settings.API_V1_STR, # The controller itself has /notify in its paths
    tags=["Notifications"]
)

if __name__ == "__main__":
    import uvicorn

    service_port = settings.NOTIFICATION_SERVICE_PORT
    reload_uvicorn = settings.RELOAD_UVICORN
    log_level_uvicorn = settings.LOG_LEVEL.lower()

    logger.info(f"Starting Uvicorn for {settings.PROJECT_NAME} locally on port {service_port}...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=service_port,
        reload=reload_uvicorn,
        log_level=log_level_uvicorn
    )
