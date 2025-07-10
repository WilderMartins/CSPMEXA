import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timezone
import json
import inspect

from app.aws import s3_collector
from app.schemas.s3 import (
    S3BucketData, S3BucketACLDetails, S3BucketACLGrant, S3BucketACLGrantee,
    S3BucketVersioning, S3BucketPublicAccessBlock, S3BucketLogging
)
from app.core.config import Settings
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
from fastapi import HTTPException

@pytest.fixture(autouse=True)
def manage_s3_collector_settings_and_cache():
    original_settings = s3_collector.settings
    original_cache = s3_collector.s3_clients_cache.copy()
    s3_collector.settings = Settings(AWS_REGION_NAME="us-east-1")
    s3_collector.s3_clients_cache.clear()
    yield
    s3_collector.settings = original_settings
    s3_collector.s3_clients_cache = original_cache
    s3_collector.s3_clients_cache.update(s3_collector.s3_clients_cache)

def test_parse_acl_no_grants():
    acl_response = {"Owner": {"DisplayName": "owner_display", "ID": "owner_id"}, "Grants": []}
    result = s3_collector.parse_acl(acl_response, "test-bucket")
    assert result.owner_display_name == "owner_display"
    assert result.owner_id == "owner_id"
    assert result.grants == []
    assert not result.is_public
    assert result.public_details == []

def test_parse_acl_public_all_users_read():
    acl_response = {
        "Owner": {"ID": "owner_id"},
        "Grants": [{"Grantee": {"Type": "Group", "URI": "http://acs.amazonaws.com/groups/global/AllUsers"}, "Permission": "READ"}]
    }
    result = s3_collector.parse_acl(acl_response, "test-bucket")
    assert result.is_public
    assert "Public (AllUsers) with permission: READ" in result.public_details

def test_check_policy_not_public_empty_policy():
    assert not s3_collector.check_policy_for_public_access(None)

def test_check_policy_public_principal_star_allow():
    policy = {"Statement": [{"Effect": "Allow", "Principal": "*", "Action": "s3:GetObject"}]}
    assert s3_collector.check_policy_for_public_access(policy)

@patch('app.aws.s3_collector.boto3.client')
def test_get_s3_data_no_buckets(mock_boto_client):
    mock_s3_global = MagicMock()
    mock_s3_global.list_buckets.return_value = {"Buckets": []}
    def client_side_effect(service_name, region_name=None, **kwargs):
        if service_name == 's3' and (region_name == s3_collector.settings.AWS_REGION_NAME or region_name == "global"):
            return mock_s3_global
        raise ValueError(f"Unexpected client call: {service_name} with region {region_name}")
    mock_boto_client.side_effect = client_side_effect
    result = s3_collector.get_s3_data()
    assert result == []
    mock_s3_global.list_buckets.assert_called_once()

@patch('app.aws.s3_collector.boto3.client')
def test_get_s3_data_one_bucket_all_details_collected(mock_boto_client):
    bucket_name = "test-bucket-1"
    bucket_region = "us-west-2"
    creation_date = datetime.now(timezone.utc)
    mock_s3_global = MagicMock()
    mock_s3_global.list_buckets.return_value = {"Buckets": [{"Name": bucket_name, "CreationDate": creation_date}]}
    mock_s3_global.get_bucket_location.return_value = {"LocationConstraint": bucket_region}
    mock_s3_regional = MagicMock()
    mock_s3_regional.get_bucket_acl.return_value = {"Owner": {"ID": "owner"}, "Grants": []}
    policy_doc = {"Statement": [{"Effect": "Allow", "Principal": "*", "Action": "s3:GetObject"}]}
    mock_s3_regional.get_bucket_policy.return_value = {"Policy": json.dumps(policy_doc)}
    mock_s3_regional.get_bucket_versioning.return_value = {"Status": "Enabled"}
    mock_s3_regional.get_public_access_block.return_value = {"PublicAccessBlockConfiguration": {"BlockPublicAcls": True}}
    mock_s3_regional.get_bucket_logging.return_value = {"LoggingEnabled": {"TargetBucket": "log-bucket"}}
    def client_side_effect(service_name, region_name=None, **kwargs):
        if service_name == 's3':
            if region_name == s3_collector.settings.AWS_REGION_NAME or region_name == "global": return mock_s3_global
            elif region_name == bucket_region: return mock_s3_regional
        raise ValueError(f"Unexpected client call: {service_name} with region {region_name}")
    mock_boto_client.side_effect = client_side_effect
    result = s3_collector.get_s3_data()
    assert len(result) == 1
    b = result[0]
    assert b.name == bucket_name
    assert b.region == bucket_region
    assert b.creation_date == creation_date
    assert b.policy_is_public is True
    assert b.versioning.status == "Enabled"
    assert b.public_access_block.block_public_acls is True
    assert b.logging.enabled is True
    assert b.error_details is None

