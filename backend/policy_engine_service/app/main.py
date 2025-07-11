from fastapi import FastAPI
from app.core.config import settings
from app.api.v1 import analysis_controller # Assuming your analysis controller is here
from app.api.v1 import alerts_controller  # Import the new alerts controller
from app.db.session import engine # Import engine for creating tables
from app.models.alert_model import Base as AlertBase # Import Base from your models

# Function to create tables, can be called on startup for development/simplicity
# For production, Alembic migrations are preferred.
def create_db_and_tables():
    # This will create tables based on models that use AlertBase
    AlertBase.metadata.create_all(bind=engine)
    # If you have other Bases for other models, create them here as well.
    # e.g., from app.models.other_model import Base as OtherBase
    # OtherBase.metadata.create_all(bind=engine)


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    # Lifespan events for startup/shutdown (FastAPI 0.90.0+)
    # For older versions, use @app.on_event("startup") and @app.on_event("shutdown")
)

@app.on_event("startup")
async def on_startup():
    # Create database tables on startup
    # In a production environment, you would typically use Alembic migrations
    # This is okay for development or simple deployments
    print("Creating database tables for Policy Engine Service...")
    create_db_and_tables()
    print("Database tables created (if they didn't exist).")


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
