from fastapi import FastAPI
from app.core.config import settings
from app.api.v1 import collector_controller

app = FastAPI(
    title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json"
)


@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "ok"}


# Incluir roteadores da API
app.include_router(
    collector_controller.router,
    prefix=settings.API_V1_STR + "/collect",
    tags=["AWS Collector"],
)

if __name__ == "__main__":
    import uvicorn

    # Lembre-se de descomentar CMD e EXPOSE no Dockerfile
    # uvicorn.run(app, host="0.0.0.0", port=8001)
    # Para desenvolvimento local:
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
