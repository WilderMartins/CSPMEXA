import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.api.v1 import notification_controller, management_controller
from app.core.logging_config import setup_logging

# Configurar logging
setup_logging()
logger = logging.getLogger(__name__)

from starlette_prometheus import metrics, PrometheusMiddleware

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
)
app.add_middleware(PrometheusMiddleware)
app.add_route("/metrics", metrics)

# Middleware de tratamento de erros
@app.middleware("http")
async def error_handling_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        logger.exception(f"Ocorreu um erro não tratado no notification_service: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Ocorreu um erro interno no notification_service."},
        )

@app.on_event("startup")
async def startup_event():
    logger.info(f"Iniciando o serviço: {settings.PROJECT_NAME}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"Encerrando o serviço: {settings.PROJECT_NAME}")

@app.get("/health", tags=["Health Check"])
def health_check():
    return {"status": "ok"}

app.include_router(
    notification_controller.router,
    prefix=settings.API_V1_STR,
    tags=["Notifications"],
)

app.include_router(
    management_controller.channels_router,
    prefix=f"{settings.API_V1_STR}/management/channels",
    tags=["Management - Channels"],
)

app.include_router(
    management_controller.rules_router,
    prefix=f"{settings.API_V1_STR}/management/rules",
    tags=["Management - Rules"],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8003,
        reload=settings.RELOAD_UVICORN,
        log_level=settings.LOG_LEVEL.lower(),
    )
