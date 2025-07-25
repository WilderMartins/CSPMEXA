import pytest
from unittest.mock import MagicMock, patch
from httpx import Response
from app.services.google_oauth_service import GoogleOAuthService
from app.core.config import settings

@pytest.fixture
def google_oauth_service():
    return GoogleOAuthService()

@patch('app.services.google_oauth_service.httpx.AsyncClient.post')
@pytest.mark.asyncio
async def test_exchange_code_for_token_success(mock_post, google_oauth_service):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": "fake_access_token",
        "refresh_token": "fake_refresh_token",
        "expires_in": 3600,
            "id_token": "fake_id_token",
    }
    mock_post.return_value = mock_response

    tokens = await google_oauth_service.exchange_code_for_tokens("fake_code")
    assert tokens["access_token"] == "fake_access_token"

@patch('app.services.google_oauth_service.httpx.AsyncClient.post')
@pytest.mark.asyncio
async def test_exchange_code_for_token_failure(mock_post, google_oauth_service):
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_post.return_value = mock_response

    with pytest.raises(Exception):
        await google_oauth_service.exchange_code_for_token("fake_code")

@patch('app.services.google_oauth_service.httpx.AsyncClient.get')
@pytest.mark.asyncio
async def test_get_google_user_info_success(mock_get, google_oauth_service):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "sub": "12345",
        "email": "test@example.com",
        "name": "Test User"
    }
    mock_get.return_value = mock_response

    user_info = await google_oauth_service.get_google_user_info("fake_token")
    assert user_info["email"] == "test@example.com"

@patch('app.services.google_oauth_service.httpx.AsyncClient.get')
@pytest.mark.asyncio
async def test_get_google_user_info_failure(mock_get, google_oauth_service):
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_get.return_value = mock_response

    with pytest.raises(Exception):
        await google_oauth_service.get_google_user_info("fake_token")
