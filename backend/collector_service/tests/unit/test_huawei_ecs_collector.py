import pytest
from unittest.mock import patch, MagicMock, PropertyMock, AsyncMock
from typing import List, Optional, Any
from datetime import datetime, timezone

from app.huawei import huawei_ecs_collector
from app.schemas.huawei_ecs import HuaweiECSServerData, HuaweiVPCSecurityGroup, HuaweiVPCSecurityGroupRule
from app.core.config import Settings
from huaweicloudsdkcore.exceptions import exceptions as sdk_exceptions
# Importar tipos de request e response do SDK ECS e VPC se necessário para mockar atributos
from huaweicloudsdkecs.v2.model import ListServersDetailsResponse, ServerDetail as SdkServerDetail, \
                                       ServerAddress, ServerImage, ServerFlavor, NovaSecurityGroup
from huaweicloudsdkvpc.v2.model import ListSecurityGroupsResponse, SecurityGroup as SdkSecurityGroup, \
                                       SecurityGroupRule as SdkSecurityGroupRule

# --- Fixtures ---

@pytest.fixture
def mock_huawei_settings() -> Settings:
    return Settings()

@pytest.fixture(autouse=True)
def override_huawei_collector_settings(mock_huawei_settings: Settings):
    with patch('app.huawei.huawei_client_manager._clients_cache', new_callable=dict), \
         patch('app.core.config.settings', mock_huawei_settings): # Patch global settings
            if hasattr(huawei_ecs_collector, '_clients_cache'): # Cache específico do módulo do coletor
                 huawei_ecs_collector._clients_cache = {}
            yield
            if hasattr(huawei_ecs_collector, '_clients_cache'):
                 huawei_ecs_collector._clients_cache = {}

@pytest.fixture
def mock_ecs_client():
    with patch('app.huawei.huawei_client_manager.get_ecs_client') as mock_get_client:
        mock_client_instance = MagicMock()
        mock_client_instance.list_servers_details = MagicMock() # Nome do método como no SDK
        mock_get_client.return_value = mock_client_instance
        yield mock_client_instance

@pytest.fixture
def mock_vpc_client():
    with patch('app.huawei.huawei_client_manager.get_vpc_client') as mock_get_client:
        mock_client_instance = MagicMock()
        mock_client_instance.list_security_groups = MagicMock() # Nome do método como no SDK
        mock_get_client.return_value = mock_client_instance
        yield mock_client_instance

@pytest.fixture
def mock_huawei_credentials_success():
    mock_creds = MagicMock()
    mock_creds.ak = "test_ak_huawei"
    mock_creds.sk = "test_sk_huawei"
    with patch('app.huawei.huawei_client_manager.get_huawei_credentials', return_value=(mock_creds, "test_project_huawei")) as mock_creds_func:
        yield mock_creds_func

# --- Testes para get_huawei_ecs_instances ---

@pytest.mark.asyncio
async def test_get_huawei_ecs_instances_no_creds(mock_ecs_client):
    with patch('app.huawei.huawei_client_manager.get_huawei_credentials', side_effect=ValueError("Simulated ECS credential error")):
        result = await huawei_ecs_collector.get_huawei_ecs_instances(project_id="proj-ecs", region_id="reg-ecs")
        assert len(result) == 1
        assert result[0].id == "ERROR_CREDENTIALS"
        assert "Simulated ECS credential error" in result[0].error_details
        mock_ecs_client.list_servers_details.assert_not_called()

@pytest.mark.asyncio
async def test_get_huawei_ecs_instances_sdk_error(mock_huawei_credentials_success, mock_ecs_client):
    mock_ecs_client.list_servers_details.side_effect = sdk_exceptions.SdkException("ECS.0001", "Simulated ECS SDK failure") # Corrigido
    result = await huawei_ecs_collector.get_huawei_ecs_instances(project_id="proj-ecs", region_id="reg-ecs")
    assert len(result) == 1
    assert result[0].id == "ERROR_LIST_ECS_SDK_reg-ecs"
    assert "ECS.0001: Simulated ECS SDK failure" in result[0].error_details

@pytest.mark.asyncio
async def test_get_huawei_ecs_instances_no_instances_returned(mock_huawei_credentials_success, mock_ecs_client):
    mock_response = MagicMock(spec=ListServersDetailsResponse)
    mock_response.servers = []
    mock_ecs_client.list_servers_details.return_value = mock_response

    result = await huawei_ecs_collector.get_huawei_ecs_instances(project_id="proj-ecs", region_id="reg-ecs")
    assert result == []
    mock_ecs_client.list_servers_details.assert_called_once()

