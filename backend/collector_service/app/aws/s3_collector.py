import boto3
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
from typing import List, Dict, Any
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Cache de cliente S3 por região para evitar recriação constante
s3_clients_cache = {}


def get_s3_client(region_name: str = None):
    target_region = region_name if region_name else settings.AWS_REGION_NAME
    if target_region not in s3_clients_cache:
        try:
            s3_clients_cache[target_region] = boto3.client(
                "s3", region_name=target_region
            )
        except (NoCredentialsError, PartialCredentialsError) as e:
            logger.error(
                f"AWS credentials not found or incomplete for region {target_region}: {e}"
            )
            raise
        except Exception as e:
            logger.error(f"Error creating S3 client for region {target_region}: {e}")
            raise
    return s3_clients_cache[target_region]


def list_s3_buckets() -> List[Dict[str, Any]]:
    """
    Lista todos os buckets S3 na conta.
    Retorna uma lista de dicionários, cada um contendo nome e data de criação do bucket.
    """
    s3_regional_client = get_s3_client(
        settings.AWS_REGION_NAME
    )  # ListBuckets é uma chamada global, usa o cliente default

    buckets_info = []
    try:
        response = s3_regional_client.list_buckets()
        for bucket in response.get("Buckets", []):
            bucket_name = bucket["Name"]
            creation_date = bucket["CreationDate"]

            # Para obter a região do bucket, precisamos de uma chamada adicional
            try:
                location_response = s3_regional_client.get_bucket_location(
                    Bucket=bucket_name
                )
                bucket_region = location_response.get("LocationConstraint")
                # LocationConstraint retorna None para us-east-1, ou a string da região para outras.
                if bucket_region is None:
                    bucket_region = "us-east-1"
            except ClientError as e:
                # Pode falhar para buckets em outras contas ou se não tiver permissão
                logger.warning(
                    f"Could not get location for bucket {bucket_name}: {e.response['Error']['Message']}"
                )
                bucket_region = "unknown"

            buckets_info.append(
                {
                    "name": bucket_name,
                    "creation_date": creation_date.isoformat(),
                    "region": bucket_region,
                }
            )
        return buckets_info
    except (NoCredentialsError, PartialCredentialsError) as e:
        logger.error(
            f"AWS credentials not configured correctly for S3 list_buckets: {e}"
        )
        return [{"error": "AWS credentials not configured."}]
    except ClientError as e:
        logger.error(
            f"ClientError listing S3 buckets: {e.response['Error']['Message']}"
        )
        return [{"error": f"ClientError: {e.response['Error']['Message']}"}]
    except Exception as e:
        logger.error(f"Unexpected error listing S3 buckets: {e}")
        return [{"error": "An unexpected error occurred."}]


def check_s3_bucket_acl(bucket_name: str, bucket_region: str) -> Dict[str, Any]:
    """
    Verifica as ACLs de um bucket S3 para identificar acesso público.
    Simplificado para MVP: verifica grants para AllUsers e AuthenticatedUsers.
    """
    s3_regional_client = get_s3_client(bucket_region)
    is_public_acl = False
    public_details = []

    try:
        acl = s3_regional_client.get_bucket_acl(Bucket=bucket_name)
        for grant in acl.get("Grants", []):
            grantee = grant.get("Grantee", {})
            grantee_type = grantee.get("Type")
            grantee_uri = grantee.get("URI")
            permission = grant.get("Permission")

            if grantee_type == "Group":
                if grantee_uri == "http://acs.amazonaws.com/groups/global/AllUsers":
                    is_public_acl = True
                    public_details.append(
                        f"Public (AllUsers) with permission: {permission}"
                    )
                elif (
                    grantee_uri
                    == "http://acs.amazonaws.com/groups/global/AuthenticatedUsers"
                ):
                    is_public_acl = True  # Consideramos AuthenticatedUsers como uma forma de público
                    public_details.append(
                        f"Public (AuthenticatedUsers) with permission: {permission}"
                    )

        return {
            "bucket_name": bucket_name,
            "is_public_by_acl": is_public_acl,
            "public_acl_details": (
                public_details if is_public_acl else "No direct public ACLs found."
            ),
        }

    except ClientError as e:
        # Handle cases como AccessDenied, NoSuchBucket
        error_code = e.response.get("Error", {}).get("Code")
        logger.warning(
            f"ClientError checking ACL for bucket {bucket_name} in region {bucket_region}: {error_code}"
        )
        return {
            "bucket_name": bucket_name,
            "is_public_by_acl": "Error",
            "public_acl_details": f"Could not check ACL: {error_code}",
        }
    except Exception as e:
        logger.error(
            f"Unexpected error checking ACL for bucket {bucket_name} in region {bucket_region}: {e}"
        )
        return {
            "bucket_name": bucket_name,
            "is_public_by_acl": "Error",
            "public_acl_details": "An unexpected error occurred during ACL check.",
        }


# Futuramente: check_s3_bucket_policy para analisar políticas de bucket
# def check_s3_bucket_policy(bucket_name: str, region: str) -> Dict[str, Any]:
#     pass


async def get_s3_data() -> List[Dict[str, Any]]:
    """
    Coleta dados de buckets S3, incluindo verificação de ACL.
    """
    collected_data = []
    buckets = list_s3_buckets()

    if buckets and "error" in buckets[0]:  # Checa se houve erro ao listar buckets
        return buckets  # Retorna a mensagem de erro

    for bucket_info in buckets:
        bucket_name = bucket_info["name"]
        bucket_region = bucket_info["region"]

        if bucket_region == "unknown":
            acl_data = {
                "bucket_name": bucket_name,
                "is_public_by_acl": "Unknown",
                "public_acl_details": "Could not determine bucket region to check ACL.",
            }
        else:
            # Para buckets em 'eu-central-1', por exemplo, o cliente S3 precisa ser dessa região
            # para get_bucket_acl funcionar corretamente sem redirecionamentos ou erros.
            acl_data = check_s3_bucket_acl(bucket_name, bucket_region)

        # Combina informações do bucket com dados da ACL
        # Adicionar mais verificações aqui (políticas, etc.) no futuro
        full_bucket_data = {**bucket_info, **acl_data}
        collected_data.append(full_bucket_data)

    return collected_data
