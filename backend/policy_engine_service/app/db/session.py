from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings # Importar as settings atualizadas

# Usar a URL montada ou diretamente fornecida
SQLALCHEMY_DATABASE_URL = settings.ASSEMBLED_ALERT_DATABASE_URL

engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para os modelos SQLAlchemy (importada de models.alert_model)
# from .models.alert_model import Base
# Não precisamos criar tabelas a partir daqui, apenas usar a sessão.

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
