import pytest
import boto3
from moto import mock_aws # Alterado de mock_s3 para mock_aws
from typing import List, Dict, Any, Generator
from unittest.mock import patch

# Importar as funções e schemas do s3_collector e config
# É importante que o PYTHONPATH esteja configurado para que isso funcione
# ou que os testes sejam executados da raiz do projeto com `python -m pytest backend/collector_service`
from app.aws import s3_collector
from app.schemas.s3 import S3BucketData
from app.core.config import Settings, get_settings

# Fixture para mockar as settings, especialmente AWS_REGION_NAME
@pytest.fixture
def mock_settings() -> Settings:
    return Settings(AWS_REGION_NAME="us-east-1")

@pytest.fixture(autouse=True) # Aplicar automaticamente a todas as funções de teste neste módulo
def override_settings(mock_settings: Settings) -> Generator[None, None, None]:
    # Sobrescrever get_settings para retornar nossas settings mockadas
    # Isso garante que s3_collector.py use a região mockada
    def get_mocked_settings() -> Settings:
        return mock_settings

    with patch('app.aws.s3_collector.settings', mock_settings), \
         patch('app.aws.s3_collector.get_s3_client', wraps=s3_collector.get_s3_client) as mock_get_client:
        # `wraps` permite que a função original seja chamada, mas podemos inspecioná-la.
        # No entanto, para moto, queremos que o cliente seja o cliente mockado pelo moto.
        # Moto faz o patch do boto3.client globalmente quando o decorador @mock_aws é usado.
        # O patch em get_s3_client aqui é mais para garantir que ele seja chamado e para
        # controlar o cache de clientes se necessário, mas moto deve lidar com o cliente real.
        # Para simplificar e garantir que o cliente do Moto seja usado, vamos resetar o cache.
        s3_collector.s3_clients_cache = {}
        yield
    s3_collector.s3_clients_cache = {} # Limpar cache após o teste também

@mock_aws # Decorador principal do Moto para mockar todos os serviços AWS
def test_get_s3_data_no_buckets(mock_settings: Settings):
    # Teste quando não há buckets S3 na conta
    # Moto irá garantir que o boto3.client('s3') não retorne buckets

    # Limpar o cache de clientes para garantir que o cliente mockado seja usado
    s3_collector.s3_clients_cache = {}

    result: List[S3BucketData] = s3_collector.get_s3_data_sync() # Criar uma versão síncrona para teste ou usar async aqui

    assert result == []

@mock_aws
def test_get_s3_data_with_one_bucket(mock_settings: Settings):
    s3_collector.s3_clients_cache = {}
    s3_client = boto3.client("s3", region_name=mock_settings.AWS_REGION_NAME)
    bucket_name = "test-bucket-1"
    s3_client.create_bucket(Bucket=bucket_name)

    # Mock para get_bucket_location, pois create_bucket no moto não define a localização por padrão
    # da mesma forma que a AWS real para todas as regiões. us-east-1 é um caso especial.
    # Se não mockarmos, a região pode vir como None ou causar erro dependendo da versão do moto.
    # No s3_collector, get_bucket_location já tem um fallback para settings.AWS_REGION_NAME
    # se LocationConstraint for None, o que é o comportamento para us-east-1.
    # Se testarmos com outra região, precisaríamos mockar get_bucket_location explicitamente.

    result: List[S3BucketData] = s3_collector.get_s3_data_sync()

    assert len(result) == 1
    bucket_data = result[0]
    assert bucket_data.name == bucket_name
    assert bucket_data.region == mock_settings.AWS_REGION_NAME # Esperado para us-east-1
    assert bucket_data.acl is not None
    assert bucket_data.acl.is_public is False # ACL padrão não é pública
    assert bucket_data.versioning is not None
    assert bucket_data.versioning.status == "NotConfigured" # Padrão
    assert bucket_data.public_access_block is not None # Padrão é tudo False
    assert bucket_data.logging is not None
    assert bucket_data.logging.enabled is False # Padrão


