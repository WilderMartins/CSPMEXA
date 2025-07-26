import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from typing import List, Optional, Any, Coroutine, Dict # Adicionado Dict
from datetime import datetime, timezone, timedelta

from ..app.gcp import gcp_compute_collector
from app.schemas.gcp_compute import GCPComputeInstanceData, GCPFirewallData, GCPComputeNetworkInterface, GCPComputeNetworkInterfaceAccessConfig, GCPComputeServiceAccount, GCPComputeScheduling, GCPComputeAttachedDisk, GCPFirewallAllowedRule, GCPFirewallLogConfig
from app.core.config import Settings
from google.cloud.exceptions import Forbidden, NotFound, GoogleCloudError
from google.cloud import compute_v1 # Adicionado import compute_v1
from google.cloud.compute_v1.types import Instance, Firewall, Tags # Para tipos de resposta mockados

# --- Fixtures ---

@pytest.fixture
def mock_gcp_settings() -> Settings:
    return Settings()

@pytest.fixture(autouse=True)
def override_gcp_collector_settings(mock_gcp_settings: Settings):
    # Patching app.core.config.settings will affect all modules importing it.
    # Também fazemos patch do cache do client_manager para garantir isolamento.
    with patch('app.gcp.gcp_client_manager._clients_cache', new_callable=dict), \
         patch('app.core.config.settings', mock_gcp_settings):
        # Se gcp_compute_collector ou gcp_client_manager importam 'settings' de app.core.config,
        # este patch global os afetará durante a execução deste fixture.
        yield

@pytest.fixture
def mock_compute_instances_client():
    with patch('app.gcp.gcp_client_manager.get_compute_client') as mock_get_client:
        mock_client_instance = MagicMock()
        # aggregated_list é um método que retorna um iterador, então o mock precisa refletir isso.
        # Para chamadas assíncronas, o mock do método deve ser um AsyncMock se a chamada no código é `await client.method()`
        # No entanto, google-cloud-compute usa métodos síncronos que retornam iteradores ou PageIterators.
        # O coletor os usa de forma síncrona, então o MagicMock padrão é suficiente.
        mock_client_instance.aggregated_list = MagicMock()
        mock_get_client.return_value = mock_client_instance
        yield mock_client_instance

@pytest.fixture
def mock_compute_firewalls_client():
    with patch('app.gcp.gcp_client_manager.get_compute_firewalls_client') as mock_get_client:
        mock_client_instance = MagicMock()
        mock_client_instance.list = MagicMock() # list retorna um iterador
        mock_get_client.return_value = mock_client_instance
        yield mock_client_instance

@pytest.fixture
def mock_project_id_resolver_success():
    with patch('app.gcp.gcp_compute_collector.get_gcp_project_id', return_value="test-gcp-project") as mock_resolver:
        yield mock_resolver

@pytest.fixture
def mock_project_id_resolver_failure():
    with patch('app.gcp.gcp_compute_collector.get_gcp_project_id', return_value=None) as mock_resolver:
        yield mock_resolver

# --- Helper para criar mock de instância ---
def create_mock_gcp_instance(
    id_str: str, name: str, zone: str, machine_type_url: str, status: str,
    creation_timestamp_str: str, project_id: str,
    public_ip: Optional[str] = None, private_ip: Optional[str] = "10.0.0.1",
    service_account_email: Optional[str] = "default",
    scopes: Optional[List[str]] = None,
    tags_list: Optional[List[str]] = None,
    labels_dict: Optional[Dict[str,str]] = None
) -> Instance: # Usar o tipo compute_v1.Instance para o mock

    mock_instance = Instance() # Objeto tipo do SDK
    mock_instance.id = int(id_str) # ID é int no objeto Instance
    mock_instance.name = name
    mock_instance.zone = f"projects/{project_id}/zones/{zone}"
    mock_instance.machine_type = machine_type_url
    mock_instance.status = status
    mock_instance.creation_timestamp = creation_timestamp_str # String no objeto Instance

    ni = compute_v1.types.NetworkInterface()
    # Corrigido para o nome de campo correto do protobuf (geralmente snake_case com 'IP' capitalizado se parte do nome)
    # O campo correto é 'network_i_p' ou verificar a definição exata no tipo NetworkInterface
    # No entanto, a biblioteca google-cloud-compute para Python mapeia os campos protobuf para atributos Python.
    # O nome do atributo Python para networkIP é network_i_p.
    # Se o objeto ni for um MagicMock, podemos apenas atribuir. Se for um objeto real, precisa ser o nome correto.
    # Vamos assumir que o objeto ni é uma instância real de compute_v1.types.NetworkInterface para o mock
    ni.network_i_p = private_ip # Campo correto é network_i_p
    if public_ip:
        ac = compute_v1.types.AccessConfig()
        ac.nat_i_p = public_ip # Campo correto é nat_i_p
        ac.name = "External NAT"
        ac.type = "ONE_TO_ONE_NAT" # type_ é usado se 'type' for uma palavra reservada, mas aqui 'type' é o campo
        ni.access_configs = [ac]
    mock_instance.network_interfaces = [ni]

    if service_account_email:
        sa = compute_v1.types.ServiceAccount()
        sa.email = service_account_email
        if scopes:
            sa.scopes = scopes
        mock_instance.service_accounts = [sa]

    if tags_list:
        instance_tags = Tags()
        instance_tags.items = tags_list
        mock_instance.tags = instance_tags

    if labels_dict:
        # labels são diretamente um map<string, string> no protobuf
        # o objeto Python SDK representa isso como um dicionário.
        mock_instance.labels = labels_dict

    # Outros campos podem ser adicionados conforme necessário para os testes
    mock_instance.disks = [] # Exemplo
    mock_instance.scheduling = compute_v1.types.Scheduling()

    return mock_instance

