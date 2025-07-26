import pytest
from unittest.mock import patch, MagicMock
from typing import List, Optional, Any
from datetime import datetime, timezone

from ..app.gcp import gcp_storage_collector
from app.schemas.gcp_storage import GCPStorageBucketData, GCPBucketIAMPolicy, GCPBucketIAMBinding, GCPBucketVersioning, GCPBucketLogging
from app.core.config import Settings # Para mockar settings se necessário (ex: default project_id)
from google.cloud.exceptions import Forbidden, NotFound, GoogleCloudError

# --- Fixtures ---

@pytest.fixture
def mock_gcp_settings() -> Settings:
    # Embora gcp_client_manager tente obter project_id de google.auth.default(),
    # os coletores geralmente recebem project_id como argumento.
    # Se precisarmos mockar um project_id padrão vindo de settings:
    # return Settings(GCP_PROJECT_ID="test-project")
    return Settings() # Default settings

@pytest.fixture(autouse=True)
def override_gcp_collector_settings(mock_gcp_settings: Settings):
    # Limpar cache de clientes do gcp_client_manager entre testes
    # para garantir que mocks sejam aplicados corretamente.
    # Isso é um pouco mais complexo porque o cache está em outro módulo.
    # Uma abordagem é mockar as funções get_X_client diretamente.
    with patch('app.gcp.gcp_client_manager._clients_cache', new_callable=dict), \
         patch('app.core.config.settings', mock_gcp_settings):
            # Se os coletores e client manager usam app.core.config.settings, este patch os afetará.
            yield

@pytest.fixture
def mock_storage_client():
    """Mock para o cliente google.cloud.storage.Client"""
    with patch('app.gcp.gcp_client_manager.get_storage_client') as mock_get_client:
        mock_client_instance = MagicMock()
        mock_get_client.return_value = mock_client_instance
        yield mock_client_instance

@pytest.fixture
def mock_project_id_resolver_success():
    """Mock para get_gcp_project_id que retorna um project_id válido."""
    with patch('app.gcp.gcp_storage_collector.get_gcp_project_id', return_value="test-project-123") as mock_resolver:
        yield mock_resolver

@pytest.fixture
def mock_project_id_resolver_failure():
    """Mock para get_gcp_project_id que simula falha em obter o project_id."""
    with patch('app.gcp.gcp_storage_collector.get_gcp_project_id', return_value=None) as mock_resolver:
        yield mock_resolver

# --- Testes ---

@pytest.mark.asyncio
async def test_get_gcp_storage_buckets_no_project_id(mock_project_id_resolver_failure, mock_storage_client):
    # Teste quando o project_id não pode ser determinado e não é fornecido
    result = await gcp_storage_collector.get_gcp_storage_buckets(project_id=None)
    assert len(result) == 1
    assert result[0].id == "ERROR_PROJECT_ID_MISSING"
    assert "GCP Project ID is required" in result[0].error_details
    mock_storage_client.list_buckets.assert_not_called()

@pytest.mark.asyncio
async def test_get_gcp_storage_buckets_list_buckets_google_cloud_error(mock_project_id_resolver_success, mock_storage_client):
    # Simula um erro genérico ao listar buckets
    mock_storage_client.list_buckets.side_effect = GoogleCloudError("Simulated list_buckets failure")

    result = await gcp_storage_collector.get_gcp_storage_buckets(project_id="test-project-123")
    assert len(result) == 1
    assert result[0].id == "ERROR_LIST_BUCKETS_test-project-123"
    assert "Failed to list GCP Storage buckets: Simulated list_buckets failure" in result[0].error_details

@pytest.mark.asyncio
async def test_get_gcp_storage_buckets_no_buckets_returned(mock_project_id_resolver_success, mock_storage_client):
    # Simula que a listagem de buckets não retorna nenhum bucket
    mock_storage_client.list_buckets.return_value = iter([]) # Iterador vazio

    result = await gcp_storage_collector.get_gcp_storage_buckets(project_id="test-project-123")
    assert result == []
    mock_storage_client.list_buckets.assert_called_once_with(project="test-project-123")

