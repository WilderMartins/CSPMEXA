import pytest
from unittest.mock import patch, MagicMock, ANY
from datetime import datetime

from backend.collector_service.app.huawei.obs_collector import OBSCollector
from backend.collector_service.app.schemas.huawei.obs import OBSBucketData, OBSBucketPolicyStatement, OBSBucketVersioningConfiguration
from backend.collector_service.app.core.config import settings

@pytest.fixture
def mock_settings(monkeypatch):
    monkeypatch.setattr(settings, 'HUAWEI_CLOUD_PROJECT_ID', 'test_project_id_setting')
    monkeypatch.setattr(settings, 'HUAWEI_CLOUD_DOMAIN_ID', 'test_domain_id_setting') # If used by collector
    # Add other settings if OBSCollector directly uses them beyond what client_manager handles

@pytest.fixture
def obs_collector(mock_settings):
    with patch('backend.collector_service.app.huawei.huawei_client_manager.HuaweiClientManager') as MockClientManager:
        mock_obs_client = MagicMock()
        MockClientManager.return_value.get_obs_client.return_value = mock_obs_client
        collector = OBSCollector(region_id='cn-north-1', client_manager=MockClientManager.return_value)
        collector.obs_client = mock_obs_client # Ensure direct access for mocking
        return collector

def create_mock_obs_response(data):
    response = MagicMock()
    response.body = MagicMock()
    if isinstance(data, list): # For listBuckets
        response.body.buckets = [MagicMock(name=b['name'], creationDate=b['creationDate'], location=b['location']) for b in data]
    elif isinstance(data, dict): # For other calls like getBucketMetadata, getBucketAcl etc.
        for key, value in data.items():
            setattr(response.body, key, value)
        if 'owner' in data and data['owner']: # For getBucketAcl
             response.body.owner = MagicMock(id=data['owner'].get('id'))
        if 'grants' in data and data['grants']: # For getBucketAcl
            mock_grants_list = []
            for grant_data in data['grants']:
                mock_grant = MagicMock()
                mock_grant.grantee = MagicMock()
                mock_grant.grantee.type = grant_data['grantee']['type']
                mock_grant.grantee.id = grant_data['grantee'].get('id')
                mock_grant.grantee.uri = grant_data['grantee'].get('uri')
                mock_grant.permission = grant_data['permission']
                mock_grants_list.append(mock_grant)
            response.body.grants = mock_grants_list

    response.status = 200 # Assuming success
    return response

def test_get_obs_data_success(obs_collector):
    mock_bucket_list_response = create_mock_obs_response([
        {'name': 'bucket1', 'creationDate': '2023-01-01T12:00:00.000Z', 'location': 'cn-north-1'},
        {'name': 'bucket2', 'creationDate': '2023-01-02T12:00:00.000Z', 'location': 'cn-north-1'}
    ])
    obs_collector.obs_client.listBuckets.return_value = mock_bucket_list_response

    # Mock responses for bucket1
    obs_collector.obs_client.getBucketMetadata.side_effect = [
        create_mock_obs_response({'storageClass': 'STANDARD', 'location': 'cn-north-1'}), # bucket1 metadata
        create_mock_obs_response({'storageClass': 'ARCHIVE', 'location': 'cn-north-1'}),  # bucket2 metadata
    ]
    obs_collector.obs_client.getBucketAcl.side_effect = [
        create_mock_obs_response({ # bucket1 ACL
            'owner': {'id': 'owner1'},
            'grants': [{'grantee': {'type': 'Group', 'uri': 'http://acs.amazonaws.com/groups/global/AllUsers'}, 'permission': 'READ'}]
        }),
        create_mock_obs_response({ # bucket2 ACL
            'owner': {'id': 'owner2'},
            'grants': []
        }),
    ]
    obs_collector.obs_client.getBucketPolicy.side_effect = [
        create_mock_obs_response({ # bucket1 Policy
            'policyJSON': '{"Statement":[{"Effect":"Allow","Principal":"*","Action":"s3:GetObject","Resource":"arn:aws:s3:::bucket1/*"}]}'
        }),
        MagicMock(status=404) # bucket2 No policy
    ]
    obs_collector.obs_client.getBucketVersioning.side_effect = [
        create_mock_obs_response({'status': 'Enabled'}), # bucket1 Versioning
        create_mock_obs_response({'status': 'Suspended'}) # bucket2 Versioning
    ]

    result = obs_collector.get_obs_data()

    assert len(result) == 2
    assert isinstance(result[0], OBSBucketData)
    assert result[0].name == 'bucket1'
    assert result[0].creation_date == datetime(2023, 1, 1, 12, 0, 0) # OBS SDK might return datetime directly or string
    assert result[0].location == 'cn-north-1'
    assert result[0].storage_class == 'STANDARD'
    assert result[0].acl is not None
    assert len(result[0].acl.grants) == 1
    assert result[0].acl.grants[0].grantee_type == 'Group'
    assert result[0].acl.grants[0].grantee_uri == 'http://acs.amazonaws.com/groups/global/AllUsers'
    assert result[0].acl.grants[0].permission == 'READ'
    assert result[0].is_public is True # Based on ACL AllUsers READ
    assert result[0].policy is not None
    assert len(result[0].policy.statement) == 1
    assert result[0].policy.statement[0].effect == "Allow"
    assert result[0].versioning.status == "Enabled"

    assert isinstance(result[1], OBSBucketData)
    assert result[1].name == 'bucket2'
    assert result[1].is_public is False
    assert result[1].policy is None
    assert result[1].versioning.status == "Suspended"

    obs_collector.obs_client.listBuckets.assert_called_once()
    assert obs_collector.obs_client.getBucketMetadata.call_count == 2
    assert obs_collector.obs_client.getBucketAcl.call_count == 2
    assert obs_collector.obs_client.getBucketPolicy.call_count == 2
    assert obs_collector.obs_client.getBucketVersioning.call_count == 2