@patch('app.aws.s3_collector.boto3.client')
def test_get_s3_data_list_buckets_no_credentials_error(mock_boto_client):
    mock_s3_global = MagicMock()
    mock_s3_global.list_buckets.side_effect = NoCredentialsError()
    mock_boto_client.return_value = mock_s3_global
    with pytest.raises(HTTPException) as exc_info:
        s3_collector.get_s3_data()
    assert exc_info.value.status_code == 500
    assert "AWS credentials not configured" in exc_info.value.detail

@patch('app.aws.s3_collector.get_s3_client')
@patch('app.aws.s3_collector.get_bucket_specific_s3_client')
def test_get_s3_data_get_bucket_location_fails(mock_get_regional_client, mock_get_global_client):
    bucket_name = "test-loc-fail"
    creation_date = datetime.now(timezone.utc)
    default_region = s3_collector.settings.AWS_REGION_NAME
    mock_s3_global_instance = MagicMock()
    mock_get_global_client.return_value = mock_s3_global_instance
    mock_s3_default_region_instance = MagicMock()
    mock_get_regional_client.return_value = mock_s3_default_region_instance
    mock_s3_global_instance.list_buckets.return_value = {"Buckets": [{"Name": bucket_name, "CreationDate": creation_date}]}
    location_error = ClientError({'Error': {'Code': 'AccessDenied', 'Message': 'Cannot get location'}}, 'GetBucketLocation')
    mock_s3_global_instance.get_bucket_location.side_effect = location_error
    mock_s3_default_region_instance.get_bucket_acl.return_value = {"Owner": {}, "Grants": []}
    mock_s3_default_region_instance.get_bucket_policy.side_effect = ClientError({'Error': {'Code': 'NoSuchBucketPolicy'}},'GetBucketPolicy')
    mock_s3_default_region_instance.get_bucket_versioning.return_value = {}
    mock_s3_default_region_instance.get_public_access_block.side_effect = ClientError({'Error':{'Code': 'NoSuchPublicAccessBlockConfiguration'}}, 'GetPublicAccessBlock')
    mock_s3_default_region_instance.get_bucket_logging.return_value = {}
    result = s3_collector.get_s3_data()
    assert len(result) == 1
    assert result[0].name == bucket_name
    assert result[0].region == default_region
    assert "Region determination failed: Cannot get location" in result[0].error_details
    mock_get_regional_client.assert_called_with(default_region)
    mock_s3_default_region_instance.get_bucket_acl.assert_called_once()