@mock_aws
def test_get_s3_data_with_public_acl(mock_settings: Settings):
    s3_collector.s3_clients_cache = {}
    s3_client = boto3.client("s3", region_name=mock_settings.AWS_REGION_NAME)
    bucket_name = "test-public-acl-bucket"
    s3_client.create_bucket(Bucket=bucket_name)
    s3_client.put_bucket_acl(
        Bucket=bucket_name,
        AccessControlPolicy={
            'Grants': [
                {
                    'Grantee': {'Type': 'Group', 'URI': 'http://acs.amazonaws.com/groups/global/AllUsers'},
                    'Permission': 'READ'
                }
            ],
            'Owner': { # Precisa de um Owner, senão moto pode reclamar
                'DisplayName': "test-owner",
                'ID': "test-owner-id-example"
            }
        }
    )

    result: List[S3BucketData] = s3_collector.get_s3_data_sync()

    assert len(result) == 1
    bucket_data = result[0]
    assert bucket_data.name == bucket_name
    assert bucket_data.acl is not None
    assert bucket_data.acl.is_public is True
    assert "Public (AllUsers) with permission: READ" in bucket_data.acl.public_details


@mock_aws
def test_get_s3_data_with_public_policy(mock_settings: Settings):
    s3_collector.s3_clients_cache = {}
    s3_client = boto3.client("s3", region_name=mock_settings.AWS_REGION_NAME)
    bucket_name = "test-public-policy-bucket"
    s3_client.create_bucket(Bucket=bucket_name)

    public_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": ["s3:GetObject"],
            "Resource": [f"arn:aws:s3:::{bucket_name}/*"]
        }]
    }
    import json
    s3_client.put_bucket_policy(Bucket=bucket_name, Policy=json.dumps(public_policy))

    result: List[S3BucketData] = s3_collector.get_s3_data_sync()

    assert len(result) == 1
    bucket_data = result[0]
    assert bucket_data.name == bucket_name
    assert bucket_data.policy is not None
    assert bucket_data.policy_is_public is True


@mock_aws
def test_get_s3_data_versioning_enabled(mock_settings: Settings):
    s3_collector.s3_clients_cache = {}
    s3_client = boto3.client("s3", region_name=mock_settings.AWS_REGION_NAME)
    bucket_name = "test-versioned-bucket"
    s3_client.create_bucket(Bucket=bucket_name)
    s3_client.put_bucket_versioning(
        Bucket=bucket_name,
        VersioningConfiguration={'Status': 'Enabled'}
    )

    result: List[S3BucketData] = s3_collector.get_s3_data_sync()

    assert len(result) == 1
    bucket_data = result[0]
    assert bucket_data.name == bucket_name
    assert bucket_data.versioning is not None
    assert bucket_data.versioning.status == "Enabled"

# Adicionar mais testes para:
# - Bucket com logging habilitado
# - Bucket com Public Access Block configurado
# - Bucket em região diferente de us-east-1 (requer mock de get_bucket_location se não for us-east-1)
# - Tratamento de erros (ex: ClientError ao tentar obter ACL de um bucket que não permite)
# - Paginação (se list_buckets retornasse muitos buckets)

# Nota: Para rodar estes testes, pode ser necessário ajustar o s3_collector.py
# para ter uma versão síncrona de get_s3_data ou usar uma biblioteca como `pytest-asyncio`
# para testar diretamente a função async. Por simplicidade, assumi uma `get_s3_data_sync`
# que encapsula a lógica async para teste, ou que o teste é adaptado para async.

# Ajuste para usar asyncio com pytest:
# 1. Instalar pytest-asyncio: pip install pytest-asyncio (feito)
# 2. Marcar as funções de teste com @pytest.mark.asyncio
# 3. Chamar `await s3_collector.get_s3_data()`

from botocore.exceptions import ClientError, NoCredentialsError # Importar para mock
from fastapi import HTTPException # Importar para verificar tipo de exceção

@pytest.mark.asyncio
@mock_aws
async def test_get_s3_data_no_buckets(mock_settings: Settings):
    # Teste quando não há buckets S3 na conta já era async.
    # s3_collector.s3_clients_cache = {} # Cache é limpo pelo fixture override_settings
    result: List[S3BucketData] = await s3_collector.get_s3_data()
    assert result == []