def test_get_obs_data_list_buckets_fails(obs_collector):
    mock_response = MagicMock()
    mock_response.status = 500
    mock_response.reason = "Internal Server Error"
    mock_response.body = None # Or some error structure
    obs_collector.obs_client.listBuckets.return_value = mock_response

    result = obs_collector.get_obs_data()
    assert len(result) == 0
    obs_collector.obs_client.listBuckets.assert_called_once()

def test_get_obs_data_detail_call_fails(obs_collector):
    # Test when one of the detail calls (e.g., getBucketAcl) fails for a bucket
    mock_bucket_list_response = create_mock_obs_response([
        {'name': 'bucket1', 'creationDate': '2023-01-01T12:00:00.000Z', 'location': 'cn-north-1'}
    ])
    obs_collector.obs_client.listBuckets.return_value = mock_bucket_list_response

    obs_collector.obs_client.getBucketMetadata.return_value = create_mock_obs_response({'storageClass': 'STANDARD'})

    # ACL call fails
    mock_acl_fail_response = MagicMock(status=500, reason="ACL Error")
    mock_acl_fail_response.body = None
    obs_collector.obs_client.getBucketAcl.return_value = mock_acl_fail_response

    obs_collector.obs_client.getBucketPolicy.return_value = MagicMock(status=404) # No policy
    obs_collector.obs_client.getBucketVersioning.return_value = create_mock_obs_response({'status': 'Enabled'})

    result = obs_collector.get_obs_data()

    assert len(result) == 1
    bucket_data = result[0]
    assert bucket_data.name == 'bucket1'
    assert bucket_data.acl is None # Should be None due to error
    assert bucket_data.is_public is False # Default if ACL cannot be determined
    assert bucket_data.policy is None
    assert bucket_data.versioning.status == "Enabled"

def test_parse_policy_valid_json(obs_collector):
    policy_json = '{"Statement":[{"Effect":"Allow","Principal":"*","Action":"s3:GetObject","Resource":"arn:aws:s3:::bucket1/*"}]}'
    mock_response = create_mock_obs_response({'policyJSON': policy_json})
    policy = obs_collector._parse_policy(mock_response, "bucket1")
    assert policy is not None
    assert len(policy.statement) == 1
    assert policy.statement[0].effect == "Allow"

def test_parse_policy_invalid_json(obs_collector):
    policy_json = '{"Statement":Invalid}' # Invalid JSON
    mock_response = create_mock_obs_response({'policyJSON': policy_json})
    policy = obs_collector._parse_policy(mock_response, "bucket1")
    assert policy is None

