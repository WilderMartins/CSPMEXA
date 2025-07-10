import pytest
import boto3
from moto import mock_aws
from typing import List, Generator
from unittest.mock import patch
from fastapi import HTTPException

from app.aws import ec2_collector
from app.schemas.ec2 import Ec2InstanceData, SecurityGroup
from app.core.config import Settings

# Fixture para mockar as settings, especialmente AWS_REGION_NAME
@pytest.fixture
def mock_settings() -> Settings:
    # Usar uma região diferente de us-east-1 para testar a lógica de múltiplas regiões
    return Settings(AWS_REGION_NAME="us-west-2")

@pytest.fixture(autouse=True)
def override_settings(mock_settings: Settings) -> Generator[None, None, None]:
    # Sobrescrever get_settings para retornar nossas settings mockadas
    def get_mocked_settings() -> Settings:
        return mock_settings

    # Limpar caches de clientes antes e depois de cada teste
    ec2_collector.ec2_clients_cache = {}
    with patch('app.aws.ec2_collector.settings', mock_settings):
        yield
    ec2_collector.ec2_clients_cache = {}


@pytest.mark.asyncio
@mock_aws
async def test_get_all_regions_no_regions(mock_settings: Settings):
    # Moto por padrão retorna algumas regiões. Para testar "sem regiões",
    # precisaríamos de uma forma de mockar describe_regions para retornar vazio.
    # No entanto, a AWS sempre terá regiões habilitadas.
    # Um teste mais realista é se ele retorna as regiões mockadas pelo Moto.

    # Por padrão, moto.mock_aws vai mockar ec2.describe_regions para retornar uma lista de regiões.
    # Vamos apenas garantir que a função chame e processe a resposta.
    regions = await ec2_collector.get_all_regions()
    assert isinstance(regions, list)
    # Moto geralmente inclui 'us-east-1', 'us-west-2', etc.
    assert "us-east-1" in regions
    assert "us-west-2" in regions


@pytest.mark.asyncio
@mock_aws
async def test_get_all_regions_client_error(mock_settings: Settings):
    with patch('boto3.client') as mock_boto_client:
        mock_ec2 = mock_boto_client.return_value
        from botocore.exceptions import ClientError
        mock_ec2.describe_regions.side_effect = ClientError(
            {'Error': {'Code': 'TestError', 'Message': 'Simulated DescribeRegions Error'}},
            'DescribeRegions'
        )
        with pytest.raises(HTTPException) as excinfo:
            await ec2_collector.get_all_regions()
        assert excinfo.value.status_code == 500
        assert "Simulated DescribeRegions Error" in excinfo.value.detail


@pytest.mark.asyncio
@mock_aws
async def test_describe_ec2_instances_no_instances(mock_settings: Settings):
    # Testa o caso onde não há instâncias na região mockada (us-west-2)
    # Moto @mock_aws já garante que a região não terá instâncias por padrão.
    result: List[Ec2InstanceData] = await ec2_collector.describe_ec2_instances(region_name=mock_settings.AWS_REGION_NAME)
    assert result == []


@pytest.mark.asyncio
@mock_aws
async def test_describe_ec2_instances_with_one_instance(mock_settings: Settings):
    region = mock_settings.AWS_REGION_NAME
    ec2_resource = boto3.resource("ec2", region_name=region)

    # Criar uma instância mock
    instance_response = ec2_resource.create_instances(
        ImageId="ami-12345678", MinCount=1, MaxCount=1, InstanceType="t2.micro",
        TagSpecifications=[{'ResourceType': 'instance', 'Tags': [{'Key': 'Name', 'Value': 'TestInstance'}]}]
    )
    instance_id = instance_response[0].id

    result: List[Ec2InstanceData] = await ec2_collector.describe_ec2_instances(region_name=region)

    assert len(result) == 1
    instance_data = result[0]
    assert instance_data.instance_id == instance_id
    assert instance_data.instance_type == "t2.micro"
    assert instance_data.image_id == "ami-12345678"
    assert instance_data.region == region
    assert instance_data.tags == [{'Key': 'Name', 'Value': 'TestInstance'}]
    assert instance_data.state is not None
    # Moto pode não popular todos os campos como IP público/privado por padrão sem mais configuração.
    # Os testes devem focar nos campos que Moto popula de forma confiável ou mockar os detalhes.

