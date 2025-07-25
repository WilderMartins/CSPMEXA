import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import TokenData, require_permission

client = TestClient(app)

@pytest.mark.asyncio
@patch("app.services.http_client.auth_service_client.get")
@patch("app.services.http_client.collector_service_client.post")
@patch("app.services.http_client.policy_engine_service_client.post")
@patch("app.core.security.get_current_user")
async def test_s3_analysis_end_to_end_flow(
    mock_get_current_user,
    mock_policy_engine_post,
    mock_collector_post,
    mock_auth_get
):
    # 1. Mockar o get_current_user para simular um usuário autenticado com a permissão correta
    mock_get_current_user.return_value = TokenData(id=1, email="test@test.com", permissions=["run:analysis"])

    # 2. Mockar a resposta do auth_service para o get_credentials
    mock_auth_response = AsyncMock()
    mock_auth_response.status_code = 200
    mock_auth_response.json.return_value = {"aws_access_key_id": "test", "aws_secret_access_key": "test"}
    mock_auth_get.return_value = mock_auth_response

    # 3. Mockar a resposta do collector_service
    mock_collector_response = AsyncMock()
    mock_collector_response.status_code = 200
    mock_collector_response.json.return_value = [
        {"name": "public-bucket", "acl": {"is_public": True}}
    ]
    mock_collector_post.return_value = mock_collector_response

    # 4. Mockar a resposta do policy_engine_service
    mock_policy_engine_response = AsyncMock()
    mock_policy_engine_response.status_code = 200
    mock_policy_engine_response.json.return_value = [
            {
                "id": 1,
                "resource_id": "public-bucket",
                "resource_type": "S3Bucket",
                "account_id": "123456789012",
                "region": "us-east-1",
                "provider": "aws",
                "severity": "CRITICAL",
                "title": "Bucket S3 com ACL pública",
                "description": "A política do bucket S3 permite acesso público.",
                "policy_id": "S3_Public_Policy_V2",
                "status": "OPEN",
                "details": {"bucket_name": "public-bucket"},
                "recommendation": "Revise a política do bucket.",
                "created_at": "2023-11-15T10:00:00Z",
                "updated_at": "2023-11-15T10:00:00Z",
                "first_seen_at": "2023-11-15T10:00:00Z",
                "last_seen_at": "2023-11-15T10:00:00Z",
            }
    ]
    mock_policy_engine_post.return_value = mock_policy_engine_response

    # 5. Chamar o endpoint de análise no API Gateway
    app.dependency_overrides[require_permission("run:analysis")] = lambda: mock_get_current_user.return_value
    from fastapi.testclient import TestClient
    client = TestClient(app)
    headers = {"Authorization": "Bearer testtoken"}
    with patch("app.core.security.jwt.decode") as mock_decode:
        mock_decode.return_value = {"sub": "1", "email": "test@test.com", "permissions": ["run:analysis"]}
        response = client.post("/api/v1/analyze/aws/s3?linked_account_id=1", headers=headers)
    app.dependency_overrides = {}

    # 6. Verificações
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Bucket S3 com ACL pública"
    assert data[0]["severity"] == "CRITICAL"

    # Verificar se os mocks foram chamados
    mock_auth_get.assert_called_once()
    mock_collector_post.assert_called_once()
    mock_policy_engine_post.assert_called_once()
