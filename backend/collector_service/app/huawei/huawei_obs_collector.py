# from huaweicloudsdkobs.v1.model import ListBucketsRequest, GetBucketPolicyRequest, GetBucketAclRequest, GetBucketVersioningRequest, GetBucketLoggingRequest
# Acima removido pois os métodos do cliente são usados diretamente.
# ListBucketsRequest pode ser necessário se listBuckets() o exigir, mas parece que não.
from huaweicloudsdkobs.v1.model import ListBucketsResponse # Para mock de tipo de resposta
from huaweicloudsdkcore.exceptions import exceptions as sdk_exceptions
from typing import List, Optional, Dict, Any
from app.schemas.huawei_obs import (
    HuaweiOBSBucketData, HuaweiOBSBucketPolicy, HuaweiOBSBucketPolicyStatement,
    HuaweiOBSBucketACL, HuaweiOBSGrant, HuaweiOBSGrantee, HuaweiOBSOwner,
    HuaweiOBSBucketVersioning, HuaweiOBSBucketLogging
)
from app.huawei.huawei_client_manager import get_obs_client, get_huawei_credentials
import logging
import json # Para parsear políticas se vierem como string JSON
from datetime import datetime # Para creation_date

logger = logging.getLogger(__name__)

def _parse_obs_policy(policy_str: Optional[str]) -> Optional[HuaweiOBSBucketPolicy]:
    if not policy_str:
        return None
    try:
        policy_dict = json.loads(policy_str)
        statements_data = []
        for stmt_dict in policy_dict.get("Statement", []):
            # A estrutura de Principal e Condition pode variar. Este é um parse genérico.
            # O SDK pode já retornar objetos mais estruturados.
            statements_data.append(HuaweiOBSBucketPolicyStatement(
                Sid=stmt_dict.get("Sid"),
                Effect=stmt_dict.get("Effect"),
                Principal=stmt_dict.get("Principal"), # Pode precisar de parse mais profundo
                Action=stmt_dict.get("Action"),
                Resource=stmt_dict.get("Resource"),
                Condition=stmt_dict.get("Condition") # Pode precisar de parse mais profundo
            ))
        return HuaweiOBSBucketPolicy(
            Version=policy_dict.get("Version"),
            Statement=statements_data
        )
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding OBS bucket policy JSON: {e}. Policy string: {policy_str[:200]}")
        return None
    except Exception as e:
        logger.error(f"Error parsing OBS bucket policy object: {e}")
        return None

def _check_obs_policy_public_access(policy: Optional[HuaweiOBSBucketPolicy]) -> (bool, List[str]):
    if not policy or not policy.statement:
        return False, []

    is_public = False
    public_details = []
    # Na Huawei, "Principal: {"HUAWEI": ["*"]}" ou "Principal: {"OBS": {"CanonicalUser": ["Everyone"]}}" (ou similar) indicaria público.
    # "Everyone" pode ter um ID canônico específico ou URI. Precisa verificar a documentação.
    # Por agora, vamos focar em Principal: "*" ou Principal: {"HUAWEI": ["*"]} como um indicador genérico.

    for stmt in policy.statement:
        if stmt.effect == "Allow":
            principal = stmt.principal
            is_principal_star = False
            if isinstance(principal, str) and principal == "*":
                is_principal_star = True
            elif isinstance(principal, dict):
                if "*" in principal.get("HUAWEI", []) or "*" in principal.get("AWS", []): # Huawei pode usar "AWS" para compatibilidade S3
                    is_principal_star = True
                # Checar por IDs canônicos de grupos públicos se conhecidos
                # Ex: if "id-for-everyone" in principal.get("CanonicalUser", []): is_principal_star = True

            if is_principal_star:
                # Simplificação: se Principal é '*' e não há Condition forte, considera-se público.
                # Uma análise de Condition seria necessária para maior precisão.
                if not stmt.condition: # Se não há condição, é definitivamente público
                    is_public = True
                    public_details.append(f"Statement '{stmt.sid or 'N/A'}' allows public access (Principal: {principal}) for actions: {stmt.action}.")
                else:
                    # Com condição, é mais complexo. Para MVP, podemos ser conservadores.
                    # Ou, se a política é para GetObject e Principal é *, é um forte candidato.
                    public_details.append(f"Statement '{stmt.sid or 'N/A'}' allows public-like access (Principal: {principal}) with conditions for actions: {stmt.action}. Review conditions: {stmt.condition}")
                    # Não marcar is_public = True automaticamente se houver condição, mas logar/detalhar.
                    # Para este CSPM, vamos marcar como potencialmente público e deixar a revisão manual.
                    is_public = True # Temporariamente, para garantir que seja sinalizado.

    return is_public, public_details


