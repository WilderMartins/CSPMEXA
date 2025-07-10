from google.cloud import storage
from google.cloud.exceptions import NotFound, Forbidden, GoogleCloudError
from typing import List, Optional, Dict, Any
from app.schemas.gcp_storage import (
    GCPStorageBucketData, GCPBucketIAMPolicy, GCPBucketIAMBinding,
    GCPBucketVersioning, GCPBucketLogging, GCPBucketWebsite, GCPBucketRetentionPolicy
)
from app.gcp.gcp_client_manager import get_storage_client, get_gcp_project_id
import logging

logger = logging.getLogger(__name__)

def _parse_iam_policy(iam_policy_native: Any) -> Optional[GCPBucketIAMPolicy]:
    """Converte o objeto IAMPolicy nativo do GCP para o schema Pydantic."""
    if not iam_policy_native:
        return None

    bindings_data = []
    for binding in iam_policy_native.bindings:
        bindings_data.append(GCPBucketIAMBinding(
            role=binding.get("role"),
            members=list(binding.get("members", [])), # Garantir que seja uma lista
            condition=binding.get("condition")
        ))
    return GCPBucketIAMPolicy(
        version=iam_policy_native.version,
        bindings=bindings_data,
        etag=iam_policy_native.etag
    )

def _check_iam_public_access(iam_policy: Optional[GCPBucketIAMPolicy]) -> (bool, List[str]):
    """Verifica se a política IAM do bucket concede acesso público."""
    if not iam_policy or not iam_policy.bindings:
        return False, []

    is_public = False
    public_details = []
    public_members = ["allUsers", "allAuthenticatedUsers"]

    for binding in iam_policy.bindings:
        # Simplificação: considera público se qualquer membro público tiver qualquer papel.
        # Uma análise mais granular verificaria os papéis (ex: apenas objectViewer vs objectCreator/Admin).
        has_public_member = any(member in binding.members for member in public_members)
        if has_public_member:
            is_public = True
            public_details.append(f"Role '{binding.role}' granted to public members: {', '.join(m for m in binding.members if m in public_members)}")
            # Não precisa de break, pode haver múltiplas bindings públicas.

    return is_public, public_details