@pytest.mark.asyncio
@mock_aws
async def test_describe_ec2_instances_client_error(mock_settings: Settings):
    region = mock_settings.AWS_REGION_NAME

    # Mock o cliente EC2 para levantar ClientError em describe_instances
    mock_ec2_client_instance = boto3.client("ec2", region_name=region)
    from botocore.exceptions import ClientError
    error_response = {'Error': {'Code': 'InternalError', 'Message': 'Simulated EC2 service error'}}

    with patch.object(mock_ec2_client_instance, 'get_paginator') as mock_get_paginator:
        mock_paginator = mock_get_paginator.return_value
        mock_paginator.paginate.side_effect = ClientError(error_response, 'DescribeInstances')

        with patch('app.aws.ec2_collector.get_ec2_client', return_value=mock_ec2_client_instance):
            ec2_collector.ec2_clients_cache = {} # Forçar recriação do cliente com o mock

            result = await ec2_collector.describe_ec2_instances(region_name=region)
            assert len(result) == 1
            assert result[0].instance_id == "ERROR_REGION"
            assert result[0].region == region
            assert "ClientError: Simulated EC2 service error" in result[0].error_details


@pytest.mark.asyncio
@mock_aws
async def test_describe_security_groups_no_sgs(mock_settings: Settings):
    # Moto cria um SG padrão. Para testar "sem SGs", precisaríamos deletá-lo
    # ou filtrar. Mais fácil testar com o SG padrão.
    # Este teste irá, portanto, encontrar o SG padrão.
    region = mock_settings.AWS_REGION_NAME
    ec2_client = boto3.client("ec2", region_name=region)

    # Encontrar e deletar o SG padrão se existir (Moto pode recriá-lo)
    # try:
    #     sgs_response = ec2_client.describe_security_groups(GroupNames=['default'])
    #     if sgs_response['SecurityGroups']:
    #         default_sg_id = sgs_response['SecurityGroups'][0]['GroupId']
    #         ec2_client.delete_security_group(GroupId=default_sg_id)
    # except ClientError as e:
    #     if "InvalidGroup.NotFound" not in str(e): # Pode já ter sido deletado
    #         pass # Ignora se não encontrar o default

    # Com o SG padrão, a lista não será vazia.
    result: List[SecurityGroup] = await ec2_collector.describe_security_groups(region_name=region)
    assert len(result) >= 1 # Pelo menos o SG padrão
    assert result[0].group_name == "default" # Moto cria um SG 'default'

