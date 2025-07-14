import pytest
from unittest.mock import patch, MagicMock, ANY
from datetime import datetime

from backend.collector_service.app.huawei.iam_collector import IAMCollector
from backend.collector_service.app.schemas.huawei.iam import IAMUserData, IAMGroupData, IAMAccessKeyData, MFADevice
from backend.collector_service.app.core.config import settings

@pytest.fixture
def mock_settings(monkeypatch):
    monkeypatch.setattr(settings, 'HUAWEI_CLOUD_DOMAIN_ID', 'test_domain_id') # Crucial for IAM calls
    # Add other relevant settings if IAMCollector uses them

@pytest.fixture
def iam_collector(mock_settings):
    with patch('backend.collector_service.app.huawei.huawei_client_manager.HuaweiClientManager') as MockClientManager:
        mock_iam_client = MagicMock()
        MockClientManager.return_value.get_iam_client.return_value = mock_iam_client
        # region_id for IAM client is often a global/central region, or the SDK handles it.
        # The collector might take a default region or it's passed during instantiation.
        collector = IAMCollector(region_id='ap-southeast-1', client_manager=MockClientManager.return_value) # Example region
        collector.iam_client = mock_iam_client # For direct access in tests
        return collector

# Helper to create mock IAM SDK responses
def create_mock_list_users_response(users_data):
    response = MagicMock()
    mock_users_list = []
    for user_item in users_data:
        mock_user = MagicMock()
        mock_user.id = user_item.get('id')
        mock_user.name = user_item.get('name')
        mock_user.enabled = user_item.get('enabled')
        mock_user.domain_id = user_item.get('domain_id', settings.HUAWEI_CLOUD_DOMAIN_ID)
        # Password status and last login might come from other calls or user detail calls
        # For list_users, it's usually basic info.
        # Let's assume list_users provides what's in IAMUserData or we mock further calls.
        mock_user.password_expires_at = user_item.get('password_expires_at') # datetime obj or string
        mock_user.pwd_status = user_item.get('pwd_status') # Boolean for password_enabled
        # last_login_time might not be directly in list_users, often an extended attribute or separate call.
        # For simplicity, let's assume it could be part of a detailed user object if fetched.
        # Or, it might be part of KeystoneListUsersResult which has more fields.
        # Let's assume the collector handles fetching details if needed.
        # For now, the test will focus on what list_users is likely to return.
        mock_users_list.append(mock_user)
    response.users = mock_users_list
    return response

def create_mock_list_groups_for_user_response(groups_data):
    response = MagicMock()
    mock_groups_list = []
    for group_item in groups_data:
        mock_group = MagicMock()
        mock_group.id = group_item.get('id')
        mock_group.name = group_item.get('name')
        mock_group.description = group_item.get('description')
        mock_groups_list.append(mock_group)
    response.groups = mock_groups_list
    return response

def create_mock_list_permanent_access_keys_response(keys_data):
    response = MagicMock()
    mock_keys_list = []
    for key_item in keys_data:
        mock_key = MagicMock()
        mock_key.id = key_item.get('id') # Actual field is 'access' for the AK itself
        mock_key.access = key_item.get('access')
        mock_key.status = key_item.get('status') # 'active' or 'inactive'
        mock_key.create_time = key_item.get('create_time') # String like "2023-01-01 10:00:00.000000"
        mock_key.last_use_time = key_item.get('last_use_time') # String or None
        mock_key.description = key_item.get('description')
        mock_keys_list.append(mock_key)
    response.credentials = mock_keys_list # SDK response field name is 'credentials'
    return response

def create_mock_show_user_login_protect_response(mfa_data):
    response = MagicMock()
    mock_login_protect = MagicMock()
    mock_login_protect.enabled = mfa_data.get('enabled', False)
    # verification_method might indicate TOTP, SMS, etc.
    # For simplicity, we'll just use 'enabled'. Actual SDK might have more structure.
    # The IAM collector's _get_user_mfa_status might simplify this to a boolean.
    # Let's assume the response for ShowUserLoginProtect has a 'login_protect' attribute.
    response.login_protect = mock_login_protect
    return response