async def get_gcp_storage_buckets(project_id: Optional[str] = None) -> List[GCPStorageBucketData]:
    """
    Coleta dados de configuração de Google Cloud Storage buckets para um projeto.
    """
    actual_project_id = project_id or get_gcp_project_id()
    if not actual_project_id:
        logger.error("GCP Project ID is required but could not be determined.")
        # Retornar um erro ou uma lista vazia com um item de erro?
        # Para consistência com AWS, levantar exceção ou retornar objeto de erro.
        # Por enquanto, lista vazia e log. O controller pode levantar HTTPEx.
        return [GCPStorageBucketData( # Criar um item de erro
            id="ERROR_PROJECT_ID_MISSING",
            name="ERROR_PROJECT_ID_MISSING",
            location="global", storage_class="N/A", time_created=datetime.now(), updated=datetime.now(),
            error_details="GCP Project ID is required for collecting storage buckets but was not provided or found."
        )]

    try:
        storage_client = get_storage_client(project=actual_project_id)
        gcp_buckets_native = storage_client.list_buckets(project=actual_project_id) # Iterador
    except GoogleCloudError as e:
        logger.error(f"Failed to list GCP Storage buckets for project {actual_project_id}: {e}")
        return [GCPStorageBucketData(
            id=f"ERROR_LIST_BUCKETS_{actual_project_id}", name=f"ERROR_LIST_BUCKETS_{actual_project_id}",
            location="global", storage_class="N/A", time_created=datetime.now(), updated=datetime.now(),
            error_details=f"Failed to list GCP Storage buckets: {str(e)}"
        )]
    except Exception as e: # Captura outras exceções de inicialização do cliente
        logger.error(f"Unexpected error initializing storage client or listing buckets for project {actual_project_id}: {e}")
        return [GCPStorageBucketData(
            id=f"ERROR_INIT_BUCKETS_{actual_project_id}", name=f"ERROR_INIT_BUCKETS_{actual_project_id}",
            location="global", storage_class="N/A", time_created=datetime.now(), updated=datetime.now(),
            error_details=f"Unexpected error listing GCP Storage buckets: {str(e)}"
        )]

    collected_buckets: List[GCPStorageBucketData] = []

    for bucket_native in gcp_buckets_native:
        bucket_name = bucket_native.name
        error_msg_bucket = []
        iam_policy_data = None
        versioning_data = None
        logging_data = None
        website_data = None
        retention_data = None
        is_public_iam = False
        public_iam_details_list = []

        try:
            # Obter IAM Policy
            try:
                iam_policy_native = bucket_native.get_iam_policy(requested_policy_version=3)
                iam_policy_data = _parse_iam_policy(iam_policy_native)
                if iam_policy_data:
                    is_public_iam, public_iam_details_list = _check_iam_public_access(iam_policy_data)
            except Forbidden as e:
                logger.warning(f"Forbidden to get IAM policy for bucket {bucket_name} in project {actual_project_id}: {e}")
                error_msg_bucket.append(f"IAM policy fetch forbidden: {str(e)}")
            except GoogleCloudError as e:
                logger.warning(f"Error getting IAM policy for bucket {bucket_name}: {e}")
                error_msg_bucket.append(f"IAM policy fetch error: {str(e)}")

            # Obter Versioning
            versioning_data = GCPBucketVersioning(enabled=bucket_native.versioning_enabled)

            # Obter Logging
            if bucket_native.logging: # logging é um dict ou None
                 logging_data = GCPBucketLogging(
                    log_bucket=bucket_native.logging.get('logBucket'),
                    log_object_prefix=bucket_native.logging.get('logObjectPrefix')
                )
            else:
                logging_data = GCPBucketLogging(log_bucket=None, log_object_prefix=None)


            # Obter Website Configuration
            if bucket_native.website: # website é um dict ou None
                website_data = GCPBucketWebsite(
                    main_page_suffix=bucket_native.website.get('mainPageSuffix'),
                    not_found_page=bucket_native.website.get('notFoundPage')
                )

            # Obter Retention Policy
            if bucket_native.retention_policy: # É um objeto RetentionPolicy ou None
                rp_native = bucket_native.retention_policy
                retention_data = GCPBucketRetentionPolicy(
                    retention_period=rp_native.get("retentionPeriod"), # Em segundos
                    effective_time=rp_native.get("effectiveTime"),
                    is_locked=rp_native.get("isLocked")
                )

            # ACLs (Legado) - Opcional, IAM uniforme é preferível
            # acl_data = None
            # try:
            #     acl_native = bucket_native.acl # Isso é um BucketACL object
            #     # acl_native.reload() # Para garantir que está fresco
            #     # acl_items = [GCPBucketACLEntity(entity=entry['entity'], role=entry['role']) for entry in acl_native]
            #     # acl_data = GCPBucketACL(items=acl_items)
            #     # is_public_acl, public_acl_details_list = _check_acl_public_access(acl_data)
            # except Exception as e:
            #     logger.warning(f"Error getting ACLs for bucket {bucket_name}: {e}")
            #     error_msg_bucket.append(f"ACL fetch error: {str(e)}")


            bucket_data = GCPStorageBucketData(
                id=bucket_native.id or bucket_name, # id pode ser None em alguns casos de mock/list
                name=bucket_name,
                project_number=str(bucket_native.project_number) if bucket_native.project_number else None,
                location=bucket_native.location,
                storageClass=bucket_native.storage_class, # Usando alias
                timeCreated=bucket_native.time_created, # Usando alias
                updated=bucket_native.updated,
                iam_policy=iam_policy_data,
                versioning=versioning_data,
                logging=logging_data,
                website=website_data, # Usando alias
                retentionPolicy=retention_data, # Usando alias
                is_public_by_iam=is_public_iam,
                public_iam_details=public_iam_details_list,
                labels=dict(bucket_native.labels) if bucket_native.labels else None,
                error_details="; ".join(error_msg_bucket) if error_msg_bucket else None
            )
            collected_buckets.append(bucket_data)

        except Exception as e_bucket:
            logger.error(f"Unexpected error processing bucket {bucket_name} in project {actual_project_id}: {e_bucket}", exc_info=True)
            collected_buckets.append(GCPStorageBucketData(
                id=bucket_name, name=bucket_name,
                location="unknown", storage_class="N/A", time_created=datetime.now(), updated=datetime.now(),
                error_details=f"Failed to process bucket details: {str(e_bucket)}"
            ))

    logger.info(f"Collected {len(collected_buckets)} GCP Storage buckets for project {actual_project_id}.")
    return collected_buckets
