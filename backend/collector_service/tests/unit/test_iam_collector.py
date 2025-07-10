import pytest
import boto3
from moto import mock_aws
from typing import List, Generator
from unittest.mock import patch
from fastapi import HTTPException
import json
from datetime import datetime, timezone

from app.aws import iam_collector
from app.schemas.iam import IAMUserData, IAMRoleData, IAMPolicyData, IAMUserAccessKeyMetadata
from app.core.config import Settings

# Fixture para mockar as settings
@pytest.fixture
def mock_settings() -> Settings:
    # IAM é global, mas o cliente pode ser inicializado com uma região.
    return Settings(AWS_REGION_NAME="us-east-1")

@pytest.fixture(autouse=True)
def override_settings(mock_settings: Settings) -> Generator[None, None, None]:
    def get_mocked_settings() -> Settings:
        return mock_settings

    iam_collector.iam_client_cache = None # Limpar cache do cliente IAM
    with patch('app.aws.iam_collector.settings', mock_settings):
        yield
    iam_collector.iam_client_cache = None


@pytest.mark.asyncio
@mock_aws
async def test_get_iam_users_data_no_users(mock_settings: Settings):
    # Moto não cria usuários IAM por padrão, então este teste deve passar.
    result: List[IAMUserData] = await iam_collector.get_iam_users_data()
    assert result == []

@pytest.mark.asyncio
@mock_aws
async def test_get_iam_users_data_one_user(mock_settings: Settings):
    iam_client = boto3.client("iam", region_name=mock_settings.AWS_REGION_NAME)
    user_name = "test-user-1"
    iam_client.create_user(UserName=user_name, Tags=[{'Key': 'Env', 'Value': 'Test'}])

    # Adicionar uma chave de acesso
    key_response = iam_client.create_access_key(UserName=user_name)
    access_key_id = key_response['AccessKey']['AccessKeyId']

    # Adicionar um dispositivo MFA (simulado)
    # Moto pode não simular completamente o processo de registro de MFA,
    # mas list_mfa_devices deve funcionar se um dispositivo for "criado".
    # create_virtual_mfa_device e enable_mfa_device são necessários.
    mfa_device_response = iam_client.create_virtual_mfa_device(VirtualMFADeviceName="testmfa")
    mfa_arn = mfa_device_response['VirtualMFADevice']['SerialNumber']
    # A associação real requer códigos, o que é complexo para mock.
    # Por enquanto, vamos testar o caso sem MFA e com MFA mockando a listagem.

    # Adicionar uma política inline
    inline_policy_name = "TestInlinePolicy"
    inline_policy_doc = {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": "s3:ListAllMyBuckets", "Resource": "*"}]}
    iam_client.put_user_policy(UserName=user_name, PolicyName=inline_policy_name, PolicyDocument=json.dumps(inline_policy_doc))

    # Adicionar uma política gerenciada
    managed_policy_response = iam_client.create_policy(
        PolicyName="TestManagedPolicy",
        PolicyDocument=json.dumps({"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": "ec2:DescribeInstances", "Resource": "*"}]})
    )
    managed_policy_arn = managed_policy_response['Policy']['Arn']
    iam_client.attach_user_policy(UserName=user_name, PolicyArn=managed_policy_arn)

    # Mock get_access_key_last_used para retornar algo previsível
    # O `iam_collector` chama `get_access_key_last_used`. Precisamos mockar a resposta.
    mock_last_used_date = datetime.now(timezone.utc)
    with patch.object(iam_client, 'get_access_key_last_used', return_value={
        'AccessKeyLastUsed': {
            'LastUsedDate': mock_last_used_date,
            'ServiceName': 's3',
            'Region': 'us-east-1'
        }
    }) as mock_get_last_used, \
    patch.object(iam_client, 'list_mfa_devices', return_value={'MFADevices': []}) as mock_list_mfa: # Simular sem MFA por enquanto
        # Se quisermos testar com MFA:
        # mock_list_mfa.return_value = {'MFADevices': [{'UserName': user_name, 'SerialNumber': mfa_arn, 'EnableDate': datetime.now(timezone.utc)}]}

        result: List[IAMUserData] = await iam_collector.get_iam_users_data()

    assert len(result) == 1
    user_data = result[0]
    assert user_data.user_name == user_name
    assert user_data.tags == [{'Key': 'Env', 'Value': 'Test'}]

    assert user_data.access_keys is not None
    assert len(user_data.access_keys) == 1
    key_meta = user_data.access_keys[0]
    assert key_meta.access_key_id == access_key_id
    assert key_meta.status == "Active"
    assert key_meta.last_used_date is not None # Checar se o mock funcionou
    # mock_get_last_used.assert_called_with(AccessKeyId=access_key_id) # Verificar se foi chamado

    assert user_data.mfa_devices == [] # Devido ao mock_list_mfa

    assert user_data.inline_policies is not None
    assert len(user_data.inline_policies) == 1
    assert user_data.inline_policies[0].policy_name == inline_policy_name
    assert user_data.inline_policies[0].policy_document == inline_policy_doc

    assert user_data.attached_policies is not None
    assert len(user_data.attached_policies) == 1
    assert user_data.attached_policies[0].policy_arn == managed_policy_arn
    assert user_data.attached_policies[0].policy_name == "TestManagedPolicy"


