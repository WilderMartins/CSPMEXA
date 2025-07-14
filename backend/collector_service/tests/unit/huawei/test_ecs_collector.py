import pytest
from unittest.mock import patch, MagicMock, ANY
from datetime import datetime

from backend.collector_service.app.huawei.ecs_collector import ECSCollector
from backend.collector_service.app.schemas.huawei.ecs import ECSVMData, ECSAddresses, ECSNetworkInterface, ECSSecurityGroup
from backend.collector_service.app.core.config import settings

@pytest.fixture
def mock_settings(monkeypatch):
    monkeypatch.setattr(settings, 'HUAWEI_CLOUD_PROJECT_ID', 'test_project_id_setting')
    # Add other relevant settings if ECSCollector uses them

@pytest.fixture
def ecs_collector(mock_settings):
    with patch('backend.collector_service.app.huawei.huawei_client_manager.HuaweiClientManager') as MockClientManager:
        mock_ecs_client = MagicMock()
        MockClientManager.return_value.get_ecs_client.return_value = mock_ecs_client
        # Mock get_vpc_client as well if it's used within ECSCollector for SG details, etc.
        # mock_vpc_client = MagicMock()
        # MockClientManager.return_value.get_vpc_client.return_value = mock_vpc_client
        collector = ECSCollector(region_id='cn-north-1', client_manager=MockClientManager.return_value)
        collector.ecs_client = mock_ecs_client # For direct access in tests
        # collector.vpc_client = mock_vpc_client # If used
        return collector

# Helper to create mock server list response from ECS SDK
def create_mock_list_servers_response(servers_data):
    response = MagicMock()
    mock_servers = []
    for server_item in servers_data:
        mock_server = MagicMock()
        mock_server.id = server_item.get('id')
        mock_server.name = server_item.get('name')
        mock_server.status = server_item.get('status')
        mock_server.created = server_item.get('created') # datetime string e.g., "2023-01-01T12:00:00.000000Z"
        mock_server.updated = server_item.get('updated') # datetime string

        # Flavor
        mock_server.flavor = MagicMock(id=server_item.get('flavor', {}).get('id'), name=server_item.get('flavor', {}).get('name'))

        # Image
        mock_server.image = MagicMock(id=server_item.get('image', {}).get('id')) # Image might be just an ID or an object

        # Key Pair
        mock_server.key_name = server_item.get('key_name')

        # Availability Zone
        mock_server.availability_zone = server_item.get('OS-EXT-AZ:availability_zone') # Note the actual attribute name from SDK

        # Metadata
        mock_server.metadata = server_item.get('metadata', {})

        # Addresses (Simplified: assuming one network with one public and one private IP)
        # The actual structure can be complex: Dict[str, List[ServerAddress]]
        # ServerAddress has addr, version, type, mac_addr
        mock_addresses = {}
        for net_name, ips_data in server_item.get('addresses', {}).items():
            addr_list = []
            for ip_data in ips_data:
                addr_list.append(MagicMock(
                    addr=ip_data.get('addr'),
                    version=ip_data.get('version'),
                    type=ip_data.get('OS-EXT-IPS:type'), # e.g., 'fixed', 'floating'
                    mac_addr=ip_data.get('OS-EXT-IPS-MAC:mac_addr')
                ))
            mock_addresses[net_name] = addr_list
        mock_server.addresses = mock_addresses

        # Security Groups (list of dicts with 'name')
        mock_sgs = []
        for sg_item in server_item.get('security_groups', []):
            mock_sgs.append(MagicMock(name=sg_item.get('name'), id=sg_item.get('id'))) # Assuming id is also available
        mock_server.security_groups = mock_sgs

        mock_servers.append(mock_server)

    response.servers = mock_servers
    response.count = len(mock_servers) # If the SDK response includes a count
    return response