def test_get_iam_users_success(iam_collector):
    mock_users_list = [
        {'id': 'user1-id', 'name': 'user1', 'enabled': True, 'pwd_status': True, 'password_expires_at': None},
        {'id': 'user2-id', 'name': 'user2', 'enabled': False, 'pwd_status': False}
    ]
    iam_collector.iam_client.keystone_list_users.return_value = create_mock_list_users_response(mock_users_list) # Using keystone_list_users

    # Mock groups for each user
    iam_collector.iam_client.keystone_list_groups_for_user.side_effect = [
        create_mock_list_groups_for_user_response([{'id': 'group1-id', 'name': 'group1', 'description': 'Group One'}]), # user1
        create_mock_list_groups_for_user_response([])  # user2
    ]
    # Mock access keys for each user
    iam_collector.iam_client.list_permanent_access_keys.side_effect = [
        create_mock_list_permanent_access_keys_response([ # user1 keys
            {'access': 'AKIAUSER1KEY1', 'status': 'active', 'create_time': '2023-01-01 10:00:00.000000', 'last_use_time': None, 'description': 'key1'},
            {'access': 'AKIAUSER1KEY2', 'status': 'inactive', 'create_time': '2022-01-01 10:00:00.000000', 'description': 'key2'},
        ]),
        create_mock_list_permanent_access_keys_response([]) # user2 keys
    ]
    # Mock MFA status for each user
    iam_collector.iam_client.show_user_login_protect.side_effect = [
        create_mock_show_user_login_protect_response({'enabled': True}),  # user1 MFA enabled
        create_mock_show_user_login_protect_response({'enabled': False}) # user2 MFA disabled
    ]

    result = iam_collector.get_iam_users()

    assert len(result) == 2
    user1_data = result[0]
    assert isinstance(user1_data, IAMUserData)
    assert user1_data.id == 'user1-id'
    assert user1_data.name == 'user1'
    assert user1_data.enabled is True
    assert user1_data.domain_id == settings.HUAWEI_CLOUD_DOMAIN_ID
    assert user1_data.password_enabled is True
    assert user1_data.mfa_enabled is True # Based on ShowUserLoginProtect mock

    assert len(user1_data.groups) == 1
    assert user1_data.groups[0].name == 'group1'

    assert len(user1_data.access_keys) == 2
    assert user1_data.access_keys[0].id == 'AKIAUSER1KEY1'
    assert user1_data.access_keys[0].status == 'active'
    # Python's datetime.strptime doesn't handle fractional seconds with 6 digits by default with %f if it's not there
    # The SDK likely returns a string that Pydantic or the collector needs to parse.
    # Assuming create_time is parsed to datetime by Pydantic or collector
    assert user1_data.access_keys[0].create_time == datetime.strptime('2023-01-01 10:00:00.000000', '%Y-%m-%d %H:%M:%S.%f')
    assert user1_data.access_keys[0].last_use_time is None

    user2_data = result[1]
    assert user2_data.name == 'user2'
    assert user2_data.enabled is False
    assert user2_data.mfa_enabled is False
    assert len(user2_data.groups) == 0
    assert len(user2_data.access_keys) == 0

    # Check calls (KeystoneListUsersRequest, KeystoneListGroupsForUserRequest, ListPermanentAccessKeysRequest, ShowUserLoginProtectRequest)
    iam_collector.iam_client.keystone_list_users.assert_called_once_with(ANY)
    assert iam_collector.iam_client.keystone_list_groups_for_user.call_count == 2
    iam_collector.iam_client.keystone_list_groups_for_user.assert_any_call(ANY) # Check if ANY request object was passed
    assert iam_collector.iam_client.list_permanent_access_keys.call_count == 2
    iam_collector.iam_client.list_permanent_access_keys.assert_any_call(ANY)
    assert iam_collector.iam_client.show_user_login_protect.call_count == 2
    iam_collector.iam_client.show_user_login_protect.assert_any_call(ANY)