@pytest.mark.asyncio
@mock_aws
async def test_get_iam_users_data_client_error_list_users(mock_settings: Settings):
    # Mock list_users para levantar ClientError
    mock_iam_client_instance = boto3.client("iam", region_name=mock_settings.AWS_REGION_NAME)
    from botocore.exceptions import ClientError
    error_response = {'Error': {'Code': 'ServiceUnavailable', 'Message': 'IAM service unavailable'}}

    with patch.object(mock_iam_client_instance, 'get_paginator') as mock_get_paginator:
        mock_paginator_instance = mock_get_paginator.return_value
        mock_paginator_instance.paginate.side_effect = ClientError(error_response, 'ListUsers')

        with patch('app.aws.iam_collector.get_iam_client', return_value=mock_iam_client_instance):
            iam_collector.iam_client_cache = None # Forçar recriação do cliente com o mock
            with pytest.raises(HTTPException) as excinfo:
                await iam_collector.get_iam_users_data()
            assert excinfo.value.status_code == 500
            assert "IAM service unavailable" in excinfo.value.detail

@pytest.mark.asyncio
@mock_aws
async def test_get_iam_user_details_partial_failure(mock_settings: Settings):
    iam_client = boto3.client("iam", region_name=mock_settings.AWS_REGION_NAME)
    user_name = "test-user-partial-fail"
    iam_client.create_user(UserName=user_name)

    from botocore.exceptions import ClientError
    error_response_policy = {'Error': {'Code': 'AccessDenied', 'Message': 'Cannot list policies'}}

    # Mock apenas list_attached_user_policies para falhar
    with patch.object(iam_client, 'get_paginator') as mock_get_paginator:
        # Configurar o paginador para diferentes chamadas
        def paginator_side_effect(operation_name):
            if operation_name == 'list_attached_user_policies':
                mock_paginator_instance = mock_get_paginator.return_value # Precisa de uma nova instância de mock
                mock_paginator_instance.paginate.side_effect = ClientError(error_response_policy, 'ListAttachedUserPolicies')
                return mock_paginator_instance
            # Para outras operações, retorna um paginador que funciona (ou mockado para sucesso)
            # Aqui, estamos interessados apenas na falha de list_attached_user_policies
            # Outras chamadas dentro de get_iam_user_details (como list_user_policies) usarão o paginador real do Moto.
            # Isso pode ser complexo. Uma abordagem mais simples é mockar a chamada de API de baixo nível.
            # Ex: patch.object(iam_client, 'list_attached_user_policies', side_effect=ClientError(...))
            # No entanto, o código usa paginators.

            # Simplificação: Mock a função de alto nível que usa o paginador
            original_paginator = boto3.client("iam").get_paginator(operation_name) # Pega um paginador real para outras chamadas
            return original_paginator

        # Re-patch get_paginator para o cliente que será usado por get_iam_client
        # Este teste está ficando complexo de mockar precisamente com paginators.
        # O código do iam_collector já tem try-except para ClientError nas chamadas de detalhes.
        # Vamos confiar nesses try-except e testar o resultado.

    # Uma forma mais direta de testar error_details:
    with patch.object(iam_client, 'list_attached_user_policies', side_effect=ClientError(error_response_policy, 'ListAttachedUserPolicies')):
         # Precisamos que o iam_collector.get_iam_client() retorne este iam_client mockado.
        with patch('app.aws.iam_collector.get_iam_client', return_value=iam_client):
            iam_collector.iam_client_cache = None # Forçar recriação
            result: List[IAMUserData] = await iam_collector.get_iam_users_data()

    assert len(result) == 1
    user_data = result[0]
    assert user_data.user_name == user_name
    assert "Failed to retrieve some details" in user_data.error_details
    assert "Cannot list policies" in user_data.error_details # Verifica se a mensagem de erro está lá
    assert user_data.attached_policies == [] # Deve ser vazio devido ao erro


