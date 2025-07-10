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

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Cache de cliente S3 por região para evitar recriação constante
s3_clients_cache = {}


def get_s3_client(region_name: str = None):
    target_region = region_name if region_name else settings.AWS_REGION_NAME
    if target_region not in s3_clients_cache:
        try:
            # Para list_buckets e get_bucket_location, um cliente global (ex: us-east-1) pode ser usado.
            # No entanto, para operações específicas de bucket como get_bucket_acl, get_bucket_policy, etc.,
            # o cliente DEVE ser configurado para a região do bucket.
            # Este get_s3_client será usado para chamadas globais ou quando a região do bucket é desconhecida.
            # Clientes específicos da região do bucket serão criados dinamicamente nas funções.
            s3_clients_cache[target_region] = boto3.client("s3", region_name=target_region)
            # Adicionalmente, um cliente S3 "global" para list_buckets, que não requer uma região específica
            # ou pode usar a região padrão. Boto3 lida com isso se region_name for None para list_buckets.
            if "global" not in s3_clients_cache:
                 s3_clients_cache["global"] = boto3.client("s3", region_name=settings.AWS_REGION_NAME)

        except (NoCredentialsError, PartialCredentialsError) as e:
            logger.error(f"AWS credentials not found or incomplete for region {target_region}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error creating S3 client for region {target_region}: {e}")
            raise
    return s3_clients_cache[target_region]


def get_bucket_specific_s3_client(bucket_region: str):
    """Retorna um cliente S3 para a região específica do bucket."""
    if not bucket_region: # Pode acontecer se get_bucket_location falhar
        logger.warning("Bucket region is unknown, using default client. Operations may fail.")
        return get_s3_client(settings.AWS_REGION_NAME) # Fallback para o cliente da região padrão

    if bucket_region not in s3_clients_cache:
        try:
            s3_clients_cache[bucket_region] = boto3.client("s3", region_name=bucket_region)
        except Exception as e: # Captura qualquer exceção durante a criação do cliente
            logger.error(f"Failed to create S3 client for region {bucket_region}: {e}")
            # Fallback para um cliente genérico se a criação específica da região falhar,
            # embora isso possa levar a erros de 'permanent redirect' ou 'authorization header is malformed'.
            return get_s3_client(settings.AWS_REGION_NAME)
    return s3_clients_cache[bucket_region]


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

        if grantee.type == "Group":
            if grantee.uri == "http://acs.amazonaws.com/groups/global/AllUsers":
                is_public = True
                public_details.append(f"Public (AllUsers) with permission: {grant_data.get('Permission')}")
            elif grantee.uri == "http://acs.amazonaws.com/groups/global/AuthenticatedUsers":
                is_public = True # Consideramos AuthenticatedUsers como uma forma de público
                public_details.append(f"Public (AuthenticatedUsers) with permission: {grant_data.get('Permission')}")

    return S3BucketACLDetails(
        owner_display_name=acl_response.get("Owner", {}).get("DisplayName"),
        owner_id=acl_response.get("Owner", {}).get("ID"),
        grants=grants_data,
        is_public=is_public,
        public_details=public_details,
    )

def check_policy_for_public_access(policy_document: Dict[str, Any]) -> bool:
    """
    Analisa uma política de bucket S3 para determinar se ela concede acesso público.
    Verifica por declarações que permitem acesso a '*' ou a um Principal AWS anônimo/público.
    """
    if not policy_document or "Statement" not in policy_document:
        return False

    for statement in policy_document["Statement"]:
        effect = statement.get("Effect")
        principal = statement.get("Principal")
        action = statement.get("Action")
        condition = statement.get("Condition", None) # Condições podem restringir o acesso público

        if effect == "Allow":
            # Checa por Principal público
            if principal == "*":
                # Se houver uma condição, a política pode não ser verdadeiramente pública.
                # Esta é uma simplificação; uma análise de condição mais profunda é complexa.
                # Por agora, se Principal é '*' e há uma condição, assumimos que não é publicamente aberto sem restrições.
                # Uma melhoria seria analisar as condições (ex: aws:SourceIp, aws:SourceArn).
                if condition:
                    # logger.debug(f"Policy for bucket has Allow for Principal='*' but with Condition: {condition}")
                    # Poderíamos tentar analisar algumas condições comuns aqui.
                    # Por enquanto, vamos ser conservadores e dizer que não é "abertamente" público se houver condição.
                    continue # Para este MVP, uma condição em um Principal '*' não será marcada como pública.
                return True

            if isinstance(principal, dict) and principal.get("AWS") == "*":
                 if condition:
                    continue
                 return True

            # Checa por um grupo específico de usuários anônimos (menos comum, mas possível)
            # Ex: "Principal": {"CanonicalUser": "ID-DO-USUARIO-ANONIMO-ESPECIFICO"}
            # Esta parte é mais complexa e geralmente não é a principal preocupação para "público".

    return False


