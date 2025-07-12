from fastapi import FastAPI
from app.core.config import settings
from app.api.v1 import analysis_controller # Assuming your analysis controller is here
from app.api.v1 import alerts_controller  # Import the new alerts controller
# from app.db.session import engine # No longer needed here for create_all
# from app.models.alert_model import Base as AlertBase # No longer needed here for create_all

# A criação de tabelas agora é gerenciada pelo Alembic no auth_service.
# A função create_db_and_tables() e sua chamada em on_startup são removidas.

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    # Lifespan events for startup/shutdown (FastAPI 0.90.0+)
    # For older versions, use @app.on_event("startup") and @app.on_event("shutdown")
)

# @app.on_event("startup")
# async def on_startup():
#     # A criação de tabelas foi movida para as migrações Alembic
#     # gerenciadas a partir do auth_service, já que compartilham o mesmo DB.
#     # print("Creating database tables for Policy Engine Service...")
#     # create_db_and_tables() # Removido
#     # print("Database tables created (if they didn't exist).")
#     pass


@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "ok", "service": settings.PROJECT_NAME}


# Include API routers
app.include_router(
    analysis_controller.router,
    prefix=settings.API_V1_STR,
    tags=["Analysis Engine"]
)
app.include_router(
    alerts_controller.router, # Add the alerts controller router
    prefix=settings.API_V1_STR + "/alerts", # Prefix for alert endpoints
    tags=["Alerts Management"]
)

if __name__ == "__main__":
    import uvicorn
    # This part is for running locally, e.g., python app/main.py
    # The Docker CMD in Dockerfile will typically use uvicorn directly
    # uvicorn.run(app, host="0.0.0.0", port=8002) # For production-like run without reload
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True) # For development with reload