# --- Testes para Roles IAM (Esqueleto) ---
@pytest.mark.asyncio
@mock_aws
async def test_get_iam_roles_data_no_roles(mock_settings: Settings):
    result: List[IAMRoleData] = await iam_collector.get_iam_roles_data()
    assert result == [] # Moto não cria roles por padrão

@pytest.mark.asyncio
@mock_aws
async def test_get_iam_roles_data_one_role(mock_settings: Settings):
    iam_client = boto3.client("iam", region_name=mock_settings.AWS_REGION_NAME)
    role_name = "TestRole-1"
    assume_role_policy_doc = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Principal": {"Service": "ec2.amazonaws.com"}, "Action": "sts:AssumeRole"}]
    }
    iam_client.create_role(RoleName=role_name, AssumeRolePolicyDocument=json.dumps(assume_role_policy_doc))

    result: List[IAMRoleData] = await iam_collector.get_iam_roles_data()
    assert len(result) == 1
    role_data = result[0]
    assert role_data.role_name == role_name
    assert role_data.assume_role_policy_document == assume_role_policy_doc
    # Adicionar mais verificações para políticas anexadas, inline, tags, role_last_used


# --- Testes para Policies IAM (Esqueleto) ---
@pytest.mark.asyncio
@mock_aws
async def test_get_iam_policies_data_no_local_policies(mock_settings: Settings):
    # Scope="Local" é o padrão
    result: List[IAMPolicyData] = await iam_collector.get_iam_policies_data()
    assert result == [] # Moto não cria políticas 'Local' por padrão

@pytest.mark.asyncio
@mock_aws
async def test_get_iam_policies_data_one_local_policy(mock_settings: Settings):
    iam_client = boto3.client("iam", region_name=mock_settings.AWS_REGION_NAME)
    policy_name = "MyCustomPolicy"
    policy_doc = {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": "s3:*", "Resource": "*"}]}
    iam_client.create_policy(PolicyName=policy_name, PolicyDocument=json.dumps(policy_doc))

    result: List[IAMPolicyData] = await iam_collector.get_iam_policies_data(scope="Local")
    assert len(result) == 1
    policy_data = result[0]
    assert policy_data.policy_name == policy_name
    assert policy_data.policy_document == policy_doc # Verifica se o documento foi obtido
    # Adicionar mais verificações para outros campos

@pytest.mark.asyncio
@mock_aws
async def test_get_iam_policies_data_aws_managed(mock_settings: Settings):
    # Moto cria algumas políticas gerenciadas pela AWS por padrão.
    result: List[IAMPolicyData] = await iam_collector.get_iam_policies_data(scope="AWS")
    assert len(result) > 0 # Espera-se que Moto tenha algumas políticas AWS
    # Ex: procurar por uma política conhecida como "AdministratorAccess"
    admin_policy = next((p for p in result if p.policy_name == "AdministratorAccess"), None)
    assert admin_policy is not None
    assert admin_policy.policy_document is not None # Documento deve ser buscado
