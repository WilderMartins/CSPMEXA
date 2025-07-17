import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch

from app.main import app
from app.tests.integration.test_auth_flow import db_session, client # Reutilizar fixtures
from app.schemas.linked_account_schema import LinkedAccountCreate
from app.services.token_service import token_service
from app.models.user_model import User, UserRole

@pytest.fixture
def admin_token_headers(db_session: Session) -> dict:
    # Criar um usuário admin para o teste
    admin_user = User(email="admin@test.com", role=UserRole.ADMINISTRATOR, is_active=True)
    db_session.add(admin_user)
    db_session.commit()

    # Gerar um token para este usuário
    token = token_service.create_jwt_token(subject=str(admin_user.id), claims={"role": admin_user.role.value})
    return {"Authorization": f"Bearer {token}"}

def test_create_linked_account_as_admin(client: TestClient, admin_token_headers: dict):
    """
    Testa a criação de uma conta vinculada por um administrador.
    """
    account_data = {
        "name": "Prod AWS",
        "provider": "aws",
        "account_id": "999888777666",
        "credentials": {"aws_access_key_id": "testkey", "aws_secret_access_key": "testsecret"}
    }

    # Mockar a chamada para o Vault no credentials_service
    with patch("app.services.credentials_service.credentials_service.vault_client") as mock_vault:
        mock_vault.secrets.kv.v2.create_or_update_secret.return_value = None

        response = client.post("/api/v1/accounts/", headers=admin_token_headers, json=account_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Prod AWS"
        assert data["account_id"] == "999888777666"
        mock_vault.secrets.kv.v2.create_or_update_secret.assert_called_once()

def test_get_linked_accounts(client: TestClient, admin_token_headers: dict):
    """
    Testa a listagem de contas vinculadas.
    """
    response = client.get("/api/v1/accounts/", headers=admin_token_headers)
    assert response.status_code == 200
    # A lista pode estar vazia ou conter o item do teste anterior, dependendo da ordem
    assert isinstance(response.json(), list)

def test_create_linked_account_as_non_admin_fails(client: TestClient, db_session: Session):
    """
    Testa que um usuário não-admin não pode criar uma conta vinculada.
    """
    # Criar um usuário normal
    user = User(email="user@test.com", role=UserRole.USER, is_active=True)
    db_session.add(user)
    db_session.commit()
    token = token_service.create_jwt_token(subject=str(user.id), claims={"role": user.role.value})
    headers = {"Authorization": f"Bearer {token}"}

    account_data = {"name": "Fail Account", "provider": "aws", "account_id": "111", "credentials": {}}
    response = client.post("/api/v1/accounts/", headers=headers, json=account_data)

    assert response.status_code == 403 # Forbidden
    assert "User does not have the required 'Administrator' role" in response.json()["detail"]
