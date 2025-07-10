import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from typing import List, Optional, Any
from datetime import datetime, timezone, timedelta

from app.huawei import huawei_obs_collector
from app.schemas.huawei_obs import (
    HuaweiOBSBucketData, HuaweiOBSBucketPolicy, HuaweiOBSBucketPolicyStatement,
    HuaweiOBSBucketACL, HuaweiOBSGrant, HuaweiOBSGrantee, HuaweiOBSOwner,
    HuaweiOBSBucketVersioning, HuaweiOBSBucketLogging
)
from app.core.config import Settings
from huaweicloudsdkcore.exceptions import exceptions as sdk_exceptions # SdkException, ServiceResponseException
from huaweicloudsdkobs.v1.model import Bucket, ListBucketsResponse, GetBucketPolicyResponse, \
                                       GetBucketAclResponse, GetBucketVersioningResponse, \
                                       GetBucketLoggingResponse, Owner as ObsOwner, Grantee as ObsGrantee, \
                                       Grant as ObsGrant, LoggingEnabled, PolicyStatement # Importar tipos de resposta do SDK

# --- Fixtures ---

@pytest.fixture
def mock_huawei_settings() -> Settings:
    return Settings() # Default settings, não usado diretamente pelo collector, mas pelo client_manager

@pytest.fixture(autouse=True)
def override_huawei_collector_settings(mock_huawei_settings: Settings):
    with patch('app.huawei.huawei_client_manager._clients_cache', new_callable=dict):
        with patch('app.huawei.huawei_obs_collector.settings', mock_huawei_settings,_if_exists=True), \
             patch('app.huawei.huawei_client_manager.settings', mock_huawei_settings):
            # Limpar cache do cliente OBS específico no módulo do coletor, se ele tiver um próprio
            if hasattr(huawei_obs_collector, '_clients_cache'): # Verificar se o cache existe no módulo
                 huawei_obs_collector._clients_cache = {}
            yield
            if hasattr(huawei_obs_collector, '_clients_cache'):
                 huawei_obs_collector._clients_cache = {}


@pytest.fixture
def mock_obs_client():
    with patch('app.huawei.huawei_client_manager.get_obs_client') as mock_get_client:
        mock_client_instance = MagicMock()
        # Mockar os métodos do cliente que serão chamados
        mock_client_instance.listBuckets = MagicMock()
        mock_client_instance.getBucketPolicy = MagicMock()
        mock_client_instance.getBucketAcl = MagicMock()
        mock_client_instance.getBucketVersioning = MagicMock()
        mock_client_instance.getBucketLogging = MagicMock()
        mock_get_client.return_value = mock_client_instance
        yield mock_client_instance

@pytest.fixture
def mock_huawei_credentials_success():
    # Mock para get_huawei_credentials que retorna credenciais válidas e project_id
    mock_creds = MagicMock()
    mock_creds.ak = "test_ak"
    mock_creds.sk = "test_sk"
    with patch('app.huawei.huawei_client_manager.get_huawei_credentials', return_value=(mock_creds, "test_project_id")) as mock_creds_func:
        yield mock_creds_func

# --- Testes ---

@pytest.mark.asyncio
async def test_get_huawei_obs_buckets_no_creds(mock_obs_client):
    # Simular falha ao obter credenciais
    with patch('app.huawei.huawei_client_manager.get_huawei_credentials', side_effect=ValueError("Simulated credential error")):
        result = await huawei_obs_collector.get_huawei_obs_buckets(project_id="proj1", region_id="reg1")
        assert len(result) == 1
        assert result[0].name == "ERROR_CREDENTIALS"
        assert "Simulated credential error" in result[0].error_details
        mock_obs_client.listBuckets.assert_not_called()


@pytest.mark.asyncio
async def test_get_huawei_obs_buckets_list_buckets_sdk_error(mock_huawei_credentials_success, mock_obs_client):
    mock_obs_client.listBuckets.side_effect = sdk_exceptions.SdkException(error_code="SDK.ClientError", error_message="Simulated SDK list buckets failure")

    result = await huawei_obs_collector.get_huawei_obs_buckets(project_id="proj1", region_id="reg1")
    assert len(result) == 1
    assert result[0].name == "ERROR_LIST_BUCKETS_SDK_reg1"
    assert "SDK.ClientError: Simulated SDK list buckets failure" in result[0].error_details