# Adicionei mais alguns testes síncronos baseados nos que eu tinha antes.
@patch('app.aws.s3_collector.boto3.client')
def test_get_s3_data_bucket_level_client_error_for_acl(mock_boto_client):
    bucket_name = "test-bucket-errors"
    bucket_region = "eu-west-1"
    creation_date = datetime.now(timezone.utc)
    mock_s3_global = MagicMock()
    mock_s3_global.list_buckets.return_value = {"Buckets": [{"Name": bucket_name, "CreationDate": creation_date}]}
    mock_s3_global.get_bucket_location.return_value = {"LocationConstraint": bucket_region}
    mock_s3_regional = MagicMock()
    acl_error_response = {'Error': {'Code': 'AccessDenied', 'Message': 'Cannot get ACL'}}
    mock_s3_regional.get_bucket_acl.side_effect = ClientError(acl_error_response, 'GetBucketAcl')
    mock_s3_regional.get_bucket_policy.side_effect = ClientError({'Error': {'Code': 'NoSuchBucketPolicy', 'Message': 'No policy'}}, 'GetBucketPolicy')
    mock_s3_regional.get_bucket_versioning.return_value = {}
    mock_s3_regional.get_public_access_block.side_effect = ClientError({'Error': {'Code': 'NoSuchPublicAccessBlockConfiguration', 'Message': 'No PAB'}}, 'GetPublicAccessBlock')
    mock_s3_regional.get_bucket_logging.return_value = {}
    def client_side_effect(service_name, region_name=None, **kwargs):
        if service_name == 's3':
            if region_name == s3_collector.settings.AWS_REGION_NAME or region_name == "global": return mock_s3_global
            elif region_name == bucket_region: return mock_s3_regional
        raise ValueError(f"Unexpected client call: {service_name} with region {region_name}")
    mock_boto_client.side_effect = client_side_effect
    result = s3_collector.get_s3_data()
    assert len(result) == 1
    bucket_data = result[0]
    assert bucket_data.name == bucket_name
    assert bucket_data.error_details is not None
    assert "ACL fetch failed: Cannot get ACL" in bucket_data.error_details
    assert bucket_data.acl is not None
    assert bucket_data.acl.is_public is False
    assert "Error fetching ACL: Cannot get ACL" in bucket_data.acl.public_details

@patch('app.aws.s3_collector.boto3.client')
def test_get_s3_data_no_such_bucket_policy(mock_boto_client):
    bucket_name = "test-bucket-no-policy"
    bucket_region = "ap-southeast-1"
    creation_date = datetime.now(timezone.utc)
    mock_s3_global = MagicMock()
    mock_s3_global.list_buckets.return_value = {"Buckets": [{"Name": bucket_name, "CreationDate": creation_date}]}
    mock_s3_global.get_bucket_location.return_value = {"LocationConstraint": bucket_region}
    mock_s3_regional = MagicMock()
    mock_s3_regional.get_bucket_acl.return_value = {"Owner": {}, "Grants": []}
    mock_s3_regional.get_bucket_policy.side_effect = ClientError(
        {'Error': {'Code': 'NoSuchBucketPolicy', 'Message': 'The bucket policy does not exist'}},
        'GetBucketPolicy'
    )
    mock_s3_regional.get_bucket_versioning.return_value = {}
    mock_s3_regional.get_public_access_block.side_effect = ClientError({'Error': {'Code': 'NoSuchPublicAccessBlockConfiguration'}}, 'GetPublicAccessBlock')
    mock_s3_regional.get_bucket_logging.return_value = {}
    def client_side_effect(service_name, region_name=None, **kwargs):
        if service_name == 's3':
            if region_name == s3_collector.settings.AWS_REGION_NAME or region_name == "global": return mock_s3_global
            elif region_name == bucket_region: return mock_s3_regional
        raise ValueError(f"Unexpected client call: {service_name} with region {region_name}")
    mock_boto_client.side_effect = client_side_effect
    result = s3_collector.get_s3_data()
    assert len(result) == 1
    bucket_data = result[0]
    assert bucket_data.name == bucket_name
    assert bucket_data.policy is None
    assert bucket_data.policy_is_public is False
    assert bucket_data.error_details is None

