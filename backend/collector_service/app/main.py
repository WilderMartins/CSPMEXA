import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.api.v1 import aws_collector_controller, gcp_collector_controller, huawei_collector_controller, azure_collector_controller, google_workspace_controller, m365_collector_controller
from app.core.logging_config import setup_logging

# Configurar logging
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Middleware de tratamento de erros
@app.middleware("http")
async def error_handling_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        logger.exception(f"Ocorreu um erro não tratado no collector_service: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Ocorreu um erro interno no collector_service."},
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

# Incluir os roteadores
app.include_router(aws_collector_controller.router, prefix=f"{settings.API_V1_STR}/collect/aws", tags=["AWS Collector"])
app.include_router(gcp_collector_controller.router, prefix=f"{settings.API_V1_STR}/collect/gcp", tags=["GCP Collector"])
app.include_router(huawei_collector_controller.router, prefix=f"{settings.API_V1_STR}/collect/huawei", tags=["Huawei Collector"])
app.include_router(azure_collector_controller.router, prefix=f"{settings.API_V1_STR}/collect/azure", tags=["Azure Collector"])
app.include_router(google_workspace_controller.router, prefix=f"{settings.API_V1_STR}/collect/googleworkspace", tags=["Google Workspace Collector"])
app.include_router(m365_collector_controller.router, prefix=f"{settings.API_V1_STR}/collect/m365", tags=["Microsoft 365 Collector"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)
