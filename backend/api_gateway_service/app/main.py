from fastapi import FastAPI
from app.core.config import settings
from app.api.v1 import auth_router, data_router
import logging

# Configuração básica de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    version="0.1.0",  # Adicionar uma versão
)


@app.on_event("startup")
async def startup_event():
    logger.info("API Gateway starting up...")
    logger.info(f"Auth Service URL: {settings.AUTH_SERVICE_URL}")
    logger.info(f"Collector Service URL: {settings.COLLECTOR_SERVICE_URL}")
    logger.info(f"Policy Engine Service URL: {settings.POLICY_ENGINE_SERVICE_URL}")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("API Gateway shutting down...")


@app.get("/health", tags=["Health Check"])
async def health_check():
    # Poderia verificar a conectividade com serviços downstream se necessário
    return {"status": "ok", "service": settings.PROJECT_NAME}


# Incluir roteadores da API
# O prefixo settings.API_V1_STR já está nos roteadores individuais se necessário,
# mas é comum aplicar um prefixo global para todos os endpoints do gateway.
# Vamos assumir que os roteadores auth_router e data_router já têm seus prefixos /auth e /data (ou similar)
# e o API_V1_STR será o prefixo base para o gateway.
# Ex: /api/v1/gateway/auth/google/login , /api/v1/gateway/analyze/aws/s3
# Se os roteadores internos não tiverem prefixo, o prefixo aqui se aplicará.
# No nosso caso, auth_router já tem /auth, data_router já tem /analyze.
# Portanto, o prefixo aqui será o prefixo geral do gateway.

# Montando os roteadores. O prefixo API_V1_STR será aplicado a todos eles.
app.include_router(
    auth_router.router, prefix=settings.API_V1_STR, tags=["Authentication"]
)
app.include_router(
    data_router.router, prefix=settings.API_V1_STR, tags=["Data Analysis & Collection"]
)


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Uvicorn for API Gateway...")
    # Lembre-se de descomentar CMD e EXPOSE no Dockerfile (porta 8050)
    # uvicorn.run(app, host="0.0.0.0", port=8050)
    # Para desenvolvimento local:
    uvicorn.run("main:app", host="0.0.0.0", port=8050, reload=True)
