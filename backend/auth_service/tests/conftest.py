import pytest
from dotenv import load_dotenv
import os

# Carregar as variáveis de ambiente de teste ANTES de qualquer outra coisa.
# Isso garante que, quando os módulos da aplicação forem importados,
# eles já vejam as variáveis de ambiente corretas.
env_path = os.path.join(os.path.dirname(__file__), '..', '.env.test')
load_dotenv(dotenv_path=env_path)

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.session import get_db
from app.models.user_model import Base as UserBase
from app.models.linked_account_model import Base as LinkedAccountBase

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def db_engine():
    UserBase.metadata.create_all(bind=engine)
    LinkedAccountBase.metadata.create_all(bind=engine)
    yield engine
    UserBase.metadata.drop_all(bind=engine)
    LinkedAccountBase.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    db = TestingSessionLocal(bind=connection)

    app.dependency_overrides[get_db] = lambda: db

    yield db

    db.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c