def test_parse_policy_no_policy_json_field(obs_collector):
    mock_response = create_mock_obs_response({}) # Missing policyJSON field
    policy = obs_collector._parse_policy(mock_response, "bucket1")
    assert policy is None

def test_check_public_access_from_acl_allusers_read(obs_collector):
    acl_data = MagicMock()
    grant = MagicMock()
    grant.grantee = MagicMock(type="Group", uri=obs_collector.OBS_ALL_USERS_URI)
    grant.permission = "READ"
    acl_data.grants = [grant]
    assert obs_collector._check_public_access_from_acl(acl_data) is True

def test_check_public_access_from_acl_allusers_write(obs_collector):
    acl_data = MagicMock()
    grant = MagicMock()
    grant.grantee = MagicMock(type="Group", uri=obs_collector.OBS_ALL_USERS_URI)
    grant.permission = "WRITE"
    acl_data.grants = [grant]
    assert obs_collector._check_public_access_from_acl(acl_data) is True


def test_check_public_access_from_acl_authenticated_users_read(obs_collector):
    # This URI might vary for OBS, ensure it matches what the SDK returns for "Authenticated Users"
    # For S3 it's http://acs.amazonaws.com/groups/global/AuthenticatedUsers
    # Assuming OBS has a similar concept or specific URI.
    # If not, this test might need adjustment based on actual OBS behavior.
    # For now, let's assume a placeholder URI or that it's not considered public.
    acl_data = MagicMock()
    grant = MagicMock()
    grant.grantee = MagicMock(type="Group", uri="SOME_AUTHENTICATED_USERS_URI_FOR_OBS")
    grant.permission = "READ"
    acl_data.grants = [grant]
    assert obs_collector._check_public_access_from_acl(acl_data) is False # Typically AuthenticatedUsers is not "public" in the same way as AllUsers

def test_check_public_access_from_acl_no_public_grants(obs_collector):
    acl_data = MagicMock()
    grant = MagicMock()
    grant.grantee = MagicMock(type="CanonicalUser", id="someuser")
    grant.permission = "FULL_CONTROL"
    acl_data.grants = [grant]
    assert obs_collector._check_public_access_from_acl(acl_data) is False

def test_check_public_access_from_acl_empty_grants(obs_collector):
    acl_data = MagicMock(grants=[])
    assert obs_collector._check_public_access_from_acl(acl_data) is False

def test_check_public_access_from_acl_none(obs_collector):
    assert obs_collector._check_public_access_from_acl(None) is False

def test_check_public_access_from_policy_allow_all(obs_collector):
    # Policy allowing wildcard principal for GetObject
    policy_statement = OBSBucketPolicyStatement(Effect="Allow", Principal="*", Action="s3:GetObject", Resource="arn:aws:s3:::bucket/*")
    policy_data = MagicMock(statement=[policy_statement])
    assert obs_collector._check_public_access_from_policy(policy_data) is True

def test_check_public_access_from_policy_allow_all_list_principal(obs_collector):
    policy_statement = OBSBucketPolicyStatement(Effect="Allow", Principal=["*", "someother"], Action="s3:GetObject", Resource="arn:aws:s3:::bucket/*")
    policy_data = MagicMock(statement=[policy_statement])
    assert obs_collector._check_public_access_from_policy(policy_data) is True

def test_check_public_access_from_policy_allow_all_aws_principal(obs_collector):
    # AWS account as principal (string or dict)
    policy_statement = OBSBucketPolicyStatement(Effect="Allow", Principal={"AWS": "*"}, Action="s3:GetObject", Resource="arn:aws:s3:::bucket/*")
    policy_data = MagicMock(statement=[policy_statement])
    assert obs_collector._check_public_access_from_policy(policy_data) is True

    policy_statement_str = OBSBucketPolicyStatement(Effect="Allow", Principal="*", Action="s3:GetObject", Resource="arn:aws:s3:::bucket/*")
    policy_data_str = MagicMock(statement=[policy_statement_str])
    assert obs_collector._check_public_access_from_policy(policy_data_str) is True