def test_get_ecs_vms_success(ecs_collector):
    mock_servers_data = [
        {
            'id': 'vm1-id', 'name': 'vm1-name', 'status': 'ACTIVE',
            'created': '2023-01-01T10:00:00Z', 'updated': '2023-01-01T11:00:00Z',
            'flavor': {'id': 'flavor1-id', 'name': 's1.small'},
            'image': {'id': 'image1-id'},
            'key_name': 'keypair1',
            'OS-EXT-AZ:availability_zone': 'cn-north-1a',
            'metadata': {'owner': 'team-a'},
            'addresses': {
                'private_net': [
                    {'addr': '192.168.1.10', 'version': 4, 'OS-EXT-IPS:type': 'fixed', 'OS-EXT-IPS-MAC:mac_addr': 'fa:16:3e:xx:xx:xx'}
                ],
                'public_net': [ # Assuming a floating IP might be structured this way or attached differently
                    {'addr': '1.2.3.4', 'version': 4, 'OS-EXT-IPS:type': 'floating', 'OS-EXT-IPS-MAC:mac_addr': 'fa:16:3e:yy:yy:yy'}
                ]
            },
            'security_groups': [{'name': 'sg-default', 'id': 'sg1-id'}, {'name': 'sg-web', 'id': 'sg2-id'}]
        },
        {
            'id': 'vm2-id', 'name': 'vm2-name', 'status': 'SHUTOFF',
            'created': '2023-02-01T10:00:00Z', 'updated': '2023-02-01T11:00:00Z',
            'flavor': {'id': 'flavor2-id', 'name': 'c1.medium'},
            'image': {'id': 'image2-id'}, 'key_name': None,
            'OS-EXT-AZ:availability_zone': 'cn-north-1b',
            'metadata': {},
            'addresses': {
                 'private_net_2': [
                    {'addr': '10.0.0.5', 'version': 4, 'OS-EXT-IPS:type': 'fixed', 'OS-EXT-IPS-MAC:mac_addr': 'fa:16:3e:zz:zz:zz'}
                ]
            },
            'security_groups': [{'name': 'sg-default', 'id': 'sg1-id'}]
        }
    ]
    mock_response = create_mock_list_servers_response(mock_servers_data)
    ecs_collector.ecs_client.list_servers_details.return_value = mock_response # Changed from list_servers to list_servers_details

    result = ecs_collector.get_ecs_vms()

    assert len(result) == 2
    vm1_data = result[0]
    assert isinstance(vm1_data, ECSVMData)
    assert vm1_data.id == 'vm1-id'
    assert vm1_data.name == 'vm1-name'
    assert vm1_data.status == 'ACTIVE'
    assert vm1_data.created_at == datetime(2023, 1, 1, 10, 0, 0) # Pydantic should parse 'Z' to UTC
    assert vm1_data.updated_at == datetime(2023, 1, 1, 11, 0, 0)
    assert vm1_data.flavor_id == 'flavor1-id'
    assert vm1_data.flavor_name == 's1.small'
    assert vm1_data.image_id == 'image1-id'
    assert vm1_data.key_pair_name == 'keypair1'
    assert vm1_data.availability_zone == 'cn-north-1a'
    assert vm1_data.metadata == {'owner': 'team-a'}

    # Asserting addresses (structure depends on _parse_addresses helper)
    assert len(vm1_data.addresses) > 0
    assert any(addr.ip_address == '192.168.1.10' and addr.type == 'fixed' for net_addrs in vm1_data.addresses.values() for addr in net_addrs)
    assert any(addr.ip_address == '1.2.3.4' and addr.type == 'floating' for net_addrs in vm1_data.addresses.values() for addr in net_addrs)
    assert vm1_data.public_ip is not None # Should be set by the logic in ECSVMData or collector
    assert '1.2.3.4' in vm1_data.public_ip # Assuming public_ip becomes a list of strings
    assert '192.168.1.10' in vm1_data.private_ips

    assert len(vm1_data.security_groups) == 2
    assert vm1_data.security_groups[0].name == 'sg-default'
    assert vm1_data.security_groups[0].id == 'sg1-id'
    assert vm1_data.security_groups[1].name == 'sg-web'
    assert vm1_data.security_groups[1].id == 'sg2-id'

    vm2_data = result[1]
    assert vm2_data.name == 'vm2-name'
    assert vm2_data.public_ip == [] # No floating IP
    assert '10.0.0.5' in vm2_data.private_ips
    assert len(vm2_data.security_groups) == 1

    # Ensure the SDK method was called correctly
    # The actual method might be list_servers_details for more info.
    # The request might take a ShowServerRequest object or parameters directly.
    # For now, assume a simple call.
    ecs_collector.ecs_client.list_servers_details.assert_called_once_with(ANY) # ANY for ListServersRequest object