@pytest.mark.asyncio
@mock_aws
async def test_get_s3_data_with_one_bucket(mock_settings: Settings):
    # s3_collector.s3_clients_cache = {} # Cache é limpo pelo fixture
    s3_client = boto3.client("s3", region_name=mock_settings.AWS_REGION_NAME)
    bucket_name = "test-bucket-1"
    s3_client.create_bucket(Bucket=bucket_name)

    result: List[S3BucketData] = await s3_collector.get_s3_data()

    assert len(result) == 1
    bucket_data = result[0]
    assert bucket_data.name == bucket_name
    assert bucket_data.region == mock_settings.AWS_REGION_NAME
    assert bucket_data.acl is not None
    assert bucket_data.acl.is_public is False
    assert bucket_data.versioning is not None
    assert bucket_data.versioning.status == "NotConfigured"
    assert bucket_data.public_access_block is not None
    assert bucket_data.logging is not None
    assert bucket_data.logging.enabled is False


@pytest.mark.asyncio
@mock_aws
async def test_get_s3_data_with_public_acl(mock_settings: Settings):
    # s3_collector.s3_clients_cache = {} # Cache é limpo pelo fixture
    s3_client = boto3.client("s3", region_name=mock_settings.AWS_REGION_NAME)
    bucket_name = "test-public-acl-bucket"
    s3_client.create_bucket(Bucket=bucket_name)
    s3_client.put_bucket_acl(
        Bucket=bucket_name,
        AccessControlPolicy={
            'Grants': [
                {
                    'Grantee': {'Type': 'Group', 'URI': 'http://acs.amazonaws.com/groups/global/AllUsers'},
                    'Permission': 'READ'
                }
            ],
            'Owner': {
                'DisplayName': "test-owner",
                'ID': "test-owner-id-example"
            }
        }
    )

    result: List[S3BucketData] = await s3_collector.get_s3_data()

    assert len(result) == 1
    bucket_data = result[0]
    assert bucket_data.name == bucket_name
    assert bucket_data.acl is not None
    assert bucket_data.acl.is_public is True
    assert "Public (AllUsers) with permission: READ" in bucket_data.acl.public_details


@pytest.mark.asyncio
@mock_aws
async def test_get_s3_data_with_public_policy(mock_settings: Settings):
    # s3_collector.s3_clients_cache = {} # Cache é limpo pelo fixture
    s3_client = boto3.client("s3", region_name=mock_settings.AWS_REGION_NAME)
    bucket_name = "test-public-policy-bucket"
    s3_client.create_bucket(Bucket=bucket_name)

    public_policy_doc = {
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": ["s3:GetObject"],
            "Resource": [f"arn:aws:s3:::{bucket_name}/*"]
        }]
    }
    import json
    s3_client.put_bucket_policy(Bucket=bucket_name, Policy=json.dumps(public_policy_doc))

    result: List[S3BucketData] = await s3_collector.get_s3_data()

    assert len(result) == 1
    bucket_data = result[0]
    assert bucket_data.name == bucket_name
    assert bucket_data.policy is not None
    assert bucket_data.policy_is_public is True


@pytest.mark.asyncio
@mock_aws
async def test_get_s3_data_versioning_enabled(mock_settings: Settings):
    # s3_collector.s3_clients_cache = {} # Cache é limpo pelo fixture
    s3_client = boto3.client("s3", region_name=mock_settings.AWS_REGION_NAME)
    bucket_name = "test-versioned-bucket"
    s3_client.create_bucket(Bucket=bucket_name)
    s3_client.put_bucket_versioning(
        Bucket=bucket_name,
        VersioningConfiguration={'Status': 'Enabled'}
    )

    result: List[S3BucketData] = await s3_collector.get_s3_data()

    assert len(result) == 1
    bucket_data = result[0]
    assert bucket_data.name == bucket_name
    assert bucket_data.versioning is not None
    assert bucket_data.versioning.status == "Enabled"

@pytest.mark.asyncio
@mock_aws
async def test_get_s3_data_logging_enabled(mock_settings: Settings):
    # s3_collector.s3_clients_cache = {} # Cache é limpo pelo fixture
    s3_client = boto3.client("s3", region_name=mock_settings.AWS_REGION_NAME)
    bucket_name = "test-logging-bucket"
    target_bucket_name = "test-log-target-bucket" # Moto requer que o target bucket exista
    s3_client.create_bucket(Bucket=bucket_name)
    s3_client.create_bucket(Bucket=target_bucket_name) # Criar o bucket de destino dos logs

    s3_client.put_bucket_logging(
        Bucket=bucket_name,
        BucketLoggingStatus={
            'LoggingEnabled': {
                'TargetBucket': target_bucket_name,
                'TargetPrefix': 'logs/'
            }
        }
    )
    result: List[S3BucketData] = await s3_collector.get_s3_data()
    assert len(result) == 2 # Conta o bucket de log também

    bucket_data = next(b for b in result if b.name == bucket_name) # Encontra o bucket de teste
    assert bucket_data.logging is not None
    assert bucket_data.logging.enabled is True
    assert bucket_data.logging.target_bucket == target_bucket_name
    assert bucket_data.logging.target_prefix == 'logs/'

