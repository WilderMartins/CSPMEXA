import pytest
from httpx import AsyncClient
from app.main import app

from app.core.security import TokenData

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service_name": "api_gateway_service"}

@pytest.mark.asyncio
async def test_protected_route_with_mocked_auth(mocker):
    # Mock a função get_current_user para retornar um usuário fake
    mocker.patch(
        "app.core.security.get_current_user",
        return_value=TokenData(email="test@example.com", id=1),
    )

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(
            "/api/v1/protected-test",
            headers={"Authorization": "Bearer fake-token"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "message": "Você está autenticado no gateway!",
        "user_email": "test@example.com",
        "user_id": 1,
    }
