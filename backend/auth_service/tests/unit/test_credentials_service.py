import pytest
from unittest.mock import MagicMock, patch
from app.services.credentials_service import CredentialsService
from app.schemas.linked_account_schema import LinkedAccountCreate

@pytest.fixture
def credentials_service():
    return CredentialsService()

@patch('app.services.credentials_service.get_vault_client')
@patch('app.services.credentials_service.linked_account_crud')
def test_save_credentials_for_account(mock_crud, mock_get_vault_client, credentials_service):
    mock_db = MagicMock()
    mock_vault_client = MagicMock()
    mock_get_vault_client.return_value = mock_vault_client
    credentials_service.vault_client = mock_vault_client

    mock_crud.get_by_account_id.return_value = None
    mock_crud.create.return_value.id = 1

    account_in = LinkedAccountCreate(
        user_id=1,
        provider="aws",
        account_id="test_account_id",
        name="test_account",
        credentials={"key": "value"}
    )

    result = credentials_service.save_credentials_for_account(mock_db, account_in=account_in)

    mock_vault_client.secrets.kv.v2.create_or_update_secret.assert_called_once()
    assert result["linked_account_id"] == 1

@patch('app.services.credentials_service.get_vault_client')
def test_get_credentials_for_account(mock_get_vault_client, credentials_service):
    mock_vault_client = MagicMock()
    mock_get_vault_client.return_value = mock_vault_client
    credentials_service.vault_client = mock_vault_client

    mock_vault_client.secrets.kv.v2.read_secret_version.return_value = {
        "data": {"data": {"key": "value"}}
    }
    credentials = credentials_service.get_credentials_for_account(1)
    assert credentials == {"key": "value"}

@patch('app.services.credentials_service.get_vault_client')
def test_get_credentials_for_account_not_found(mock_get_vault_client, credentials_service):
    mock_vault_client = MagicMock()
    mock_get_vault_client.return_value = mock_vault_client
    credentials_service.vault_client = mock_vault_client

    mock_vault_client.secrets.kv.v2.read_secret_version.side_effect = Exception("InvalidPath")

    with pytest.raises(Exception):
        credentials_service.get_credentials_for_account(1)


@patch('app.services.credentials_service.get_vault_client')
@patch('app.services.credentials_service.linked_account_crud')
def test_delete_credentials_for_account(mock_crud, mock_get_vault_client, credentials_service):
    mock_db = MagicMock()
    mock_vault_client = MagicMock()
    mock_get_vault_client.return_value = mock_vault_client
    credentials_service.vault_client = mock_vault_client

    result = credentials_service.delete_credentials_for_account(mock_db, linked_account_id=1)

    mock_vault_client.secrets.kv.v2.delete_metadata_and_all_versions.assert_called_once()
    mock_crud.remove.assert_called_once()
    assert result["deleted_account_id"] == 1