@pytest.mark.asyncio
@mock_aws
async def test_get_s3_data_pab_configured(mock_settings: Settings):
    # s3_collector.s3_clients_cache = {} # Cache é limpo pelo fixture
    s3_client = boto3.client("s3", region_name=mock_settings.AWS_REGION_NAME)
    bucket_name = "test-pab-bucket"
    s3_client.create_bucket(Bucket=bucket_name)
    s3_client.put_public_access_block(
        Bucket=bucket_name,
        PublicAccessBlockConfiguration={
            'BlockPublicAcls': True,
            'IgnorePublicAcls': True,
            'BlockPublicPolicy': True,
            'RestrictPublicBuckets': True
        }
    )
    result: List[S3BucketData] = await s3_collector.get_s3_data()
    assert len(result) == 1
    bucket_data = result[0]
    assert bucket_data.public_access_block is not None
    assert bucket_data.public_access_block.block_public_acls is True
    assert bucket_data.public_access_block.restrict_public_buckets is True


# O fixture `override_settings` com `autouse=True` ajuda com o cache e settings.

@pytest.mark.asyncio
@mock_aws
async def test_get_s3_data_acl_access_denied_simulation(mock_settings: Settings):
    # s3_collector.s3_clients_cache = {} # Cache é limpo pelo fixture
    s3_client = boto3.client("s3", region_name=mock_settings.AWS_REGION_NAME)
    bucket_name = "test-acl-denied-bucket"
    s3_client.create_bucket(Bucket=bucket_name)

    # Mock get_bucket_acl para levantar ClientError para este bucket específico
    original_get_bucket_acl = s3_collector.get_bucket_specific_s3_client(mock_settings.AWS_REGION_NAME).get_bucket_acl

    def mock_get_bucket_acl_that_fails(Bucket):
        if Bucket == bucket_name:
            raise ClientError({'Error': {'Code': 'AccessDenied', 'Message': 'Simulated Access Denied'}}, 'GetBucketAcl')
        return original_get_bucket_acl(Bucket=Bucket)

    # Usar patch no cliente S3 que será retornado por get_bucket_specific_s3_client
    # Pode ser um pouco complexo se o cliente já estiver no cache.
    # Uma forma mais robusta poderia ser mockar a função `check_s3_bucket_acl` dentro do `s3_collector`
    # ou mockar o método `get_bucket_acl` do cliente que será usado.

    # Simplificação: o código em s3_collector já trata ClientError para get_bucket_acl.
    # Este teste verifica se `error_details` é populado.
    # Para forçar o erro, precisamos garantir que o mock seja aplicado corretamente.
    # Como o `s3_collector` instancia clientes dinamicamente por região,
    # o patch precisa ser no local correto onde o cliente é usado ou na chamada do boto3.client.

    # Este teste é mais conceitual, pois a simulação exata de ClientError apenas para uma chamada
    # com Moto pode ser tricky sem alterar o código de produção para injetar mocks.
    # O código de produção já tem try-except, então confiamos que ele loga e continua.
    # Para verificar `error_details`, precisaríamos que o `parse_acl` ou `check_s3_bucket_acl`
    # retornasse um objeto que `get_s3_data` pudesse usar para popular `error_details`.
    # A função `parse_acl` no `s3_collector` já retorna um objeto `S3BucketACLDetails`
    # que pode conter `public_details` com mensagens de erro.

    # Vamos testar o cenário onde get_bucket_location falha, pois isso é mais fácil de mockar
    # e o s3_collector.py já tem lógica para lidar com isso e definir a região como 'unknown'.

    with patch.object(s3_collector.get_s3_client("global"), 'get_bucket_location', side_effect=ClientError({'Error': {'Code': 'AccessDenied', 'Message': 'Cannot get location'}}, 'GetBucketLocation')):
        result = await s3_collector.get_s3_data()
        # Se houver buckets, eles terão a região 'unknown' e error_details.
        # Se não houver buckets (como neste caso, pois o create_bucket não será encontrado devido ao mock),
        # o resultado será uma lista vazia ou erro global dependendo de onde o mock é aplicado.
        # Este mock específico para get_bucket_location no cliente global pode não ser o ideal.
        # Melhor seria mockar a chamada de get_bucket_location dentro do loop de get_s3_data.
        # No entanto, o `s3_collector` já tem try-except para `get_bucket_location`.
        # Se a localização falhar, ele usa `settings.AWS_REGION_NAME` e adiciona ao `error_message`.
        # Então, o teste para `error_details` de falha de localização seria:
        # 1. Criar bucket
        # 2. Mockar `s3_global_client.get_bucket_location` para dar erro para ESSE bucket.
        # 3. Verificar se `bucket_data.error_details` contém a mensagem de falha de localização.

    # Teste mais focado no error_details de ACL:
    # Suponha que o bucket existe, mas get_bucket_acl falha
    s3_client_regional_mock = boto3.client("s3", region_name=mock_settings.AWS_REGION_NAME)
    with patch.object(s3_client_regional_mock, 'get_bucket_acl', side_effect=ClientError({'Error': {'Code': 'AccessDenied', 'Message': 'ACL Denied Test'}}, 'GetBucketAcl')), \
         patch('app.aws.s3_collector.get_bucket_specific_s3_client', return_value=s3_client_regional_mock):

        # Recriar o bucket no contexto deste mock para garantir que `list_buckets` o encontre
        s3_global_client = boto3.client("s3", region_name=mock_settings.AWS_REGION_NAME)
        s3_global_client.create_bucket(Bucket=bucket_name) # Assegura que o bucket existe para ser listado

        result_with_acl_error = await s3_collector.get_s3_data()

        assert len(result_with_acl_error) == 1
        bucket_data_error = result_with_acl_error[0]
        assert bucket_data_error.name == bucket_name
        assert "ACL fetch failed: Access Denied Test" in bucket_data_error.error_details
        assert bucket_data_error.acl is not None # O objeto ACL ainda é criado com detalhes do erro
        assert "Error fetching ACL: Access Denied Test" in bucket_data_error.acl.public_details


