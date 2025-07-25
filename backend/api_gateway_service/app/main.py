from fastapi import FastAPI, Depends
from app.core.config import settings
from app.api.v1 import auth_router, data_router, alerts_router, dashboard_router, users_router, audit_router, remediation_router
from app.services import http_client # Import para fechar o cliente HTTP na saída
from app.core.security import TokenData, get_current_user # Para o endpoint de teste de autenticação
from app.core.logging_config import setup_logging
import logging

setup_logging()
logger = logging.getLogger(__name__)

from starlette_prometheus import metrics, PrometheusMiddleware

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    version="0.1.1", # Version bump
)
app.add_middleware(PrometheusMiddleware)
app.add_route("/metrics", metrics)

@app.on_event("startup")
async def startup_event():
    logger.info(f"{settings.PROJECT_NAME} starting up...")
    # Logar URLs dos serviços downstream para fácil verificação
    logger.info(f"Auth Service URL: {settings.AUTH_SERVICE_URL}")
    logger.info(f"Collector Service URL: {settings.COLLECTOR_SERVICE_URL}")
    logger.info(f"Policy Engine Service URL: {settings.POLICY_ENGINE_SERVICE_URL}")

@app.on_event("shutdown")
async def shutdown_event():
    await http_client.close_clients() # Fecha as sessões HTTPX dos clientes
    logger.info(f"{settings.PROJECT_NAME} shutting down. HTTPX client sessions closed.")


@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "ok", "service_name": settings.PROJECT_NAME}

# Endpoint de teste para verificar se a autenticação JWT está funcionando no gateway
@app.get(settings.API_V1_STR + "/protected-test", tags=["Test"])
async def protected_test_endpoint(current_user: TokenData = Depends(get_current_user)):
    return {"message": "Você está autenticado no gateway!", "user_email": current_user.email, "user_id": current_user.id}


# Incluir os roteadores da API
# O prefixo settings.API_V1_STR é o prefixo base para todos os endpoints do gateway.
# Os roteadores individuais podem ter seus próprios sub-prefixos.

# auth_router lida com /api/v1/auth/*
app.include_router(
    auth_router.router,
    prefix=settings.API_V1_STR + "/auth",  # Ex: /api/v1/auth/google/login
    tags=["Authentication"]
)

# data_router lida com /api/v1/collect/* e /api/v1/analyze/*
app.include_router(
    data_router.router,
    prefix=settings.API_V1_STR, # O data_router já tem prefixos internos /collect e /analyze
    tags=["Data Collection & Analysis Orchestration"]
)

# alerts_router lida com /api/v1/alerts/*
app.include_router(
    alerts_router.router,
    prefix=settings.API_V1_STR + "/alerts", # Ex: /api/v1/alerts/
    tags=["Alerts Management"]
)

# dashboard_router lida com /api/v1/dashboard/*
app.include_router(
    dashboard_router.router,
    prefix=settings.API_V1_STR + "/dashboard",
    tags=["Dashboard"]
)

# users_router lida com /api/v1/users/*
app.include_router(
    users_router.router,
    prefix=settings.API_V1_STR, # O prefixo /users já está no roteador
    tags=["Users Management"]
)

# audit_router lida com /api/v1/audit/*
app.include_router(
    audit_router.router,
    prefix=settings.API_V1_STR, # O prefixo /audit já está no roteador
    tags=["Audit Trails"]
)

# remediation_router lida com /api/v1/remediate/*
app.include_router(
    remediation_router.router,
    prefix=settings.API_V1_STR, # O prefixo /remediate já está no roteador
    tags=["Remediation"]
)


if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting Uvicorn for {settings.PROJECT_NAME} locally...")
    uvicorn.run("main:app", host="0.0.0.0", port=8050, reload=True)
