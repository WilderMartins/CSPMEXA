import pytest
from dotenv import load_dotenv
load_dotenv(dotenv_path="backend/auth_service/.env.test")

from unittest.mock import patch, AsyncMock

from app.core.config import settings

@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_google_callback_creates_new_user_and_returns_token(client, db_session):
    """
    Testa o fluxo completo de callback do Google para um novo usuário.
    Verifica se o usuário é criado no banco de dados e se um token JWT é retornado.
    """
    with patch("app.services.google_oauth_service.google_oauth_service.exchange_code_for_tokens", new_callable=AsyncMock) as mock_exchange_code, \
         patch("app.services.google_oauth_service.google_oauth_service.get_google_user_info", new_callable=AsyncMock) as mock_get_user_info, \
         patch("app.services.user_service.audit_service_client.create_event", new_callable=AsyncMock) as mock_audit_event:

        # --- Configuração dos Mocks ---
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
    assert len(response.history) == 1
    redirect_response = response.history[0]
    assert redirect_response.status_code == 307
    redirect_location = redirect_response.headers["location"]
    assert settings.FRONTEND_URL_AUTH_CALLBACK in redirect_location
    assert "token=" in redirect_location

    from app.models.user_model import User
    user = db_session.query(User).filter_by(email="testuser@example.com").first()
    assert user is not None
    assert user.google_id == "google_id_12345"
    assert user.full_name == "Test User"

    token = redirect_location.split("token=")[1]
    from jose import jwt
    decoded_token = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert decoded_token["sub"] == str(user.id)
    assert decoded_token["email"] == "testuser@example.com"
    assert "run:analysis" in decoded_token["permissions"]
    mock_audit_event.assert_called_once()
