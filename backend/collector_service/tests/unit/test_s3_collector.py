import pytest
import boto3
from moto import mock_aws
from app.aws import s3_collector
import asyncio
import json

@pytest.fixture
def aws_credentials():
    """Mock AWS Credentials."""
    return {"aws_access_key_id": "testing", "aws_secret_access_key": "testing", "aws_session_token": "testing"}

@pytest.mark.asyncio
@mock_aws
async def test_get_s3_data_no_buckets(aws_credentials):
    result = await s3_collector.get_s3_data(credentials=aws_credentials)
    assert result == []

@pytest.mark.asyncio
@mock_aws
async def test_get_s3_data_with_buckets(aws_credentials):
    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.create_bucket(Bucket="test-bucket-1")
    s3_client.create_bucket(Bucket="test-bucket-2", CreateBucketConfiguration={'LocationConstraint': 'eu-west-1'})

    result = await s3_collector.get_s3_data(credentials=aws_credentials)

    assert len(result) == 2
    bucket_names = {b.name for b in result}
    assert "test-bucket-1" in bucket_names
    assert "test-bucket-2" in bucket_names

    bucket1 = next(b for b in result if b.name == "test-bucket-1")
    bucket2 = next(b for b in result if b.name == "test-bucket-2")

    assert bucket1.region == "us-east-1"
    assert bucket2.region == "eu-west-1"

@pytest.mark.asyncio
@mock_aws
async def test_get_s3_data_with_public_acl(aws_credentials):
    s3_client = boto3.client("s3", region_name="us-east-1")
    bucket_name = "test-public-acl-bucket"
    s3_client.create_bucket(Bucket=bucket_name)
    s3_client.put_bucket_acl(
        Bucket=bucket_name,
        AccessControlPolicy={
            'Grants': [{'Grantee': {'Type': 'Group', 'URI': 'http://acs.amazonaws.com/groups/global/AllUsers'}, 'Permission': 'READ'}],
            'Owner': {'DisplayName': "test", 'ID': "test"}
        }
    )

    result = await s3_collector.get_s3_data(credentials=aws_credentials)

    assert len(result) == 1
    assert result[0].acl.is_public is True

@pytest.mark.asyncio
@mock_aws
async def test_get_s3_data_with_public_policy(aws_credentials):
    s3_client = boto3.client("s3", region_name="us-east-1")
    bucket_name = "test-public-policy-bucket"
    s3_client.create_bucket(Bucket=bucket_name)

    public_policy = {
        "Statement": [{"Effect": "Allow", "Principal": "*", "Action": "s3:GetObject", "Resource": f"arn:aws:s3:::{bucket_name}/*"}]
    }
    s3_client.put_bucket_policy(Bucket=bucket_name, Policy=json.dumps(public_policy))

    result = await s3_collector.get_s3_data(credentials=aws_credentials)

    assert len(result) == 1
    assert result[0].policy_is_public is True
