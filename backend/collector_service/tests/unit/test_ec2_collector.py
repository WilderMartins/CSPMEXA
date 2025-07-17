import pytest
import boto3
from moto import mock_aws
from app.aws import ec2_collector
import asyncio

@pytest.fixture
def aws_credentials():
    """Mock AWS Credentials."""
    return {"aws_access_key_id": "testing", "aws_secret_access_key": "testing", "aws_session_token": "testing"}

@pytest.mark.asyncio
@mock_aws
async def test_get_ec2_instance_data_no_instances(aws_credentials):
    result = await ec2_collector.get_ec2_instance_data_all_regions(credentials=aws_credentials)
    assert result == []

@pytest.mark.asyncio
@mock_aws
async def test_get_ec2_instance_data_with_instances(aws_credentials):
    ec2_us = boto3.resource("ec2", region_name="us-east-1")
    ec2_us.create_instances(ImageId="ami-123456", MinCount=1, MaxCount=1)

    ec2_eu = boto3.resource("ec2", region_name="eu-west-1")
    ec2_eu.create_instances(ImageId="ami-abcdef", MinCount=2, MaxCount=2)

    result = await ec2_collector.get_ec2_instance_data_all_regions(credentials=aws_credentials)

    assert len(result) == 3
    regions = {i.region for i in result if i.region} # Ignorar instâncias com erro de região
    assert "us-east-1" in regions
    assert "eu-west-1" in regions

@pytest.mark.asyncio
@mock_aws
async def test_get_security_group_data(aws_credentials):
    ec2 = boto3.client("ec2", region_name="us-east-1")
    ec2.create_security_group(GroupName="test-sg", Description="Test SG", VpcId="vpc-12345")

    result = await ec2_collector.get_security_group_data_all_regions(credentials=aws_credentials)

    # Moto cria um SG padrão, então esperamos 2 no total (1 default por região mockada)
    # O número exato pode variar com a versão do moto, o importante é encontrar o nosso.
    assert len(result) >= 1
    sg_names = {sg.GroupName for sg in result}
    assert "test-sg" in sg_names
    assert "default" in sg_names