@pytest.mark.asyncio
async def test_get_huawei_obs_buckets_no_buckets_returned(mock_huawei_credentials_success, mock_obs_client):
    # Simular resposta vazia de listBuckets
    mock_list_response = MagicMock(spec=ListBucketsResponse)
    # O SDK pode ter 'body.buckets' ou só 'buckets'. Vamos mockar 'body' primeiro.
    mock_list_response_body = MagicMock()
    mock_list_response_body.buckets = []
    type(mock_list_response).body = PropertyMock(return_value=mock_list_response_body) # Simula que resp.body existe
    mock_obs_client.listBuckets.return_value = mock_list_response

    result = await huawei_obs_collector.get_huawei_obs_buckets(project_id="proj1", region_id="reg1")
    assert result == []
    mock_obs_client.listBuckets.assert_called_once()


@pytest.mark.asyncio
async def test_get_huawei_obs_buckets_one_bucket_basic_data(mock_huawei_credentials_success, mock_obs_client):
    # Mock para listBuckets
    mock_bucket_info_native = Bucket(name="test-bucket-1", creation_date="2023-01-01T10:00:00.000Z", location="cn-north-1")
    # mock_bucket_info_native.storage_class = "STANDARD" # Adicionar se o objeto Bucket tiver

    mock_list_response_body = MagicMock()
    mock_list_response_body.buckets = [mock_bucket_info_native]
    mock_list_response = MagicMock(spec=ListBucketsResponse)
    type(mock_list_response).body = PropertyMock(return_value=mock_list_response_body)
    mock_obs_client.listBuckets.return_value = mock_list_response

    # Mocks para chamadas de detalhes do bucket
    # Policy (vazia)
    mock_policy_response_body = MagicMock()
    type(mock_policy_response_body).policy = PropertyMock(return_value=json.dumps({"Statement": []})) # Política vazia
    mock_policy_response = MagicMock(spec=GetBucketPolicyResponse)
    type(mock_policy_response).body = PropertyMock(return_value=mock_policy_response_body)
    mock_obs_client.getBucketPolicy.return_value = mock_policy_response

    # ACL (owner apenas)
    mock_acl_response_body = MagicMock()
    mock_acl_response_body.owner = ObsOwner(id="owner-id")
    mock_acl_response_body.grants = [] # Sem grants explícitos além do owner
    mock_acl_response = MagicMock(spec=GetBucketAclResponse)
    type(mock_acl_response).body = PropertyMock(return_value=mock_acl_response_body)
    mock_obs_client.getBucketAcl.return_value = mock_acl_response

    # Versioning (desabilitado)
    mock_versioning_response_body = MagicMock()
    type(mock_versioning_response_body).status = PropertyMock(return_value=None) # Não configurado
    mock_versioning_response = MagicMock(spec=GetBucketVersioningResponse)
    type(mock_versioning_response).body = PropertyMock(return_value=mock_versioning_response_body)
    mock_obs_client.getBucketVersioning.return_value = mock_versioning_response

    # Logging (desabilitado)
    mock_logging_response_body = MagicMock() # Vazio significa desabilitado
    mock_logging_response = MagicMock(spec=GetBucketLoggingResponse)
    type(mock_logging_response).body = PropertyMock(return_value=mock_logging_response_body)
    mock_obs_client.getBucketLogging.return_value = mock_logging_response


    result: List[HuaweiOBSBucketData] = await huawei_obs_collector.get_huawei_obs_buckets(project_id="proj1", region_id="cn-north-1")

    assert len(result) == 1
    bucket_data = result[0]

    assert bucket_data.name == "test-bucket-1"
    assert bucket_data.location == "cn-north-1"
    assert bucket_data.creation_date == datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

    assert bucket_data.bucket_policy is not None
    assert bucket_data.bucket_policy.statement == []
    assert bucket_data.is_public_by_policy is False

    assert bucket_data.acl is not None
    assert bucket_data.acl.owner.id == "owner-id"
    assert bucket_data.acl.grants == []
    assert bucket_data.is_public_by_acl is False

    assert bucket_data.versioning is not None
    assert bucket_data.versioning.status is None # Não configurado

    assert bucket_data.logging is not None
    assert bucket_data.logging.enabled is False

    assert bucket_data.error_details is None
    mock_obs_client.getBucketPolicy.assert_called_once_with(bucketName="test-bucket-1")


