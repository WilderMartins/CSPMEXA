import boto3
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
from typing import List, Dict, Any, Optional
from app.core.config import settings
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
            aws_session_token=credentials.get('aws_session_token')
        )
    except (NoCredentialsError, PartialCredentialsError) as e:
        raise HTTPException(status_code=403, detail=f"Credenciais AWS inválidas ou incompletas: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao criar cliente AWS: {e}")

def parse_acl(acl_response: Dict[str, Any], bucket_name: str) -> S3BucketACLDetails:
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

        if grantee.type == "Group" and (grantee.uri == "http://acs.amazonaws.com/groups/global/AllUsers" or grantee.uri == "http://acs.amazonaws.com/groups/global/AuthenticatedUsers"):
            is_public = True
            public_details.append(f"Public access via {grantee.type} with permission: {grant_data.get('Permission')}")

    return S3BucketACLDetails(
        owner_display_name=acl_response.get("Owner", {}).get("DisplayName"),
        owner_id=acl_response.get("Owner", {}).get("ID"),
        grants=grants_data,
        is_public=is_public,
        public_details=public_details,
    )

def check_policy_for_public_access(policy_document: Dict[str, Any]) -> bool:
    if not policy_document or "Statement" not in policy_document:
        return False
    for statement in policy_document["Statement"]:
        if statement.get("Effect") == "Allow" and statement.get("Principal") == "*":
            if not statement.get("Condition"):
                return True
    return False

async def get_s3_data(credentials: Dict[str, Any]) -> List[S3BucketData]:
    """
    Ponto de entrada principal para coletar dados de S3 usando as credenciais fornecidas.
    """
    logger.info("Iniciando coleta de dados S3.")
    collected_data: List[S3BucketData] = []
    s3_global_client = get_boto3_client("s3", settings.AWS_REGION_NAME, credentials)

    try:
        response = s3_global_client.list_buckets()
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar buckets S3: {e.response['Error']['Message']}")

    for bucket in response.get("Buckets", []):
        bucket_name = bucket["Name"]
        creation_date = bucket.get("CreationDate")
        bucket_region = None
        error_message = ""

        try:
            location_response = s3_global_client.get_bucket_location(Bucket=bucket_name)
            bucket_region = location_response.get("LocationConstraint") or "us-east-1"
            s3_regional_client = get_boto3_client("s3", bucket_region, credentials)

            # Coleta de detalhes
            acl_details = None
            try:
                acl_response = s3_regional_client.get_bucket_acl(Bucket=bucket_name)
                acl_details = parse_acl(acl_response, bucket_name)
            except ClientError as e:
                error_message += f"ACL fetch failed: {e.response['Error']['Message']}; "

            # ... (Lógica para policy, versioning, etc. aqui) ...

        except Exception as e_bucket_level:
            error_message += f"Unexpected processing error: {str(e_bucket_level)}"

        bucket_data = S3BucketData(
            name=bucket_name,
            creation_date=creation_date,
            region=bucket_region or "unknown",
            acl=acl_details,
            # ... (outros campos) ...
            error_details=error_message.strip() if error_message else None,
        )
        collected_data.append(bucket_data)

    return collected_data

async def remediate_public_acl(credentials: Dict[str, Any], bucket_name: str, region: str) -> Dict[str, Any]:
    """
    Aplica a ACL 'private' a um bucket S3 para remover o acesso público.
    """
    logger.info(f"Tentando remediar ACL pública para o bucket '{bucket_name}' na região '{region}'.")
    s3_client = get_boto3_client("s3", region, credentials)
    try:
        s3_client.put_bucket_acl(Bucket=bucket_name, ACL='private')
        logger.info(f"ACL 'private' aplicada com sucesso ao bucket '{bucket_name}'.")
        return {"status": "success", "message": f"ACL do bucket '{bucket_name}' definida como privada."}
    except ClientError as e:
        logger.error(f"Erro ao tentar remediar o bucket '{bucket_name}': {e.response['Error']['Message']}")
        raise HTTPException(status_code=500, detail=f"Erro ao aplicar ACL privada: {e.response['Error']['Message']}")