def _parse_obs_acl(acl_native: Any) -> Optional[HuaweiOBSBucketACL]:
    if not acl_native:
        return None
    try:
        owner_data = HuaweiOBSOwner(ID=acl_native.owner.id) # Assumindo que acl_native.owner.id existe
        grants_data = []
        if hasattr(acl_native, 'grants') and acl_native.grants: # grants pode ser 'Grant'
            for grant_native in acl_native.grants:
                grantee_data = HuaweiOBSGrantee(
                    ID=getattr(grant_native.grantee, 'id', None), # Usar getattr para segurança
                    URI=getattr(grant_native.grantee, 'uri', None)
                )
                grants_data.append(HuaweiOBSGrant(grantee=grantee_data, permission=grant_native.permission))

        return HuaweiOBSBucketACL(owner=owner_data, grants=grants_data) # grants pode ser 'Grant'
    except Exception as e:
        logger.error(f"Error parsing OBS ACL object: {e}", exc_info=True)
        return None

def _check_obs_acl_public_access(acl: Optional[HuaweiOBSBucketACL]) -> (bool, List[str]):
    if not acl or not acl.grants:
        return False, []

    is_public = False
    public_details = []
    # URIs/IDs para grupos públicos na Huawei (ex: Everyone, AuthenticatedUsers) precisam ser confirmados.
    # Exemplo S3: "http://acs.amazonaws.com/groups/global/AllUsers"
    # Exemplo S3: "http://acs.amazonaws.com/groups/global/AuthenticatedUsers"
    # Na Huawei, o grupo "Everyone" (todos os usuários) é representado pelo ID de domínio "Domain Others".
    # O SDK pode traduzir isso para um URI ou um ID específico.
    # Vamos procurar por grantee.uri conhecidos ou grantee.id específicos se documentados.
    # Por enquanto, uma heurística:
    public_grantee_identifiers = [
        "http://obs.myhuaweicloud.com/grantees/Everyone", # Exemplo hipotético, verificar URI correto
        # Ou um ID canônico específico para "Everyone"
    ]

    for grant in acl.grants:
        grantee_id = grant.grantee.id
        grantee_uri = grant.grantee.uri
        permission = grant.permission

        # Checar por URIs públicos conhecidos
        if grantee_uri in public_grantee_identifiers:
            is_public = True
            public_details.append(f"Public access via URI '{grantee_uri}' with permission '{permission}'.")

        # Checar por ID de domínio para "Everyone" (OBS: "Others" ou "Domain Others")
        # O ID canônico para o grupo "Everyone" (todos os usuários) é um ID de domínio especial.
        # Se o SDK expõe isso como um ID específico, podemos checá-lo.
        # Exemplo: Se o ID do domínio para "Everyone" for "00000000000000000000000000000000", por exemplo.
        # if grantee_id == "ID_ESPECIFICO_PARA_EVERYONE_HUAWEI":
        #     is_public = True
        #     public_details.append(f"Public access via Grantee ID '{grantee_id}' with permission '{permission}'.")

    return is_public, public_details