@pytest.mark.asyncio
@mock_aws
async def test_describe_security_groups_with_one_sg(mock_settings: Settings):
    region = mock_settings.AWS_REGION_NAME
    ec2_client = boto3.client("ec2", region_name=region)

    sg_name = "test-sg-1"
    sg_description = "Test SG"
    vpc_response = ec2_client.create_default_vpc() # Garante que há uma VPC
    vpc_id = vpc_response['Vpc']['VpcId'] if vpc_response and 'Vpc' in vpc_response else None

    if not vpc_id: # Se create_default_vpc não retornar VPC (ex: já existe), descreva uma.
        vpcs = ec2_client.describe_vpcs()
        if not vpcs['Vpcs']: # Se realmente não há VPCs (improvável com Moto default)
             pytest.skip("No VPC found in Moto to create SG, skipping test")
        vpc_id = vpcs['Vpcs'][0]['VpcId']

    sg_response = ec2_client.create_security_group(
        GroupName=sg_name, Description=sg_description, VpcId=vpc_id,
        TagSpecifications=[{'ResourceType': 'security-group', 'Tags': [{'Key': 'Env', 'Value': 'Test'}]}]
    )
    sg_id = sg_response["GroupId"]

    # Adicionar uma regra de entrada
    ec2_client.authorize_security_group_ingress(
        GroupId=sg_id,
        IpPermissions=[{
            'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22,
            'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
        }]
    )

    result: List[SecurityGroup] = await ec2_collector.describe_security_groups(region_name=region)

    test_sg_data = next((sg for sg in result if sg.group_id == sg_id), None)
    assert test_sg_data is not None
    assert test_sg_data.group_name == sg_name
    assert test_sg_data.description == sg_description
    assert test_sg_data.vpc_id == vpc_id
    assert test_sg_data.region == region
    assert test_sg_data.tags == [{'Key': 'Env', 'Value': 'Test'}]
    assert test_sg_data.ip_permissions is not None
    assert len(test_sg_data.ip_permissions) == 1
    rule = test_sg_data.ip_permissions[0]
    assert rule.ip_protocol == "tcp"
    assert rule.from_port == 22
    assert rule.to_port == 22
    assert rule.ip_ranges[0]['CidrIp'] == '0.0.0.0/0'


@pytest.mark.asyncio
@mock_aws
async def test_describe_security_groups_client_error(mock_settings: Settings):
    region = mock_settings.AWS_REGION_NAME
    mock_ec2_client_instance = boto3.client("ec2", region_name=region)
    from botocore.exceptions import ClientError
    error_response = {'Error': {'Code': 'RequestLimitExceeded', 'Message': 'Simulated SG Limit Exceeded'}}

    with patch.object(mock_ec2_client_instance, 'get_paginator') as mock_get_paginator:
        mock_paginator = mock_get_paginator.return_value
        mock_paginator.paginate.side_effect = ClientError(error_response, 'DescribeSecurityGroups')

        with patch('app.aws.ec2_collector.get_ec2_client', return_value=mock_ec2_client_instance):
            ec2_collector.ec2_clients_cache = {}
            with pytest.raises(HTTPException) as excinfo:
                await ec2_collector.describe_security_groups(region_name=region)
            assert excinfo.value.status_code == 500
            assert "Simulated SG Limit Exceeded" in excinfo.value.detail


@pytest.mark.asyncio
@mock_aws
async def test_get_ec2_instance_data_all_regions(mock_settings: Settings):
    # Mock get_all_regions para retornar apenas a região mockada para simplificar
    # e evitar dependência do estado global do Moto para regiões.
    test_region = mock_settings.AWS_REGION_NAME
    with patch('app.aws.ec2_collector.get_all_regions', return_value=[test_region]):
        ec2_resource = boto3.resource("ec2", region_name=test_region)
        instance_response = ec2_resource.create_instances(ImageId="ami-abcdef12", MinCount=1, MaxCount=1)
        instance_id = instance_response[0].id

        all_instances = await ec2_collector.get_ec2_instance_data_all_regions()

        assert len(all_instances) == 1
        assert all_instances[0].instance_id == instance_id
        assert all_instances[0].region == test_region

# Adicionar testes similares para get_security_group_data_all_regions
@pytest.mark.asyncio
@mock_aws
async def test_get_security_group_data_all_regions(mock_settings: Settings):
    test_region = mock_settings.AWS_REGION_NAME
    with patch('app.aws.ec2_collector.get_all_regions', return_value=[test_region]):
        ec2_client = boto3.client("ec2", region_name=test_region)

        # Moto cria um SG 'default'. Vamos verificar se ele é retornado.
        sgs_response = ec2_client.describe_security_groups(GroupNames=['default'])
        default_sg_id = sgs_response['SecurityGroups'][0]['GroupId']

        all_sgs = await ec2_collector.get_security_group_data_all_regions()

        assert len(all_sgs) >= 1
        default_sg_data = next((sg for sg in all_sgs if sg.group_id == default_sg_id), None)
        assert default_sg_data is not None
        assert default_sg_data.region == test_region