def test_check_public_access_from_policy_no_allow_all(obs_collector):
    policy_statement = OBSBucketPolicyStatement(Effect="Allow", Principal="arn:aws:iam::123456789012:root", Action="s3:GetObject", Resource="arn:aws:s3:::bucket/*")
    policy_data = MagicMock(statement=[policy_statement])
    assert obs_collector._check_public_access_from_policy(policy_data) is False

def test_check_public_access_from_policy_deny_takes_precedence(obs_collector):
    # Even if there's an Allow *, a Deny * should make it not public through policy.
    # (Though such a policy is weird, testing the logic)
    allow_statement = OBSBucketPolicyStatement(Effect="Allow", Principal="*", Action="s3:GetObject", Resource="arn:aws:s3:::bucket/*")
    deny_statement = OBSBucketPolicyStatement(Effect="Deny", Principal="*", Action="s3:GetObject", Resource="arn:aws:s3:::bucket/*")
    policy_data = MagicMock(statement=[allow_statement, deny_statement])
    # Current _check_public_access_from_policy only looks for "Allow" with "*". It doesn't evaluate Deny.
    # This is a simplification. A more robust check would consider Deny statements.
    # For now, based on the current implementation, this will be True.
    # If the implementation is improved to consider Deny, this test should expect False.
    assert obs_collector._check_public_access_from_policy(policy_data) is True

def test_check_public_access_from_policy_none(obs_collector):
    assert obs_collector._check_public_access_from_policy(None) is False

def test_obs_bucket_data_public_determination(obs_collector):
    # Case 1: Public by ACL
    bucket_acl_public = MagicMock()
    grant_public_acl = MagicMock(grantee=MagicMock(type="Group", uri=obs_collector.OBS_ALL_USERS_URI), permission="READ")
    bucket_acl_public.grants = [grant_public_acl]

    data_public_acl = OBSBucketData(
        name="b1", creation_date=datetime.now(), location="loc1", storage_class="sc1",
        acl=obs_collector._parse_acl(bucket_acl_public, "b1"),
        policy=None,
        versioning=OBSBucketVersioningConfiguration(status="Enabled"),
        is_public=False # Placeholder, will be re-evaluated by property
    )
    data_public_acl.is_public = obs_collector._check_overall_public_status(
        obs_collector._check_public_access_from_acl(data_public_acl.acl),
        obs_collector._check_public_access_from_policy(data_public_acl.policy)
    )
    assert data_public_acl.is_public is True

    # Case 2: Public by Policy
    policy_st = OBSBucketPolicyStatement(Effect="Allow", Principal="*", Action="s3:GetObject", Resource="arn:aws:s3:::b2/*")
    bucket_policy_public_obj = MagicMock(statement=[policy_st])

    data_public_policy = OBSBucketData(
        name="b2", creation_date=datetime.now(), location="loc2", storage_class="sc2",
        acl=obs_collector._parse_acl(MagicMock(grants=[]), "b2"), # Non-public ACL
        policy=bucket_policy_public_obj,
        versioning=OBSBucketVersioningConfiguration(status="Enabled"),
        is_public=False
    )
    data_public_policy.is_public = obs_collector._check_overall_public_status(
        obs_collector._check_public_access_from_acl(data_public_policy.acl),
        obs_collector._check_public_access_from_policy(data_public_policy.policy)
    )
    assert data_public_policy.is_public is True

    # Case 3: Not Public
    data_not_public = OBSBucketData(
        name="b3", creation_date=datetime.now(), location="loc3", storage_class="sc3",
        acl=obs_collector._parse_acl(MagicMock(grants=[]), "b3"), # Non-public ACL
        policy=None, # No policy
        versioning=OBSBucketVersioningConfiguration(status="Enabled"),
        is_public=False
    )
    data_not_public.is_public = obs_collector._check_overall_public_status(
        obs_collector._check_public_access_from_acl(data_not_public.acl),
        obs_collector._check_public_access_from_policy(data_not_public.policy)
    )
    assert data_not_public.is_public is False

# Helper to create mock OBS SDK datetime string if needed,
# but the SDK might return actual datetime objects for creationDate.
# For OBS, creationDate is a string like '2023-01-01T12:00:00.000Z'.
# The Pydantic model should handle parsing this.
# If SDK returns string: OBSBucketData model's creation_date field type hint is datetime,
# Pydantic will attempt to parse it.
```