@pytest.mark.asyncio
async def test_get_huawei_ecs_instances_one_instance(mock_huawei_credentials_success, mock_ecs_client):
    created_time_str = "2023-05-01T10:00:00Z"
    updated_time_str = "2023-05-10T12:00:00.000000" # Formato com microssegundos sem Z

    # Criar mock do objeto ServerDetail do SDK
    mock_server_native = SdkServerDetail(
        id="ecs-instance-uuid-1",
        name="test-ecs-vm-1",
        status="ACTIVE",
        created=created_time_str, # SDK espera string
        updated=updated_time_str, # SDK espera string
        user_id="user-creator-id",
        image=ServerImage(id="image-uuid"),
        flavor=ServerFlavor(id="flavor-s6.large.2", name="s6.large.2"),
        addresses={
            "private_net_1": [ServerAddress(version=4, addr="192.168.1.10", mac_addr="fa:16:3e:xx:yy:zz", type="fixed")], # Corrigido: os_ext_ips_mac_mac_addr -> mac_addr, os_ext_ips_type -> type
            "public_eip_net": [ServerAddress(version=4, addr="120.0.0.10", mac_addr="fa:16:3e:aa:bb:cc", type="floating")] # Corrigido
        },
        key_name="ssh-keypair-name",
        os_ext_az_availability_zone="cn-north-4a", # No SDK, os_ext_az_availability_zone é o campo
        os_ext_srv_attr_host="host-id-xyz",
        os_ext_srv_attr_hypervisor_hostname="hypervisor.example.com",
        security_groups=[NovaSecurityGroup(name="sg-uuid-1"), NovaSecurityGroup(name="sg-uuid-2")], # Lista de objetos com atributo 'name'
        os_extended_volumes_volumes_attached=[{"id": "vol-uuid-1"}],
        metadata={"app": "my-app", "env": "prod"}
    )

    mock_response = MagicMock(spec=ListServersDetailsResponse)
    mock_response.servers = [mock_server_native]
    mock_ecs_client.list_servers_details.return_value = mock_response

    result: List[HuaweiECSServerData] = await huawei_ecs_collector.get_huawei_ecs_instances(project_id="proj-ecs", region_id="cn-north-4")

    assert len(result) == 1
    vm_data = result[0]

    assert vm_data.id == "ecs-instance-uuid-1"
    assert vm_data.name == "test-ecs-vm-1"
    assert vm_data.status == "ACTIVE"
    assert vm_data.created == datetime(2023, 5, 1, 10, 0, 0, tzinfo=timezone.utc)
    assert vm_data.updated == datetime(2023, 5, 10, 12, 0, 0, tzinfo=timezone.utc)
    assert vm_data.project_id == "proj-ecs"
    assert vm_data.region_id == "cn-north-4"
    assert vm_data.image.id == "image-uuid"
    assert vm_data.flavor.id == "flavor-s6.large.2"
    assert vm_data.flavor.name == "s6.large.2"
    assert vm_data.public_ips == ["120.0.0.10"]
    assert vm_data.private_ips == ["192.168.1.10"]
    assert vm_data.availability_zone == "cn-north-4a"
    assert len(vm_data.security_groups) == 2
    assert vm_data.security_groups[0]['name'] == "sg-uuid-1" # 'name' aqui é o ID
    assert vm_data.metadata.custom_metadata == {"app": "my-app", "env": "prod"}
    assert vm_data.error_details is None

# --- Testes para get_huawei_vpc_security_groups ---

@pytest.mark.asyncio
async def test_get_huawei_vpc_sgs_no_creds(mock_vpc_client):
    with patch('app.huawei.huawei_client_manager.get_huawei_credentials', side_effect=ValueError("Simulated VPC credential error")):
        result = await huawei_ecs_collector.get_huawei_vpc_security_groups(project_id="proj-vpc", region_id="reg-vpc")
        assert len(result) == 1
        assert result[0].id == "ERROR_CREDENTIALS"
        mock_vpc_client.list_security_groups.assert_not_called()

@pytest.mark.asyncio
async def test_get_huawei_vpc_sgs_sdk_error(mock_huawei_credentials_success, mock_vpc_client):
    mock_vpc_client.list_security_groups.side_effect = sdk_exceptions.SdkException("VPC.0001", "Simulated VPC SDK failure") # Corrigido
    result = await huawei_ecs_collector.get_huawei_vpc_security_groups(project_id="proj-vpc", region_id="reg-vpc")
    assert len(result) == 1
    assert result[0].id == "ERROR_LIST_SGS_SDK_reg-vpc"