@pytest.mark.asyncio
async def test_get_gcp_storage_buckets_one_bucket_basic_data(mock_project_id_resolver_success, mock_storage_client):
    mock_bucket_native = MagicMock()
    mock_bucket_native.name = "test-bucket-1"
    mock_bucket_native.id = "test-bucket-1-id" # GCP bucket.id é o nome
    mock_bucket_native.project_number = 1234567890
    mock_bucket_native.location = "US-CENTRAL1"
    mock_bucket_native.storage_class = "STANDARD"
    mock_bucket_native.time_created = datetime.now(timezone.utc) - timedelta(days=10)
    mock_bucket_native.updated = datetime.now(timezone.utc) - timedelta(days=1)
    mock_bucket_native.versioning_enabled = True
    mock_bucket_native.logging = {'logBucket': 'logs-bucket', 'logObjectPrefix': 'test-bucket-1/'}
    mock_bucket_native.website = None
    mock_bucket_native.retention_policy = None
    mock_bucket_native.labels = {"env": "test"}

    # Mock para get_iam_policy
    mock_iam_policy_native = MagicMock()
    mock_iam_policy_native.version = 3
    mock_iam_policy_native.bindings = [
        {"role": "roles/storage.objectViewer", "members": ["user:test@example.com"]}
    ]
    mock_iam_policy_native.etag = "test-etag"
    mock_bucket_native.get_iam_policy.return_value = mock_iam_policy_native

    mock_storage_client.list_buckets.return_value = iter([mock_bucket_native])

    result: List[GCPStorageBucketData] = await gcp_storage_collector.get_gcp_storage_buckets(project_id="test-project-123")

    assert len(result) == 1
    bucket_data = result[0]

    assert bucket_data.name == "test-bucket-1"
    assert bucket_data.id == "test-bucket-1-id"
    assert bucket_data.project_number == "1234567890"
    assert bucket_data.location == "US-CENTRAL1"
    assert bucket_data.storage_class == "STANDARD" # Alias storageClass
    assert bucket_data.time_created == mock_bucket_native.time_created # Alias timeCreated
    assert bucket_data.updated == mock_bucket_native.updated

    assert bucket_data.versioning is not None
    assert bucket_data.versioning.enabled is True

    assert bucket_data.logging is not None
    assert bucket_data.logging.log_bucket == "logs-bucket"
    assert bucket_data.logging.log_object_prefix == "test-bucket-1/"

    assert bucket_data.iam_policy is not None
    assert bucket_data.iam_policy.version == 3
    assert len(bucket_data.iam_policy.bindings) == 1
    assert bucket_data.iam_policy.bindings[0].role == "roles/storage.objectViewer"
    assert bucket_data.iam_policy.bindings[0].members == ["user:test@example.com"]

    assert bucket_data.is_public_by_iam is False
    assert bucket_data.public_iam_details == []

    assert bucket_data.labels == {"env": "test"}
    assert bucket_data.error_details is None

    mock_bucket_native.get_iam_policy.assert_called_once_with(requested_policy_version=3)


@pytest.mark.asyncio
async def test_get_gcp_storage_buckets_iam_public(mock_project_id_resolver_success, mock_storage_client):
    mock_bucket_native = MagicMock()
    mock_bucket_native.name = "public-bucket"
    # ... outros campos básicos ...
    mock_bucket_native.id = "public-bucket"
    mock_bucket_native.project_number = 123
    mock_bucket_native.location = "US"
    mock_bucket_native.storage_class = "MULTI_REGIONAL"
    mock_bucket_native.time_created = datetime.now(timezone.utc)
    mock_bucket_native.updated = datetime.now(timezone.utc)
    mock_bucket_native.versioning_enabled = False
    mock_bucket_native.logging = None
    mock_bucket_native.labels = None


    mock_iam_policy_native = MagicMock()
    mock_iam_policy_native.version = 1
    mock_iam_policy_native.bindings = [
        {"role": "roles/storage.objectViewer", "members": ["allUsers"]},
        {"role": "roles/storage.legacyObjectReader", "members": ["allAuthenticatedUsers"]}
    ]
    mock_iam_policy_native.etag = "public-etag"
    mock_bucket_native.get_iam_policy.return_value = mock_iam_policy_native

    mock_storage_client.list_buckets.return_value = iter([mock_bucket_native])

    result = await gcp_storage_collector.get_gcp_storage_buckets(project_id="test-project-123")

    assert len(result) == 1
    bucket_data = result[0]
    assert bucket_data.is_public_by_iam is True
    assert len(bucket_data.public_iam_details) == 2
    assert "Role 'roles/storage.objectViewer' granted to public members: allUsers" in bucket_data.public_iam_details
    assert "Role 'roles/storage.legacyObjectReader' granted to public members: allAuthenticatedUsers" in bucket_data.public_iam_details


@pytest.mark.asyncio
async def test_get_gcp_storage_buckets_iam_policy_forbidden(mock_project_id_resolver_success, mock_storage_client):
    mock_bucket_native = MagicMock(name="bucket_with_iam_forbidden")
    mock_bucket_native.name = "iam-forbidden-bucket"
    # ... preencher outros campos básicos ...
    mock_bucket_native.id = "iam-forbidden-bucket"
    mock_bucket_native.project_number = 123
    mock_bucket_native.location = "EU"
    mock_bucket_native.storage_class = "STANDARD"
    mock_bucket_native.time_created = datetime.now(timezone.utc)
    mock_bucket_native.updated = datetime.now(timezone.utc)
    mock_bucket_native.versioning_enabled = True
    mock_bucket_native.logging = None
    mock_bucket_native.labels = None


    mock_bucket_native.get_iam_policy.side_effect = Forbidden("Simulated IAM policy forbidden")

    mock_storage_client.list_buckets.return_value = iter([mock_bucket_native])

    result = await gcp_storage_collector.get_gcp_storage_buckets(project_id="test-project-123")

    assert len(result) == 1
    bucket_data = result[0]
    assert bucket_data.name == "iam-forbidden-bucket"
    assert bucket_data.iam_policy is None
    assert "IAM policy fetch forbidden: Simulated IAM policy forbidden" in bucket_data.error_details
    assert bucket_data.is_public_by_iam is False # Default quando a política não pode ser lida


# Adicionar mais testes para outros campos (website, retention policy) e cenários de erro.
# Teste para _parse_iam_policy e _check_iam_public_access podem ser feitos separadamente
# se a lógica se tornar mais complexa.