async def get_s3_data() -> List[S3BucketData]:
    collected_data: List[S3BucketData] = []
    s3_global_client = get_s3_client("global") # Cliente para list_buckets

    try:
        response = s3_global_client.list_buckets()
    except (NoCredentialsError, PartialCredentialsError) as e:
        logger.error(f"AWS credentials not configured correctly for S3 list_buckets: {e}")
        # No caso de erro de credencial global, não podemos prosseguir.
        # O controller deve capturar isso e retornar um erro HTTP apropriado.
        raise HTTPException(status_code=500, detail="AWS credentials not configured.") from e
    except ClientError as e:
        logger.error(f"ClientError listing S3 buckets: {e.response['Error']['Message']}")
        raise HTTPException(status_code=500, detail=f"ClientError listing S3 buckets: {e.response['Error']['Message']}") from e
    except Exception as e: # Captura outras exceções inesperadas
        logger.error(f"Unexpected error listing S3 buckets: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while listing S3 buckets: {str(e)}") from e

    for bucket in response.get("Buckets", []):
        bucket_name = bucket["Name"]
        creation_date = bucket.get("CreationDate")
        bucket_region = None
        acl_details = None
        policy_doc = None
        policy_is_public = None
        versioning_config = None
        public_access_block_config = None
        logging_config = None
        error_message = None

        try:
            # 1. Obter Região do Bucket
            try:
                location_response = s3_global_client.get_bucket_location(Bucket=bucket_name)
                bucket_region = location_response.get("LocationConstraint")
                if bucket_region is None: # us-east-1 retorna None
                    bucket_region = "us-east-1"
            except ClientError as e:
                logger.warning(f"Could not get location for bucket {bucket_name}: {e.response['Error']['Message']}. Using default region.")
                bucket_region = settings.AWS_REGION_NAME # Fallback, mas pode não ser correto
                error_message = f"Region determination failed: {e.response['Error']['Message']}; "


            s3_regional_client = get_bucket_specific_s3_client(bucket_region)

            # 2. Obter ACL do Bucket
            try:
                acl_response = s3_regional_client.get_bucket_acl(Bucket=bucket_name)
                acl_details = parse_acl(acl_response, bucket_name)
            except ClientError as e:
                logger.warning(f"Could not get ACL for bucket {bucket_name} in region {bucket_region}: {e.response['Error']['Message']}")
                error_message += f"ACL fetch failed: {e.response['Error']['Message']}; "
                acl_details = S3BucketACLDetails(is_public=False, public_details=[f"Error fetching ACL: {e.response['Error']['Message']}"])


            # 3. Obter Política do Bucket
            try:
                policy_response = s3_regional_client.get_bucket_policy(Bucket=bucket_name)
                policy_doc = json.loads(policy_response["Policy"])
                policy_is_public = check_policy_for_public_access(policy_doc)
            except ClientError as e:
                if e.response["Error"]["Code"] == "NoSuchBucketPolicy":
                    policy_doc = None
                    policy_is_public = False
                else:
                    logger.warning(f"Could not get policy for bucket {bucket_name}: {e.response['Error']['Message']}")
                    error_message += f"Policy fetch failed: {e.response['Error']['Message']}; "
                    policy_is_public = None # Indeterminado
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding policy for bucket {bucket_name}: {e}")
                error_message += f"Policy JSON decode error; "
                policy_is_public = None


            # 4. Obter Configuração de Versionamento
            try:
                versioning_response = s3_regional_client.get_bucket_versioning(Bucket=bucket_name)
                versioning_config = S3BucketVersioning(
                    status=versioning_response.get("Status", "NotConfigured"), # Pode não haver 'Status' se nunca ativado
                    mfa_delete=versioning_response.get("MFADelete")
                )
            except ClientError as e:
                logger.warning(f"Could not get versioning for bucket {bucket_name}: {e.response['Error']['Message']}")
                error_message += f"Versioning fetch failed: {e.response['Error']['Message']}; "

            # 5. Obter Configuração de Bloqueio de Acesso Público
            try:
                pab_response = s3_regional_client.get_public_access_block(Bucket=bucket_name)
                public_access_block_config = S3BucketPublicAccessBlock(
                    **pab_response.get("PublicAccessBlockConfiguration", {})
                )
            except ClientError as e:
                # Se não houver PublicAccessBlock configurado, a API retorna 'NoSuchPublicAccessBlockConfiguration'.
                # Isso significa que os padrões (geralmente tudo false) são aplicados.
                if e.response["Error"]["Code"] == "NoSuchPublicAccessBlockConfiguration":
                     public_access_block_config = S3BucketPublicAccessBlock(
                        BlockPublicAcls=False,
                        IgnorePublicAcls=False,
                        BlockPublicPolicy=False,
                        RestrictPublicBuckets=False
                    )
                else:
                    logger.warning(f"Could not get public access block for bucket {bucket_name}: {e.response['Error']['Message']}")
                    error_message += f"Public Access Block fetch failed: {e.response['Error']['Message']}; "

            # 6. Obter Configuração de Logging
            try:
                logging_response = s3_regional_client.get_bucket_logging(Bucket=bucket_name)
                if logging_response.get("LoggingEnabled"):
                    logging_config = S3BucketLogging(
                        enabled=True,
                        target_bucket=logging_response["LoggingEnabled"].get("TargetBucket"),
                        target_prefix=logging_response["LoggingEnabled"].get("TargetPrefix")
                    )
                else:
                    logging_config = S3BucketLogging(enabled=False)
            except ClientError as e:
                logger.warning(f"Could not get logging for bucket {bucket_name}: {e.response['Error']['Message']}")
                error_message += f"Logging fetch failed: {e.response['Error']['Message']}; "


        except Exception as e_bucket_level:
            # Captura qualquer outra exceção inesperada durante o processamento deste bucket
            logger.error(f"Unexpected error processing bucket {bucket_name}: {e_bucket_level}")
            if error_message:
                error_message += f"Unexpected processing error: {str(e_bucket_level)}"
            else:
                error_message = f"Unexpected processing error: {str(e_bucket_level)}"

        bucket_data = S3BucketData(
            name=bucket_name,
            creation_date=creation_date,
            region=bucket_region or "unknown", # Garante que a região não seja None
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

# Import HTTPException para ser usado em caso de erros globais que impedem a coleta
from fastapi import HTTPException