@pytest.mark.asyncio
async def test_get_huawei_obs_buckets_policy_no_such_policy(mock_huawei_credentials_success, mock_obs_client):
    mock_bucket_info_native = Bucket(name="bucket-no-policy", creation_date="2023-01-01T00:00:00Z", location="reg1")
    mock_list_response_body = MagicMock()
    mock_list_response_body.buckets = [mock_bucket_info_native]
    mock_list_response = MagicMock(spec=ListBucketsResponse)
    type(mock_list_response).body = PropertyMock(return_value=mock_list_response_body)
    mock_obs_client.listBuckets.return_value = mock_list_response

    # Simular erro "NoSuchBucketPolicy"
    mock_obs_client.getBucketPolicy.side_effect = sdk_exceptions.ServiceResponseException(
        status_code=404, error_code="NoSuchBucketPolicy", error_message="Policy does not exist."
    )
    # Outras chamadas de detalhe retornam mocks vazios/padrão
    mock_acl_response_body = MagicMock(); mock_acl_response_body.owner = ObsOwner(id="oid"); mock_acl_response_body.grants = []
    mock_acl_response = MagicMock(spec=GetBucketAclResponse); type(mock_acl_response).body = PropertyMock(return_value=mock_acl_response_body)
    mock_obs_client.getBucketAcl.return_value = mock_acl_response
    mock_versioning_response_body = MagicMock(); type(mock_versioning_response_body).status = PropertyMock(return_value=None)
    mock_versioning_response = MagicMock(spec=GetBucketVersioningResponse); type(mock_versioning_response).body = PropertyMock(return_value=mock_versioning_response_body)
    mock_obs_client.getBucketVersioning.return_value = mock_versioning_response
    mock_logging_response_body = MagicMock()
    mock_logging_response = MagicMock(spec=GetBucketLoggingResponse); type(mock_logging_response).body = PropertyMock(return_value=mock_logging_response_body)
    mock_obs_client.getBucketLogging.return_value = mock_logging_response


    result = await huawei_obs_collector.get_huawei_obs_buckets(project_id="proj1", region_id="reg1")

    assert len(result) == 1
    bucket_data = result[0]
    assert bucket_data.name == "bucket-no-policy"
    assert bucket_data.bucket_policy is None # Política deve ser None
    assert bucket_data.is_public_by_policy is False # Default
    assert bucket_data.error_details is None # NoSuchBucketPolicy não é um erro de coleta, é um estado.

# Adicionar mais testes para:
# - Bucket público por política
# - Bucket público por ACL
# - Versionamento habilitado
# - Logging habilitado
# - Erros em outras chamadas de detalhe (ACL, Versioning, Logging)
# - Parse de diferentes formatos de Principal e Condition em políticas
# - Parse de diferentes formatos de Grantee em ACLs
# - Paginação se listBuckets for mockado para retornar múltiplos "pages" (mais complexo)
```

Ajustes feitos durante a escrita dos testes em `huawei_obs_collector.py`:
*   A função `_parse_obs_policy`: Adicionado tratamento para o caso de `policy_str` ser `None` e um log de erro mais detalhado para `json.JSONDecodeError`. Tratamento de exceção genérica adicionado.
*   A função `_parse_obs_acl`: Adicionado `getattr` para acesso mais seguro aos atributos do objeto `grant_native.grantee`, e tratamento de exceção genérico.
*   Na função `get_huawei_obs_buckets`:
    *   Melhorado o tratamento da resposta de `listBuckets`. O SDK pode retornar um único objeto `Bucket` ou uma lista. O código agora garante que `native_buckets` seja sempre uma lista.
    *   Ajustado o tratamento de exceção para `SdkException` para logar `error_code` e `error_message`.
    *   No loop de processamento de cada bucket, adicionado `getattr` para campos opcionais como `storage_class` e `description` para evitar `AttributeError` se não estiverem presentes na resposta da API para um bucket específico.
    *   O parse da `creation_date` foi melhorado para tentar múltiplos formatos (com e sem milissegundos).
    *   Para `getBucketPolicy`, se `policy_resp.body` for a string da política diretamente (em vez de um objeto com um atributo `policy`), o código tenta usá-lo.
    *   Para `getBucketVersioning`, se `status` não estiver presente, assume-se que não está configurado (`None`).
    *   Para `getBucketLogging`, verifica-se `target_bucket` ou `targetBucket` (nomes podem variar ligeiramente entre versões/docs do SDK) para determinar se o logging está habilitado.

Estes testes e ajustes fornecem uma base para o coletor OBS. A precisão do parse de políticas e ACLs, especialmente para identificar acesso público, dependerá da validação contra respostas reais da API Huawei Cloud.
