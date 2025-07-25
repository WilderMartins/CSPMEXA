import pytest
from unittest.mock import patch, MagicMock
from typing import List, Optional, Any
from datetime import datetime, timezone

from ..app.gcp import gcp_iam_collector
from app.schemas.gcp_iam import GCPProjectIAMPolicyData, GCPIAMPolicy, GCPIAMBinding
from app.core.config import Settings
from googleapiclient.errors import HttpError # Para simular erros da API
from google.cloud.exceptions import GoogleCloudError # Para erros de inicialização de cliente

# --- Fixtures ---

@pytest.fixture
def mock_gcp_settings() -> Settings:
    return Settings()

@pytest.fixture(autouse=True)
def override_gcp_collector_settings(mock_gcp_settings: Settings):
    with patch('app.gcp.gcp_client_manager._clients_cache', new_callable=dict), \
         patch('app.core.config.settings', mock_gcp_settings):
            # Limpar cache do cliente IAM específico no módulo do coletor, se ele tiver um próprio
            if hasattr(gcp_iam_collector, 'iam_client_cache'): # Verificar se o cache existe no módulo
                gcp_iam_collector.iam_client_cache = None
            yield
            if hasattr(gcp_iam_collector, 'iam_client_cache'):
                gcp_iam_collector.iam_client_cache = None


@pytest.fixture
def mock_crm_client(): # Cloud Resource Manager client
    with patch('app.gcp.gcp_client_manager.get_cloud_resource_manager_client') as mock_get_crm_client:
        mock_client_instance = MagicMock()
        # O método projects().getIamPolicy().execute() precisa ser mockado
        mock_projects_resource = MagicMock()
        mock_get_iam_policy_method = MagicMock()

        mock_projects_resource.getIamPolicy.return_value = mock_get_iam_policy_method
        mock_client_instance.projects.return_value = mock_projects_resource

        mock_get_crm_client.return_value = mock_client_instance
        yield mock_get_iam_policy_method # Retorna o mock do método execute() para setar o return_value no teste

@pytest.fixture
def mock_project_id_resolver_success():
    with patch('app.gcp.gcp_iam_collector.get_gcp_project_id', return_value="test-iam-project") as mock_resolver:
        yield mock_resolver

@pytest.fixture
def mock_project_id_resolver_failure():
    with patch('app.gcp.gcp_iam_collector.get_gcp_project_id', return_value=None) as mock_resolver:
        yield mock_resolver

# --- Testes ---

@pytest.mark.asyncio
async def test_get_gcp_project_iam_policy_no_project_id(mock_project_id_resolver_failure, mock_crm_client):
    result = await gcp_iam_collector.get_gcp_project_iam_policy(project_id=None)
    assert result is None # Ou um objeto de erro específico, dependendo da implementação
    # mock_crm_client (que é o mock do método execute) não deve ter sido chamado
    mock_crm_client.execute.assert_not_called()


@pytest.mark.asyncio
async def test_get_gcp_project_iam_policy_http_error(mock_project_id_resolver_success, mock_crm_client):
    # Simular HttpError do googleapiclient
    # A fixture mock_crm_client já é o mock do método `execute`
    mock_resp = MagicMock()
    mock_resp.status = 403
    mock_crm_client.execute.side_effect = HttpError(resp=mock_resp, content=b'Forbidden', uri='test-uri')

    result = await gcp_iam_collector.get_gcp_project_iam_policy(project_id="test-iam-project")

    assert result is not None
    assert result.project_id == "test-iam-project"
    assert "HttpError: 403" in result.error_details
    assert result.iam_policy.bindings == [] # Política vazia em caso de erro

