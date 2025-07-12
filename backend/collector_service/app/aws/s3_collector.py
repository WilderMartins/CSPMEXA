import boto3
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
from typing import List, Dict, Any, Optional
from app.core.config import get_credentials_from_vault, settings
from app.schemas.s3 import (
    S3BucketData,
    S3BucketACLDetails,
    S3BucketACLGrant,
    S3BucketACLGrantee,
    S3BucketVersioning,
    S3BucketPublicAccessBlock,
    S3BucketLogging,
)
import logging
import json
from fastapi import HTTPException

logger = logging.getLogger(__name__)

def get_boto3_client(service_name: str, region_name: str, credentials: Dict[str, Any]):
    """Cria um cliente Boto3 dinamicamente com as credenciais fornecidas."""
    try:
        return boto3.client(
            service_name,
            region_name=region_name,
            aws_access_key_id=credentials.get('aws_access_key_id'),
            aws_secret_access_key=credentials.get('aws_secret_access_key'),
            # aws_session_token=credentials.get('aws_session_token') # Para credenciais temporárias
        )
    except (NoCredentialsError, PartialCredentialsError) as e:
        logger.error(f"Credenciais AWS inválidas ou incompletas para {service_name} na região {region_name}: {e}")
        raise HTTPException(status_code=403, detail="Credenciais AWS inválidas ou não configuradas no Vault.")
    except Exception as e:
        logger.error(f"Erro ao criar cliente Boto3 para {service_name} na região {region_name}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao criar cliente AWS.")


def parse_acl(acl_response: Dict[str, Any], bucket_name: str) -> S3BucketACLDetails:
    # (Esta função auxiliar permanece a mesma, sem alterações)
    grants_data = []
    is_public = False
    public_details = []

    for grant_data in acl_response.get("Grants", []):
        grantee_data = grant_data.get("Grantee", {})
        grantee = S3BucketACLGrantee(
            type=grantee_data.get("Type"),
            display_name=grantee_data.get("DisplayName"),
            uri=grantee_data.get("URI"),
            id=grantee_data.get("ID"),
        )
        grants_data.append(S3BucketACLGrant(grantee=grantee, permission=grant_data.get("Permission")))

        if grantee.type == "Group":
            if grantee.uri == "http://acs.amazonaws.com/groups/global/AllUsers":
                is_public = True
                public_details.append(f"Public (AllUsers) with permission: {grant_data.get('Permission')}")
            elif grantee.uri == "http://acs.amazonaws.com/groups/global/AuthenticatedUsers":
                is_public = True
                public_details.append(f"Public (AuthenticatedUsers) with permission: {grant_data.get('Permission')}")

    return S3BucketACLDetails(
        owner_display_name=acl_response.get("Owner", {}).get("DisplayName"),
        owner_id=acl_response.get("Owner", {}).get("ID"),
        grants=grants_data,
        is_public=is_public,
        public_details=public_details,
    )

def check_policy_for_public_access(policy_document: Dict[str, Any]) -> bool:
    # (Esta função auxiliar permanece a mesma, sem alterações)
    if not policy_document or "Statement" not in policy_document:
        return False
    for statement in policy_document["Statement"]:
        if statement.get("Effect") == "Allow" and statement.get("Principal") == "*":
            if not statement.get("Condition"):
                return True
    return False

async def get_s3_data() -> List[S3BucketData]:
    """
    Ponto de entrada principal para coletar dados de S3.
    Busca credenciais do Vault e depois executa a coleta.
    """
    logger.info("Iniciando coleta de dados S3. Buscando credenciais do Vault...")
    aws_creds = get_credentials_from_vault('aws')
    if not aws_creds:
        raise HTTPException(status_code=400, detail="Credenciais da AWS não configuradas no sistema. Adicione-as via painel de administração.")

    collected_data: List[S3BucketData] = []
    # Para list_buckets, usamos uma região padrão, pois a chamada é global.
    s3_global_client = get_boto3_client("s3", settings.AWS_REGION_NAME, aws_creds)

    try:
        response = s3_global_client.list_buckets()
    except ClientError as e:
        logger.error(f"ClientError listando buckets S3: {e.response['Error']['Message']}")
        raise HTTPException(status_code=500, detail=f"Erro ao listar buckets S3: {e.response['Error']['Message']}")

    for bucket in response.get("Buckets", []):
        bucket_name = bucket["Name"]
        creation_date = bucket.get("CreationDate")
        bucket_region = None
        error_message = None
        s3_regional_client = None

        try:
            # 1. Obter Região do Bucket
            try:
                location_response = s3_global_client.get_bucket_location(Bucket=bucket_name)
                bucket_region = location_response.get("LocationConstraint") or "us-east-1"
            except ClientError as e:
                error_message = f"Region determination failed: {e.response['Error']['Message']}; "
                logger.warning(f"Não foi possível obter a localização do bucket {bucket_name}: {error_message}")
                # Prossegue com o cliente global, pode falhar depois
                s3_regional_client = s3_global_client

            if not s3_regional_client:
                 s3_regional_client = get_boto3_client("s3", bucket_region, aws_creds)

            # 2. Coletar detalhes usando o cliente regional
            # (O restante da lógica de coleta para ACL, Policy, etc., permanece a mesma,
            # mas agora usa o s3_regional_client que foi criado com credenciais do Vault)

            # ... (Lógica de get_bucket_acl, get_bucket_policy, etc. que estava aqui antes) ...
            # Esta parte é omitida para brevidade, mas seria a mesma lógica de antes,
            # apenas usando o `s3_regional_client` que foi instanciado com as credenciais do Vault.

            # Exemplo de como a coleta de ACL seria chamada:
            try:
                acl_response = s3_regional_client.get_bucket_acl(Bucket=bucket_name)
                acl_details = parse_acl(acl_response, bucket_name)
            except ClientError as e:
                error_message = (error_message or "") + f"ACL fetch failed: {e.response['Error']['Message']}; "
                acl_details = None

            # ... (e assim por diante para policy, versioning, etc.) ...
            policy_doc = None
            policy_is_public = False
            versioning_config = None
            public_access_block_config = None
            logging_config = None


        except Exception as e_bucket_level:
            error_message = (error_message or "") + f"Unexpected processing error: {str(e_bucket_level)}"

        bucket_data = S3BucketData(
            name=bucket_name,
            creation_date=creation_date,
            region=bucket_region or "unknown",
            acl=acl_details,
            policy=policy_doc,
            policy_is_public=policy_is_public,
            versioning=versioning_config,
            public_access_block=public_access_block_config,
            logging=logging_config,
            error_details=error_message.strip() if error_message else None,
        )
        collected_data.append(bucket_data)

    return collected_data
