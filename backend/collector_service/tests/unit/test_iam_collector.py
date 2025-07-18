import pytest
import boto3
from moto import mock_aws
from app.aws import iam_collector
import asyncio
import json

@pytest.fixture
def aws_credentials():
    """Mock AWS Credentials."""
    return {"aws_access_key_id": "testing", "aws_secret_access_key": "testing", "aws_session_token": "testing"}

@pytest.mark.asyncio
@mock_aws
async def test_get_iam_users_data_no_users(aws_credentials):
    result = await iam_collector.get_iam_users_data(credentials=aws_credentials)
    assert result == []

@pytest.mark.asyncio
@mock_aws
async def test_get_iam_users_data_with_one_user(aws_credentials):
    iam_client = boto3.client("iam", region_name="us-east-1")
    user_name = "test-user"
    iam_client.create_user(UserName=user_name)

    result = await iam_collector.get_iam_users_data(credentials=aws_credentials)

    assert len(result) == 1
    assert result[0].user_name == user_name
    # O sumário da conta deve ser anexado ao primeiro usuário
    assert result[0].account_summary is not None
    assert "Users" in result[0].account_summary

@pytest.mark.asyncio
@mock_aws
async def test_get_iam_roles_data_no_roles(aws_credentials):
    result = await iam_collector.get_iam_roles_data(credentials=aws_credentials)
    assert result == []

@pytest.mark.asyncio
@mock_aws
async def test_get_iam_roles_data_with_one_role(aws_credentials):
    iam_client = boto3.client("iam", region_name="us-east-1")
    role_name = "test-role"
    assume_role_policy = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Principal": {"Service": "ec2.amazonaws.com"}, "Action": "sts:AssumeRole"}]
    }
    iam_client.create_role(RoleName=role_name, AssumeRolePolicyDocument=json.dumps(assume_role_policy))

    result = await iam_collector.get_iam_roles_data(credentials=aws_credentials)

    assert len(result) == 1
    assert result[0].role_name == role_name

@pytest.mark.asyncio
@mock_aws
async def test_get_iam_policies_data(aws_credentials):
    iam_client = boto3.client("iam", region_name="us-east-1")
    policy_name = "test-policy"
    policy_doc = {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": "s3:*", "Resource": "*"}]}
    iam_client.create_policy(PolicyName=policy_name, PolicyDocument=json.dumps(policy_doc))

    result = await iam_collector.get_iam_policies_data(credentials=aws_credentials, scope="Local")

    assert len(result) == 1
    assert result[0].policy_name == policy_name