@pytest.mark.asyncio
async def test_get_gcp_project_iam_policy_success_basic(mock_project_id_resolver_success, mock_crm_client):
    mock_policy_response = {
        "version": 1,
        "bindings": [
            {"role": "roles/owner", "members": ["user:owner@example.com"]},
            {"role": "roles/viewer", "members": ["serviceAccount:sa@project.iam.gserviceaccount.com", "group:viewers@example.com"]}
        ],
        "etag": "test-etag-123"
    }
    mock_crm_client.execute.return_value = mock_policy_response

    result: Optional[GCPProjectIAMPolicyData] = await gcp_iam_collector.get_gcp_project_iam_policy(project_id="test-iam-project")

    assert result is not None
    assert result.project_id == "test-iam-project"
    assert result.error_details is None

    assert result.iam_policy.version == 1
    assert result.iam_policy.etag == "test-etag-123"
    assert len(result.iam_policy.bindings) == 2

    owner_binding = next(b for b in result.iam_policy.bindings if b.role == "roles/owner")
    viewer_binding = next(b for b in result.iam_policy.bindings if b.role == "roles/viewer")

    assert owner_binding.members == ["user:owner@example.com"]
    assert sorted(viewer_binding.members) == sorted(["serviceAccount:sa@project.iam.gserviceaccount.com", "group:viewers@example.com"])

    assert result.has_external_members_with_primitive_roles is False
    assert result.external_primitive_role_details == []

    mock_crm_client.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_gcp_project_iam_policy_with_external_primitive_roles(mock_project_id_resolver_success, mock_crm_client):
    mock_policy_response = {
        "version": 3,
        "bindings": [
            {"role": "roles/editor", "members": ["user:editor@example.com", "allUsers"]}, # allUsers com editor
            {"role": "roles/viewer", "members": ["allAuthenticatedUsers"]},
            {"role": "roles/storage.objectViewer", "members": ["allUsers"]} # Não primitivo, não deve ser pego
        ],
        "etag": "test-etag-456"
    }
    mock_crm_client.execute.return_value = mock_policy_response

    result = await gcp_iam_collector.get_gcp_project_iam_policy(project_id="test-iam-project")

    assert result is not None
    assert result.has_external_members_with_primitive_roles is True
    assert len(result.external_primitive_role_details) == 2
    assert "Principal externo 'allUsers' encontrado com papel primitivo 'roles/editor'." in result.external_primitive_role_details
    assert "Principal externo 'allAuthenticatedUsers' encontrado com papel primitivo 'roles/viewer'." in result.external_primitive_role_details

@pytest.mark.asyncio
async def test_get_gcp_project_iam_policy_binding_without_members(mock_project_id_resolver_success, mock_crm_client):
    # Testar se uma binding sem 'members' é tratada corretamente (deve ser lista vazia)
    mock_policy_response = {
        "version": 1,
        "bindings": [
            {"role": "roles/customRole1"} # Sem campo 'members'
        ],
        "etag": "test-etag-789"
    }
    mock_crm_client.execute.return_value = mock_policy_response

    result = await gcp_iam_collector.get_gcp_project_iam_policy(project_id="test-iam-project")

    assert result is not None
    assert len(result.iam_policy.bindings) == 1
    assert result.iam_policy.bindings[0].role == "roles/customRole1"
    assert result.iam_policy.bindings[0].members == [] # Espera lista vazia

# Adicionar teste para quando a chave 'bindings' está ausente na resposta da API
@pytest.mark.asyncio
async def test_get_gcp_project_iam_policy_no_bindings_key(mock_project_id_resolver_success, mock_crm_client):
    mock_policy_response = {
        "version": 1,
        "etag": "test-etag-nobindings"
        # Sem a chave 'bindings'
    }
    mock_crm_client.execute.return_value = mock_policy_response

    result = await gcp_iam_collector.get_gcp_project_iam_policy(project_id="test-iam-project")

    assert result is not None
    assert result.iam_policy.bindings == [] # Espera lista vazia
    assert result.error_details is None

# A função `_parse_native_iam_policy_bindings` no `gcp_iam_collector.py` foi ajustada para retornar uma lista vazia se `native_bindings` for `None`,
# e o `_check_external_members_in_primitive_roles` também foi ajustado para lidar com `iam_policy.bindings` potencialmente vazio.
# O coletor principal também foi ajustado para criar um `GCPIAMPolicy` com `bindings=[]` se a chave `bindings` não estiver na resposta da API, em vez de falhar.
