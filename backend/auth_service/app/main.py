from fastapi import FastAPI
from app.core.config import settings
from app.db.session import engine, Base  # , create_db_and_tables

# from app.api.v1 import auth_controller # Será importado quando o controller estiver pronto


# --- Database table creation (for development) ---
# Remova ou mova para um script de migração (Alembic) para produção
def create_tables():
    Base.metadata.create_all(bind=engine)


# create_tables() # Chamada para criar tabelas ao iniciar (cuidado em produção)
# --- End Database table creation ---


app = FastAPI(
    title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json"
)


@app.on_event("startup")
async def startup_event():
    # Idealmente, use Alembic para migrações.
    # Para desenvolvimento, podemos criar tabelas aqui.
    # Certifique-se que o DB exista antes de rodar.
    try:
        create_tables()
        print("Database tables created (if they didn't exist).")
    except Exception as e:
        print(f"Error creating tables: {e}")
        print("Please ensure the database is running and accessible.")


@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "ok"}


# Incluir roteadores da API
# app.include_router(auth_controller.router, prefix=settings.API_V1_STR, tags=["Auth"]) # Será descomentado

if __name__ == "__main__":
    import uvicorn

    # Lembre-se de descomentar CMD e EXPOSE no Dockerfile
    # uvicorn.run(app, host="0.0.0.0", port=8000)
    # Para desenvolvimento local:
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
