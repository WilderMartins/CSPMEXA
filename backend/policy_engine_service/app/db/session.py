from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings # Importar as settings atualizadas onde ASSEMBLED_DATABASE_URL é definida

# Usar a URL montada ou diretamente fornecida a partir das settings
SQLALCHEMY_DATABASE_URL = settings.ASSEMBLED_DATABASE_URL

engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# A função create_policy_engine_tables ainda é útil para inicialização/migrações
# e precisa ser mantida ou adaptada para Alembic.

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
