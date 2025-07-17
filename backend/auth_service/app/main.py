import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.config import settings
from app.api.v1 import auth_controller, admin_controller
from app.db.session import engine
from app.models import user_model
from app.core.logging_config import setup_logging # Importar a configuração de logging

# Configurar o logging estruturado ANTES de instanciar o app
setup_logging()
logger = logging.getLogger(__name__)

# Cria as tabelas no banco de dados (se não existirem)
user_model.Base.metadata.create_all(bind=engine)

from app.core.rate_limiter import limiter

# Configuração do Rate Limiter
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Registrar o limiter no app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Middleware de tratamento de erros
@app.middleware("http")
async def error_handling_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        logger.exception(f"Ocorreu um erro não tratado: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Ocorreu um erro interno no servidor."},
        )

@app.on_event("startup")
async def startup_event():
    logger.info(f"Iniciando o serviço: {settings.PROJECT_NAME}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"Encerrando o serviço: {settings.PROJECT_NAME}")

@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "ok"}

# Incluir os roteadores da API
app.include_router(
    auth_controller.router,
    prefix=settings.API_V1_STR + "/auth",
    tags=["Authentication"]
)

app.include_router(
    admin_controller.router,
    prefix=settings.API_V1_STR + "/admin",
    tags=["Admin"]
)

if __name__ == "__main__":
    import uvicorn
    # O uvicorn usará a configuração de logging já definida
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
