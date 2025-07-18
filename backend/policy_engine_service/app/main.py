import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.api.v1 import analysis_controller, alerts_controller, asset_controller, attack_path_controller
from app.core.logging_config import setup_logging
from app.db.session import engine
from app.models import alert_model

# Configurar logging
setup_logging()
logger = logging.getLogger(__name__)

# Criar tabelas
alert_model.Base.metadata.create_all(bind=engine)

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
        logger.exception(f"Ocorreu um erro não tratado no policy_engine_service: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Ocorreu um erro interno no policy_engine_service."},
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

app.include_router(analysis_controller.router, prefix=settings.API_V1_STR, tags=["Analysis"])
app.include_router(alerts_controller.router, prefix=f"{settings.API_V1_STR}/alerts", tags=["Alerts"])
app.include_router(asset_controller.router, prefix=f"{settings.API_V1_STR}/assets", tags=["Assets"])
app.include_router(attack_path_controller.router, prefix=f"{settings.API_V1_STR}/attack-paths", tags=["Attack Paths"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002, reload=True)
