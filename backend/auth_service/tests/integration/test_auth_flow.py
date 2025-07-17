import pytest
from dotenv import load_dotenv
load_dotenv(dotenv_path="backend/auth_service/.env.test")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch

from app.main import app
from app.core.config import settings
from app.db.session import get_db
from app.models.user_model import Base

# --- Configuração do Banco de Dados de Teste ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Criar as tabelas no banco de dados de teste
Base.metadata.create_all(bind=engine)

# --- Sobrescrever a dependência get_db para usar o banco de dados de teste ---
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# --- Cliente de Teste ---
client = TestClient(app)

# --- Testes de Integração ---

@pytest.fixture(scope="function")
def db_session():
    """Fixture para limpar o banco de dados antes de cada teste."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@patch("app.services.google_oauth_service.google_oauth_service.exchange_code_for_tokens")
@patch("app.services.google_oauth_service.google_oauth_service.get_google_user_info")
def test_google_callback_creates_new_user_and_returns_token(
    mock_get_user_info, mock_exchange_code, db_session
):
    """
    Testa o fluxo completo de callback do Google para um novo usuário.
    Verifica se o usuário é criado no banco de dados e se um token JWT é retornado.
    """
    # --- Mock das chamadas ao Google ---
    mock_exchange_code.return_value = {"access_token": "fake_google_access_token"}
    mock_get_user_info.return_value = {
        "sub": "google_id_12345",
        "email": "testuser@example.com",
        "name": "Test User",
        "picture": "http://example.com/pic.jpg",
    }

    # --- Fazer a requisição ao endpoint de callback ---
    response = client.get("/api/v1/auth/google/callback?code=fake_auth_code")

    # --- Verificações ---
    # 1. A requisição deve ser um redirecionamento para o frontend
    # O TestClient segue o redirecionamento, então a resposta final será 404
    # porque o frontend não está rodando. Verificamos o histórico.
    assert len(response.history) == 1
    redirect_response = response.history[0]
    assert redirect_response.status_code == 307
    redirect_location = redirect_response.headers["location"]
    assert settings.FRONTEND_URL_AUTH_CALLBACK in redirect_location
    assert "token=" in redirect_location

    # 2. O usuário deve ter sido criado no banco de dados de teste
    from app.models.user_model import User
    user = db_session.query(User).filter_by(email="testuser@example.com").first()
    assert user is not None
    assert user.google_id == "google_id_12345"
    assert user.full_name == "Test User"

    # 3. O token JWT no redirecionamento deve ser válido (opcional, mais complexo)
    # Poderíamos decodificar o token e verificar os claims
    token = redirect_location.split("token=")[1]
    from jose import jwt
    decoded_token = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert decoded_token["sub"] == str(user.id)
    assert decoded_token["email"] == "testuser@example.com"
    assert decoded_token["role"] == "User"