# --- Testes para get_gcp_compute_instances ---

@pytest.mark.asyncio
async def test_get_gcp_compute_instances_no_project_id(mock_project_id_resolver_failure, mock_compute_instances_client):
    result = await gcp_compute_collector.get_gcp_compute_instances(project_id=None)
    assert len(result) == 1
    assert result[0].id == "ERROR_PROJECT_ID_MISSING"
    mock_compute_instances_client.aggregated_list.assert_not_called()

@pytest.mark.asyncio
async def test_get_gcp_compute_instances_aggregated_list_error(mock_project_id_resolver_success, mock_compute_instances_client):
    mock_compute_instances_client.aggregated_list.side_effect = GoogleCloudError("Simulated aggregated_list failure")
    result = await gcp_compute_collector.get_gcp_compute_instances(project_id="test-gcp-project")
    assert len(result) == 1
    assert result[0].id == "ERROR_LIST_INSTANCES_test-gcp-project"
    assert "Failed to list GCP Compute Instances: Simulated aggregated_list failure" in result[0].error_details

@pytest.mark.asyncio
async def test_get_gcp_compute_instances_no_instances_returned(mock_project_id_resolver_success, mock_compute_instances_client):
    # aggregated_list retorna um iterador de tuplas (scope, instances_scoped_list_object)
    # onde instances_scoped_list_object pode ter um campo 'instances' que é uma lista.
    # Se não há instâncias, o campo 'instances' pode estar ausente ou a lista ser vazia.
    mock_scope_list = MagicMock()
    mock_scope_list.instances = [] # Nenhuma instância neste escopo
    mock_compute_instances_client.aggregated_list.return_value = iter([("zones/us-central1-a", mock_scope_list)])

    result = await gcp_compute_collector.get_gcp_compute_instances(project_id="test-gcp-project")
    assert result == []
    mock_compute_instances_client.aggregated_list.assert_called_once_with(project="test-gcp-project")

@pytest.mark.asyncio
async def test_get_gcp_compute_instances_one_instance(mock_project_id_resolver_success, mock_compute_instances_client):
    now_str = datetime.now(timezone.utc).isoformat()
    mock_inst_native = create_mock_gcp_instance(
        id_str="12345", name="test-instance-1", zone="us-central1-a",
        machine_type_url="projects/test-gcp-project/zones/us-central1-a/machineTypes/n1-standard-1",
        status="RUNNING", creation_timestamp_str=now_str, project_id="test-gcp-project",
        public_ip="35.0.0.1", private_ip="10.0.0.5",
        service_account_email="test-sa@test-gcp-project.iam.gserviceaccount.com",
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
        tags_list=["http-server", "env-dev"],
        labels_dict={"owner": "team-a"}
    )

    mock_scope_list = MagicMock()
    mock_scope_list.instances = [mock_inst_native]
    mock_compute_instances_client.aggregated_list.return_value = iter([("zones/us-central1-a", mock_scope_list)])

    result: List[GCPComputeInstanceData] = await gcp_compute_collector.get_gcp_compute_instances(project_id="test-gcp-project")

    assert len(result) == 1
    instance_data = result[0]
    assert instance_data.id == "12345" # Convertido para str no schema
    assert instance_data.name == "test-instance-1"
    assert instance_data.project_id == "test-gcp-project"
    assert instance_data.extracted_zone == "us-central1-a"
    assert instance_data.extracted_machine_type == "n1-standard-1"
    assert instance_data.status == "RUNNING"
    assert instance_data.public_ip_addresses == ["35.0.0.1"]
    assert instance_data.private_ip_addresses == ["10.0.0.5"]
    assert instance_data.service_accounts[0].email == "test-sa@test-gcp-project.iam.gserviceaccount.com"
    assert "https://www.googleapis.com/auth/cloud-platform" in instance_data.service_accounts[0].scopes
    assert instance_data.tags_items == ["http-server", "env-dev"]
    assert instance_data.labels == {"owner": "team-a"}
    assert instance_data.error_details is None

