from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from app.core.config import settings

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# Função para obter uma sessão de DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Função para criar todas as tabelas (chamar em main.py ou via um script CLI)
def create_db_and_tables():
    Base.metadata.create_all(bind=engine)