@patch('app.aws.s3_collector.get_bucket_specific_s3_client')
@patch('app.aws.s3_collector.get_s3_client')
def test_get_s3_data_bucket_region_us_east_1(mock_get_s3_client, mock_get_bucket_specific_s3_client):
    bucket_name = "test-bucket-us-east-1"
    creation_date = datetime.now(timezone.utc)
    mock_s3_global_instance = MagicMock()
    mock_s3_global_instance.list_buckets.return_value = {"Buckets": [{"Name": bucket_name, "CreationDate": creation_date}]}
    mock_s3_global_instance.get_bucket_location.return_value = {} # us-east-1 retorna None ou sem LocationConstraint
    mock_get_s3_client.return_value = mock_s3_global_instance
    mock_s3_us_east_1_instance = MagicMock()
    mock_s3_us_east_1_instance.get_bucket_acl.return_value = {"Owner": {}, "Grants": []}
    mock_s3_us_east_1_instance.get_bucket_policy.side_effect = ClientError({'Error': {'Code': 'NoSuchBucketPolicy'}}, 'GetBucketPolicy')
    mock_s3_us_east_1_instance.get_bucket_versioning.return_value = {"Status": "Suspended"}
    mock_s3_us_east_1_instance.get_public_access_block.side_effect = ClientError({'Error': {'Code': 'NoSuchPublicAccessBlockConfiguration'}}, 'GetPublicAccessBlock')
    mock_s3_us_east_1_instance.get_bucket_logging.return_value = {}
    mock_get_bucket_specific_s3_client.return_value = mock_s3_us_east_1_instance
    result = s3_collector.get_s3_data()
    assert len(result) == 1
    bucket_data = result[0]
    assert bucket_data.name == bucket_name
    assert bucket_data.region == "us-east-1"
    assert bucket_data.versioning.status == "Suspended"
    mock_get_bucket_specific_s3_client.assert_called_once_with("us-east-1")
    mock_s3_global_instance.get_bucket_location.assert_called_once_with(Bucket=bucket_name)
    mock_s3_us_east_1_instance.get_bucket_acl.assert_called_once()

@patch('app.aws.s3_collector.boto3.client')
def test_get_s3_data_pab_not_configured(mock_boto_client):
    bucket_name = "test-bucket-no-pab"
    bucket_region = "eu-central-1"
    creation_date = datetime.now(timezone.utc)
    mock_s3_global = MagicMock()
    mock_s3_global.list_buckets.return_value = {"Buckets": [{"Name": bucket_name, "CreationDate": creation_date}]}
    mock_s3_global.get_bucket_location.return_value = {"LocationConstraint": bucket_region}
    mock_s3_regional = MagicMock()
    mock_s3_regional.get_bucket_acl.return_value = {"Owner": {}, "Grants": []}
    mock_s3_regional.get_bucket_policy.side_effect = ClientError({'Error': {'Code': 'NoSuchBucketPolicy'}}, 'GetBucketPolicy')
    mock_s3_regional.get_bucket_versioning.return_value = {}
    mock_s3_regional.get_public_access_block.side_effect = ClientError(
        {'Error': {'Code': 'NoSuchPublicAccessBlockConfiguration', 'Message': 'The public access block configuration does not exist'}},
        'GetPublicAccessBlock'
    )
    mock_s3_regional.get_bucket_logging.return_value = {}
    def client_side_effect(service_name, region_name=None, **kwargs):
        if service_name == 's3':
            if region_name == s3_collector.settings.AWS_REGION_NAME or region_name == "global": return mock_s3_global
            elif region_name == bucket_region: return mock_s3_regional
        raise ValueError(f"Unexpected client call: {service_name} with region {region_name}")
    mock_boto_client.side_effect = client_side_effect
    result = s3_collector.get_s3_data()
    assert len(result) == 1
    bucket_data = result[0]
    assert bucket_data.name == bucket_name
    assert bucket_data.public_access_block is not None
    assert bucket_data.public_access_block.block_public_acls is False
    assert bucket_data.error_details is None

```

Vou fazer o mesmo para `test_ec2_collector.py` e `test_iam_collector.py`.