# --- Testes para get_gcp_firewall_rules ---

@pytest.mark.asyncio
async def test_get_gcp_firewall_rules_no_project_id(mock_project_id_resolver_failure, mock_compute_firewalls_client):
    result = await gcp_compute_collector.get_gcp_firewall_rules(project_id=None)
    assert len(result) == 1
    assert result[0].id == "ERROR_PROJECT_ID_MISSING"
    mock_compute_firewalls_client.list.assert_not_called()

@pytest.mark.asyncio
async def test_get_gcp_firewall_rules_list_error(mock_project_id_resolver_success, mock_compute_firewalls_client):
    mock_compute_firewalls_client.list.side_effect = GoogleCloudError("Simulated firewall list failure")
    result = await gcp_compute_collector.get_gcp_firewall_rules(project_id="test-gcp-project")
    assert len(result) == 1
    assert result[0].id == "ERROR_LIST_FIREWALLS_test-gcp-project"
    assert "Failed to list GCP Firewall Rules: Simulated firewall list failure" in result[0].error_details

@pytest.mark.asyncio
async def test_get_gcp_firewall_rules_no_rules_returned(mock_project_id_resolver_success, mock_compute_firewalls_client):
    mock_compute_firewalls_client.list.return_value = iter([])
    result = await gcp_compute_collector.get_gcp_firewall_rules(project_id="test-gcp-project")
    assert result == []
    mock_compute_firewalls_client.list.assert_called_once_with(project="test-gcp-project")

@pytest.mark.asyncio
async def test_get_gcp_firewall_rules_one_rule(mock_project_id_resolver_success, mock_compute_firewalls_client):
    now_str = datetime.now(timezone.utc).isoformat()
    mock_firewall_native = Firewall() # Objeto tipo do SDK
    mock_firewall_native.id = 78901
    mock_firewall_native.name = "allow-ssh-external"
    mock_firewall_native.network = "projects/test-gcp-project/global/networks/default"
    mock_firewall_native.priority = 1000
    mock_firewall_native.direction = "INGRESS"
    mock_firewall_native.disabled = False
    mock_firewall_native.creation_timestamp = now_str

    allowed_rule = compute_v1.types.Allowed()
    allowed_rule.i_p_protocol = "tcp" # Corrigido para i_p_protocol
    allowed_rule.ports = ["22"]
    mock_firewall_native.allowed = [allowed_rule]
    mock_firewall_native.source_ranges = ["0.0.0.0/0"]

    log_config = compute_v1.types.Firewall.LogConfig()
    log_config.enable = True
    mock_firewall_native.log_config = log_config

    mock_compute_firewalls_client.list.return_value = iter([mock_firewall_native])

    result: List[GCPFirewallData] = await gcp_compute_collector.get_gcp_firewall_rules(project_id="test-gcp-project")

    assert len(result) == 1
    fw_data = result[0]
    assert fw_data.id == "78901"
    assert fw_data.name == "allow-ssh-external"
    assert fw_data.project_id == "test-gcp-project"
    assert fw_data.extracted_network_name == "default"
    assert fw_data.direction == "INGRESS"
    assert fw_data.priority == 1000
    assert not fw_data.disabled
    assert fw_data.source_ranges == ["0.0.0.0/0"]
    assert len(fw_data.allowed) == 1
    assert fw_data.allowed[0].ip_protocol == "tcp"
    assert fw_data.allowed[0].ports == ["22"]
    assert fw_data.log_config.enable is True
    assert fw_data.error_details is None

# A função `_parse_gcp_timestamp` no `gcp_compute_collector.py` foi ajustada para lidar melhor com o formato de timestamp do GCP,
# especialmente com o 'Z', e para normalizar para UTC. Se o timestamp for naive, ele será considerado UTC.
# Estes testes fornecem uma cobertura básica para os coletores de Compute Engine.
# Mais testes podem ser adicionados para cobrir outros campos e cenários de erro.