def test_get_ecs_vms_api_call_fails(ecs_collector):
    # Simulate an SDK exception or error response
    ecs_collector.ecs_client.list_servers_details.side_effect = Exception("SDK call failed")
    # Or mock a response with an error status if SDK returns that way
    # mock_error_response = MagicMock(status=500, reason="Server Error")
    # ecs_collector.ecs_client.list_servers_details.return_value = mock_error_response

    result = ecs_collector.get_ecs_vms()
    assert len(result) == 0
    ecs_collector.ecs_client.list_servers_details.assert_called_once()


def test_get_ecs_vms_no_servers_returned(ecs_collector):
    mock_response = create_mock_list_servers_response([]) # Empty list of servers
    ecs_collector.ecs_client.list_servers_details.return_value = mock_response

    result = ecs_collector.get_ecs_vms()
    assert len(result) == 0
    ecs_collector.ecs_client.list_servers_details.assert_called_once()

def test_parse_addresses_logic(ecs_collector):
    # Test the internal _parse_addresses method if it's complex
    # This is implicitly tested by test_get_ecs_vms_success
    # but can be tested in isolation if needed.
    raw_addresses_data = {
        'private_net': [
            {'addr': '192.168.1.10', 'version': 4, 'OS-EXT-IPS:type': 'fixed', 'OS-EXT-IPS-MAC:mac_addr': 'fa:16:3e:xx:xx:xx'}
        ],
        'another_private': [
             {'addr': '10.10.0.5', 'version': 4, 'OS-EXT-IPS:type': 'fixed', 'OS-EXT-IPS-MAC:mac_addr': 'fa:16:3e:aa:bb:cc'}
        ],
        'public_eip_net': [
            {'addr': '1.2.3.4', 'version': 4, 'OS-EXT-IPS:type': 'floating', 'OS-EXT-IPS-MAC:mac_addr': 'fa:16:3e:yy:yy:yy'}
        ]
    }
    parsed_addrs, public_ips, private_ips = ecs_collector._parse_addresses(raw_addresses_data)

    assert len(parsed_addrs) == 3 # Number of networks
    assert 'private_net' in parsed_addrs
    assert len(parsed_addrs['private_net']) == 1
    assert parsed_addrs['private_net'][0].ip_address == '192.168.1.10'
    assert parsed_addrs['private_net'][0].type == 'fixed'

    assert '1.2.3.4' in public_ips
    assert '192.168.1.10' in private_ips
    assert '10.10.0.5' in private_ips

def test_parse_addresses_no_public_ip(ecs_collector):
    raw_addresses_data = {
        'private_net': [
            {'addr': '192.168.1.10', 'version': 4, 'OS-EXT-IPS:type': 'fixed', 'OS-EXT-IPS-MAC:mac_addr': 'fa:16:3e:xx:xx:xx'}
        ]
    }
    _, public_ips, private_ips = ecs_collector._parse_addresses(raw_addresses_data)
    assert len(public_ips) == 0
    assert '192.168.1.10' in private_ips

def test_parse_addresses_empty(ecs_collector):
    raw_addresses_data = {}
    parsed_addrs, public_ips, private_ips = ecs_collector._parse_addresses(raw_addresses_data)
    assert len(parsed_addrs) == 0
    assert len(public_ips) == 0
    assert len(private_ips) == 0

# Example of how a ShowServerRequest might be constructed for list_servers_details
# from huaweicloudsdkecs.v2.model import ListServersDetailsRequest
# request = ListServersDetailsRequest()
# # Set other parameters on request if needed, e.g., limit, offset, name filter
# ecs_collector.ecs_client.list_servers_details(request)