# Teste para o caso de erro de credenciais global
@pytest.mark.asyncio
@mock_aws
async def test_get_s3_data_no_credentials(mock_settings: Settings):
    # s3_collector.s3_clients_cache = {} # Cache é limpo pelo fixture
    with patch('boto3.client', side_effect=NoCredentialsError()) as mock_boto_client:
        with pytest.raises(HTTPException) as excinfo:
            await s3_collector.get_s3_data()

        assert excinfo.value.status_code == 500
        assert "AWS credentials not configured" in excinfo.value.detail
        # mock_boto_client.assert_called_once() # A chamada pode ocorrer múltiplas vezes devido ao cache e clientes regionais.


# Teste para o caso de ClientError global em list_buckets
@pytest.mark.asyncio
@mock_aws
async def test_get_s3_data_list_buckets_client_error(mock_settings: Settings):
    # s3_collector.s3_clients_cache = {} # Cache é limpo pelo fixture
    mock_s3_client_instance = boto3.client("s3", region_name=mock_settings.AWS_REGION_NAME)
    error_response = {'Error': {'Code': 'InternalError', 'Message': 'Simulated service error'}}

    # Patch a instância do cliente que seria usada para list_buckets
    with patch.object(mock_s3_client_instance, 'list_buckets', side_effect=ClientError(error_response, 'ListBuckets')) as mock_list_buckets, \
         patch('app.aws.s3_collector.get_s3_client', return_value=mock_s3_client_instance):

        # s3_collector.s3_clients_cache = {} # Garantir que o get_s3_client seja chamado e use nosso mock
                                         # Removido pois o fixture `override_settings` já lida com o cache.

        with pytest.raises(HTTPException) as excinfo:
            await s3_collector.get_s3_data()

        assert excinfo.value.status_code == 500
        assert "ClientError listing S3 buckets: Simulated service error" in excinfo.value.detail
        mock_list_buckets.assert_called_once()