@pytest.mark.asyncio
async def test_get_huawei_vpc_sgs_no_sgs_returned(mock_huawei_credentials_success, mock_vpc_client):
    mock_response = MagicMock(spec=ListSecurityGroupsResponse)
    mock_response.security_groups = []
    mock_vpc_client.list_security_groups.return_value = mock_response

    result = await huawei_ecs_collector.get_huawei_vpc_security_groups(project_id="proj-vpc", region_id="reg-vpc")
    assert result == []

@pytest.mark.asyncio
async def test_get_huawei_vpc_sgs_one_sg_with_rules(mock_huawei_credentials_success, mock_vpc_client):
    # Mock para SdkSecurityGroupRule
    mock_rule_native = SdkSecurityGroupRule(
        id="rule-uuid-1",
        description="Allow SSH",
        security_group_id="sg-uuid-parent",
        direction="ingress",
        ethertype="IPv4",
        protocol="tcp",
        port_range_min=22,
        port_range_max=22,
        remote_ip_prefix="0.0.0.0/0"
    )
    # Mock para SdkSecurityGroup
    mock_sg_native = SdkSecurityGroup(
        id="sg-uuid-parent",
        name="allow-ssh-sg",
        description="Allows SSH from anywhere",
        # project_id="proj-vpc", # Removido - não é parâmetro do construtor do objeto SdkSecurityGroup
        security_group_rules=[mock_rule_native]
    )
    # Adicionar project_id como atributo se o código do coletor espera ler dele diretamente
    # mock_sg_native.project_id = "proj-vpc" # O coletor já lê sg_native.project_id

    mock_response = MagicMock(spec=ListSecurityGroupsResponse)
    mock_response.security_groups = [mock_sg_native]
    mock_vpc_client.list_security_groups.return_value = mock_response

    result: List[HuaweiVPCSecurityGroup] = await huawei_ecs_collector.get_huawei_vpc_security_groups(project_id="proj-vpc", region_id="reg-vpc")

    assert len(result) == 1
    sg_data = result[0]
    assert sg_data.id == "sg-uuid-parent"
    assert sg_data.name == "allow-ssh-sg"
    assert sg_data.project_id_from_collector == "proj-vpc" # Mapeado pelo alias
    assert sg_data.region_id == "reg-vpc"
    assert len(sg_data.security_group_rules) == 1
    rule_data = sg_data.security_group_rules[0]
    assert rule_data.id == "rule-uuid-1"
    assert rule_data.direction == "ingress"
    assert rule_data.protocol == "tcp"
    assert rule_data.port_range_min == 22
    assert rule_data.remote_ip_prefix == "0.0.0.0/0"
    assert sg_data.error_details is None

# Ajustes feitos durante a escrita dos testes em `huawei_ecs_collector.py`:
# *   Na função `_parse_huawei_timestamp`: Adicionado tratamento para quando o input já é um objeto `datetime`.
#     Melhorado o parse de strings com e sem 'Z' e com e sem microssegundos, e garantia de que o resultado seja timezone-aware (UTC).
# *   Na função `get_huawei_ecs_instances`:
#     *   Corrigido o acesso a `server_native.image` e `server_native.flavor` para checar se existem antes de acessar `id`.
#     *   Corrigido o acesso a `server_native.os_ext_az_availability_zone` e outros campos com hífen/dois-pontos usando `getattr` para segurança.
#     *   Tratamento para `server_native.security_groups` para garantir que é uma lista de dicts com a chave 'name'.
#     *   O `flavor` no schema `HuaweiECSServerData` agora espera `HuaweiECSFlavor` que tem `id` e `name` opcionais.
#     *   O `project_id` e `region_id` são adicionados ao objeto `HuaweiECSServerData` final.
# *   Na função `get_huawei_vpc_security_groups`:
#     *   Corrigido o acesso a `sg_native.project_id` e `rule_native.description` usando `getattr` ou verificando existência.
#     *   O `project_id` coletado da API é mapeado para `project_id_from_collector` no schema Pydantic.
#     *   O `region_id` da chamada é adicionado ao objeto `HuaweiVPCSecurityGroup`.
#
# Estes testes cobrem cenários básicos e de erro para os coletores ECS e VPC SG.
# Fim do arquivo, garantindo que não há comentários de markdown.