async def get_huawei_obs_buckets(project_id: str, region_id: str) -> List[HuaweiOBSBucketData]:
    """Coleta dados de configuração de Huawei OBS buckets para um projeto e região."""
    collected_buckets: List[HuaweiOBSBucketData] = []
    try:
        obs_client = get_obs_client(region_id=region_id) # Passa a região para o client manager
    except ValueError as ve: # Erro de credenciais do client_manager
        logger.error(f"Credential error for Huawei OBS in region {region_id}: {ve}")
        return [HuaweiOBSBucketData(name="ERROR_CREDENTIALS", error_details=str(ve))]
    except Exception as e:
        logger.error(f"Failed to initialize OBS client for region {region_id}: {e}")
        return [HuaweiOBSBucketData(name=f"ERROR_CLIENT_INIT_{region_id}", error_details=str(e))]

    try:
        # Listar buckets - OBS list_buckets é global, não precisa de project_id aqui
        # mas a conta (AK/SK) já define o escopo.
        # O SDK Python do OBS para `listBuckets` não toma `project_id` no request.
        resp = obs_client.listBuckets() # Bloqueante

        if not hasattr(resp, 'body') or not hasattr(resp.body, 'buckets') or not resp.body.buckets:
            logger.info(f"No OBS buckets found or error in response structure for account/region {region_id}.")
            return []

        native_buckets = resp.body.buckets
        if not isinstance(native_buckets, list): # Se for um único objeto bucket
            native_buckets = [native_buckets]

    except sdk_exceptions.SdkException as e:
        logger.error(f"Huawei SDK error listing OBS buckets for region {region_id}: {e.error_code} - {e.error_message}")
        return [HuaweiOBSBucketData(name=f"ERROR_LIST_BUCKETS_SDK_{region_id}", error_details=f"{e.error_code}: {e.error_message}")]
    except Exception as e:
        logger.error(f"Unexpected error listing OBS buckets for region {region_id}: {e}", exc_info=True)
        return [HuaweiOBSBucketData(name=f"ERROR_LIST_BUCKETS_UNEXPECTED_{region_id}", error_details=str(e))]

    for bucket_native_info in native_buckets:
        bucket_name = bucket_native_info.name
        error_msg_bucket = []
        policy_data = None
        acl_data = None
        versioning_data = None
        logging_data = None
        is_pub_policy, pub_pol_details = False, []
        is_pub_acl, pub_acl_details = False, []

        # OBS: Cada chamada de detalhe pode precisar de um novo cliente se o bucket estiver em uma região diferente
        # da `region_id` passada, ou se o cliente OBS for configurado por bucket/endpoint.
        # No entanto, `get_obs_client` já é por região. Se `bucket_native_info.location` for diferente,
        # precisaríamos de um novo cliente para essa localização específica.
        # Para o MVP, vamos assumir que o `obs_client` da `region_id` principal pode obter detalhes
        # ou que todos os buckets de interesse estão nessa `region_id`.
        # O ideal é obter a localização do bucket e usar um cliente para essa localização.

        bucket_location = bucket_native_info.location or region_id # Fallback para a região da chamada

        # Se a localização do bucket for diferente da região do cliente, idealmente obter um novo cliente.
        # current_obs_client = obs_client
        # if bucket_location and bucket_location.lower() != region_id.lower():
        #     try:
        #         current_obs_client = get_obs_client(region_id=bucket_location)
        #     except Exception as client_err:
        #         error_msg_bucket.append(f"Failed to get client for bucket location {bucket_location}: {client_err}")
        #         # Continuar com o cliente original, mas pode falhar.

        try:
            # Get Bucket Policy
            try:
                policy_resp = obs_client.getBucketPolicy(bucketName=bucket_name) # Bloqueante
                if hasattr(policy_resp, 'body') and policy_resp.body is not None:
                     # A resposta do SDK OBS para getBucketPolicy pode ser um objeto com um campo 'policy'.
                     # Ou o body pode ser diretamente a string da política.
                     policy_string = getattr(policy_resp.body, 'policy', None) or str(policy_resp.body)
                     policy_data = _parse_obs_policy(policy_string)
                     if policy_data:
                         is_pub_policy, pub_pol_details = _check_obs_policy_public_access(policy_data)
            except sdk_exceptions.ServiceResponseException as e:
                if e.error_code == "NoSuchBucketPolicy": # Código de erro específico da Huawei
                    logger.debug(f"No policy for OBS bucket {bucket_name} in region {bucket_location}.")
                else:
                    logger.warning(f"Error getting policy for OBS bucket {bucket_name}: {e.error_code} - {e.error_message}")
                    error_msg_bucket.append(f"Policy fetch error: {e.error_code} - {e.error_message}")

            # Get Bucket ACL
            try:
                acl_resp = obs_client.getBucketAcl(bucketName=bucket_name) # Bloqueante
                if hasattr(acl_resp, 'body') and acl_resp.body is not None:
                    acl_data = _parse_obs_acl(acl_resp.body) # Passar o objeto body
                    if acl_data:
                        is_pub_acl, pub_acl_details = _check_obs_acl_public_access(acl_data)
            except sdk_exceptions.ServiceResponseException as e:
                logger.warning(f"Error getting ACL for OBS bucket {bucket_name}: {e.error_code} - {e.error_message}")
                error_msg_bucket.append(f"ACL fetch error: {e.error_code} - {e.error_message}")

            # Get Bucket Versioning
            try:
                versioning_resp = obs_client.getBucketVersioning(bucketName=bucket_name) # Bloqueante
                if hasattr(versioning_resp, 'body') and hasattr(versioning_resp.body, 'status'):
                    versioning_data = HuaweiOBSBucketVersioning(status=versioning_resp.body.status)
                else: # Se não tiver status, pode não estar configurado
                    versioning_data = HuaweiOBSBucketVersioning(status=None)
            except sdk_exceptions.ServiceResponseException as e:
                logger.warning(f"Error getting versioning for OBS bucket {bucket_name}: {e.error_code} - {e.error_message}")
                error_msg_bucket.append(f"Versioning fetch error: {e.error_code} - {e.error_message}")

            # Get Bucket Logging
            try:
                logging_resp = obs_client.getBucketLogging(bucketName=bucket_name) # Bloqueante
                if hasattr(logging_resp, 'body') and logging_resp.body and \
                   (getattr(logging_resp.body, 'target_bucket', None) or getattr(logging_resp.body, 'targetBucket', None)): # Nomes podem variar
                    target_bucket_val = getattr(logging_resp.body, 'target_bucket', None) or getattr(logging_resp.body, 'targetBucket', None)
                    target_prefix_val = getattr(logging_resp.body, 'target_prefix', None) or getattr(logging_resp.body, 'targetPrefix', None)
                    logging_data = HuaweiOBSBucketLogging(
                        enabled=True, # Se target_bucket existe, está habilitado
                        target_bucket=target_bucket_val,
                        target_prefix=target_prefix_val
                    )
                else:
                    logging_data = HuaweiOBSBucketLogging(enabled=False)
            except sdk_exceptions.ServiceResponseException as e:
                logger.warning(f"Error getting logging for OBS bucket {bucket_name}: {e.error_code} - {e.error_message}")
                error_msg_bucket.append(f"Logging fetch error: {e.error_code} - {e.error_message}")

            # Data de criação pode estar em formatos diferentes, ou precisar de parse
            creation_dt = None
            if hasattr(bucket_native_info, 'creation_date') and bucket_native_info.creation_date:
                try:
                    # O SDK OBS retorna creation_date como string. Ex: "2023-01-15T10:20:30.000Z"
                    creation_dt = datetime.strptime(bucket_native_info.creation_date, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
                except ValueError:
                     try: # Sem milissegundos
                        creation_dt = datetime.strptime(bucket_native_info.creation_date, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                     except ValueError:
                        logger.warning(f"Could not parse creation_date '{bucket_native_info.creation_date}' for bucket {bucket_name}")

            bucket_entry = HuaweiOBSBucketData(
                name=bucket_name,
                creation_date=creation_dt,
                location=bucket_location,
                storage_class=getattr(bucket_native_info, 'storage_class', None), # Pode não existir em todas as listagens
                bucket_policy=policy_data,
                acl=acl_data,
                versioning=versioning_data,
                logging=logging_data,
                is_public_by_policy=is_pub_policy,
                public_policy_details=pub_pol_details,
                is_public_by_acl=is_pub_acl,
                public_acl_details=pub_acl_details,
                error_details="; ".join(error_msg_bucket) if error_msg_bucket else None
            )
            collected_buckets.append(bucket_entry)

        except Exception as e_bucket_processing:
            logger.error(f"Unexpected error processing OBS bucket {bucket_name} in region {region_id}: {e_bucket_processing}", exc_info=True)
            collected_buckets.append(HuaweiOBSBucketData(
                name=bucket_name, location=bucket_location or region_id,
                error_details=f"Failed to process bucket details: {str(e_bucket_processing)}"
            ))

    logger.info(f"Collected {len(collected_buckets)} Huawei OBS buckets for project {project_id} in region {region_id}.")
    return collected_buckets