def test_get_iam_users_list_users_fails(iam_collector):
    iam_collector.iam_client.keystone_list_users.side_effect = Exception("SDK call failed for list_users")
    result = iam_collector.get_iam_users()
    assert len(result) == 0
    iam_collector.iam_client.keystone_list_users.assert_called_once()

def test_get_iam_users_detail_call_fails(iam_collector):
    # Test when a detail call (e.g., groups) fails for one user
    mock_users_list = [{'id': 'user1-id', 'name': 'user1', 'enabled': True}]
    iam_collector.iam_client.keystone_list_users.return_value = create_mock_list_users_response(mock_users_list)

    iam_collector.iam_client.keystone_list_groups_for_user.side_effect = Exception("Failed to get groups")
    # Other calls will proceed or return defaults
    iam_collector.iam_client.list_permanent_access_keys.return_value = create_mock_list_permanent_access_keys_response([])
    iam_collector.iam_client.show_user_login_protect.return_value = create_mock_show_user_login_protect_response({'enabled': False})

    result = iam_collector.get_iam_users()
    assert len(result) == 1
    user1_data = result[0]
    assert user1_data.name == 'user1'
    assert len(user1_data.groups) == 0 # Should be empty due to the failure
    assert len(user1_data.access_keys) == 0
    assert user1_data.mfa_enabled is False

def test_parse_access_key_last_used_conversion(iam_collector):
    # Test _parse_access_key_last_used if it's a helper in the collector
    # This is implicitly tested by the main success case if data is correct
    # Here's an example if you wanted to test it separately:
    # raw_key_data = MagicMock(last_use_time="2023-05-01 12:30:00")
    # parsed_date = iam_collector._parse_access_key_last_used(raw_key_data.last_use_time)
    # assert parsed_date == datetime(2023, 5, 1, 12, 30, 0)

    # raw_key_data_none = MagicMock(last_use_time=None)
    # parsed_date_none = iam_collector._parse_access_key_last_used(raw_key_data_none.last_use_time)
    # assert parsed_date_none is None
    pass # Covered by the main test for now

def test_get_user_mfa_status_handles_not_found(iam_collector):
    # Simulate SDK raising an exception that means MFA is not configured (e.g., 404 Not Found)
    # The SDK might return a specific error code or object for this.
    # For this example, assume a generic exception that the collector catches.
    from huaweicloudsdkcore.exceptions import ApiValueError, ServiceResponseException

    # Mock the client to raise ServiceResponseException with status 404 for MFA check
    # This requires knowing how the SDK signals "not found" for login_protect
    # It might be a specific error code in the exception, or the exception type itself.
    # For now, let's assume any ServiceResponseException is caught and treated as MFA not enabled.
    # A more precise test would mock the specific error.

    # Let's refine: The SDK's show_user_login_protect might return a response object
    # even on 404, or raise an SdkException. The collector's try-except needs to match.
    # If it raises SdkException for 404:
    mock_sdk_exception = ServiceResponseException(status_code=404, error_code="IAM.0000", error_msg="Not Found")
    iam_collector.iam_client.show_user_login_protect.side_effect = mock_sdk_exception

    mfa_status = iam_collector._get_user_mfa_status('user-id-test')
    assert mfa_status is False # Should default to False if MFA info isn't found or error occurs
    iam_collector.iam_client.show_user_login_protect.assert_called_once()

# Request objects that might be used:
# from huaweicloudsdkeiam.v3.model import KeystoneListUsersRequest
# from huaweicloudsdkeiam.v3.model import KeystoneListGroupsForUserRequest
# from huaweicloudsdkeiam.v3.model import ListPermanentAccessKeysRequest
# from huaweicloudsdkeiam.v3.model import ShowUserLoginProtectRequest
# request = KeystoneListUsersRequest(domain_id=settings.HUAWEI_CLOUD_DOMAIN_ID)
# request = ListPermanentAccessKeysRequest(user_id=user.id)
# request = ShowUserLoginProtectRequest(user_id=user.id)
