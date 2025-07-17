import boto3
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
from typing import List, Dict, Any, Optional
from app.core.config import settings # settings.AWS_REGION_NAME pode ser usado para o cliente inicial
from app.schemas.iam import (
    IAMUserData, IAMUserAccessKeyMetadata, IAMUserMFADevice,
    IAMPolicyAttachment, IAMUserPolicy,
    IAMRoleData, IAMRoleLastUsed,
    IAMPolicyData
)
import logging
from fastapi import HTTPException
import json # Para carregar documentos de política inline

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

iam_client_cache = None

def get_iam_client():
    global iam_client_cache
    if iam_client_cache is None:
        try:
            # IAM é um serviço global, mas o cliente Boto3 ainda pode ser associado a uma região na configuração.
            # A documentação do Boto3 sugere que, para serviços globais, a região no cliente é ignorada
            # para o endpoint do serviço, mas pode ser usada para outras coisas como assinatura.
            # Usar a região padrão definida nas configurações é uma prática segura.
            iam_client_cache = boto3.client("iam", region_name=settings.AWS_REGION_NAME)
        except (NoCredentialsError, PartialCredentialsError) as e:
            logger.error(f"AWS credentials not found or incomplete for IAM: {e}")
            raise HTTPException(status_code=500, detail="AWS credentials not configured for IAM.") from e
        except Exception as e:
            logger.error(f"Error creating IAM client: {e}")
            raise HTTPException(status_code=500, detail=f"Error creating IAM client: {str(e)}") from e
    return iam_client_cache

async def get_iam_user_details(user_name: str, client) -> Dict[str, Any]:
    """Coleta detalhes para um usuário IAM específico."""
    details = {
        "attached_policies": [],
        "inline_policies": [],
        "mfa_devices": [],
        "access_keys": [],
        "tags": []
    }

    # Políticas Anexadas
    try:
        paginator_attached = client.get_paginator('list_attached_user_policies')
        for page in paginator_attached.paginate(UserName=user_name):
            for policy in page.get("AttachedPolicies", []):
                details["attached_policies"].append(IAMPolicyAttachment(**policy))
    except ClientError as e:
        logger.warning(f"Could not list attached policies for user {user_name}: {e.response['Error']['Message']}")
        # Não parar a coleta de outros detalhes por isso

    # Políticas Inline
    try:
        paginator_inline = client.get_paginator('list_user_policies')
        for page in paginator_inline.paginate(UserName=user_name):
            for policy_name in page.get("PolicyNames", []):
                try:
                    policy_doc_response = client.get_user_policy(UserName=user_name, PolicyName=policy_name)
                    details["inline_policies"].append(IAMUserPolicy(
                        PolicyName=policy_name,
                        policy_document=json.loads(policy_doc_response["PolicyDocument"]) if isinstance(policy_doc_response["PolicyDocument"], str) else policy_doc_response["PolicyDocument"]
                    ))
                except ClientError as e_doc:
                    logger.warning(f"Could not get inline policy document {policy_name} for user {user_name}: {e_doc.response['Error']['Message']}")
                except json.JSONDecodeError as e_json:
                    logger.error(f"Error decoding inline policy JSON for user {user_name}, policy {policy_name}: {e_json}")

    except ClientError as e:
        logger.warning(f"Could not list inline policies for user {user_name}: {e.response['Error']['Message']}")

    # Dispositivos MFA
    try:
        paginator_mfa = client.get_paginator('list_mfa_devices')
        for page in paginator_mfa.paginate(UserName=user_name):
            for mfa_device in page.get("MFADevices", []):
                details["mfa_devices"].append(IAMUserMFADevice(UserName=user_name, **mfa_device)) # Adiciona UserName aqui
    except ClientError as e:
        logger.warning(f"Could not list MFA devices for user {user_name}: {e.response['Error']['Message']}")

    # Chaves de Acesso
    try:
        paginator_keys = client.get_paginator('list_access_keys')
        for page in paginator_keys.paginate(UserName=user_name):
            for key_meta in page.get("AccessKeyMetadata", []):
                last_used_info = {}
                if key_meta.get("AccessKeyId"):
                    try:
                        last_used_response = client.get_access_key_last_used(AccessKeyId=key_meta["AccessKeyId"])
                        if last_used_response.get("AccessKeyLastUsed"):
                            last_used_info = {
                                "last_used_date": last_used_response["AccessKeyLastUsed"].get("LastUsedDate"),
                                "last_used_service": last_used_response["AccessKeyLastUsed"].get("ServiceName"),
                                "last_used_region": last_used_response["AccessKeyLastUsed"].get("Region"),
                            }
                    except ClientError as e_lu:
                         # Comum se a chave nunca foi usada ou info não disponível
                        logger.debug(f"Could not get last used info for access key {key_meta['AccessKeyId']} for user {user_name}: {e_lu.response['Error']['Message']}")

                details["access_keys"].append(IAMUserAccessKeyMetadata(**key_meta, **last_used_info))

    except ClientError as e:
        logger.warning(f"Could not list access keys for user {user_name}: {e.response['Error']['Message']}")

    # Tags do Usuário
    try:
        tag_response = client.list_user_tags(UserName=user_name) # Não é paginado diretamente, mas pode ter Marker
        details["tags"] = tag_response.get("Tags", [])
        # Adicionar lógica de paginação se muitos tags forem esperados (raro para usuários)
    except ClientError as e:
        logger.warning(f"Could not list tags for user {user_name}: {e.response['Error']['Message']}")

    return details


async def get_account_summary_data(client) -> Dict[str, Any]:
    """Coleta o sumário da conta IAM."""
    try:
        summary_map = client.get_account_summary()
        return summary_map.get("SummaryMap", {})
    except ClientError as e:
        logger.error(f"Could not get IAM account summary: {e.response['Error']['Message']}")
        return {"Error": f"Could not get IAM account summary: {e.response['Error']['Message']}"}

async def get_iam_users_data() -> List[IAMUserData]:
    client = get_iam_client() # Pode levantar HTTPException
    users_data: List[IAMUserData] = []

    try:
        # Coletar o sumário da conta primeiro
        account_summary = await get_account_summary_data(client)

        paginator = client.get_paginator('list_users')
        first_user = True
        for page in paginator.paginate():
            for user_dict in page.get("Users", []):
                user_name = user_dict["UserName"]
                error_details_user = None
                user_specific_details = {}
                try:
                    user_specific_details = await get_iam_user_details(user_name, client)
                except Exception as e_details:
                    logger.error(f"Failed to get all details for user {user_name}: {e_details}")
                    error_details_user = f"Failed to retrieve some details: {str(e_details)}"

                iam_user = IAMUserData(
                    **user_dict,
                    **user_specific_details,
                    error_details=error_details_user,
                    account_summary=account_summary if first_user else None
                )
                users_data.append(iam_user)
                first_user = False

    except ClientError as e:
        logger.error(f"ClientError listing IAM users: {e.response['Error']['Message']}")
        raise HTTPException(status_code=500, detail=f"ClientError listing IAM users: {e.response['Error']['Message']}") from e
    except Exception as e:
        logger.error(f"Unexpected error listing IAM users: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while listing IAM users: {str(e)}") from e

    return users_data


async def get_iam_role_details(role_name: str, client) -> Dict[str, Any]:
    """Coleta detalhes para uma role IAM específica."""
    details = {
        "attached_policies": [],
        "inline_policies": [],
        "tags": []
        # RoleLastUsed é obtido diretamente do list_roles, não precisa ser coletado aqui
    }

    # Políticas Anexadas
    try:
        paginator_attached = client.get_paginator('list_attached_role_policies')
        for page in paginator_attached.paginate(RoleName=role_name):
            for policy in page.get("AttachedPolicies", []):
                details["attached_policies"].append(IAMPolicyAttachment(**policy))
    except ClientError as e:
        logger.warning(f"Could not list attached policies for role {role_name}: {e.response['Error']['Message']}")

    # Políticas Inline
    try:
        paginator_inline = client.get_paginator('list_role_policies')
        for page in paginator_inline.paginate(RoleName=role_name):
            for policy_name in page.get("PolicyNames", []):
                try:
                    policy_doc_response = client.get_role_policy(RoleName=role_name, PolicyName=policy_name)
                    details["inline_policies"].append(IAMUserPolicy( # Reutilizando schema
                        PolicyName=policy_name,
                        policy_document=json.loads(policy_doc_response["PolicyDocument"]) if isinstance(policy_doc_response["PolicyDocument"], str) else policy_doc_response["PolicyDocument"]
                    ))
                except ClientError as e_doc:
                    logger.warning(f"Could not get inline policy document {policy_name} for role {role_name}: {e_doc.response['Error']['Message']}")
                except json.JSONDecodeError as e_json:
                     logger.error(f"Error decoding inline policy JSON for role {role_name}, policy {policy_name}: {e_json}")
    except ClientError as e:
        logger.warning(f"Could not list inline policies for role {role_name}: {e.response['Error']['Message']}")

    # Tags da Role
    try:
        tag_response = client.list_role_tags(RoleName=role_name)
        details["tags"] = tag_response.get("Tags", [])
    except ClientError as e:
        logger.warning(f"Could not list tags for role {role_name}: {e.response['Error']['Message']}")

    return details

async def get_iam_roles_data() -> List[IAMRoleData]:
    client = get_iam_client()
    roles_data: List[IAMRoleData] = []

    try:
        paginator = client.get_paginator('list_roles')
        for page in paginator.paginate():
            for role_dict in page.get("Roles", []):
                role_name = role_dict["RoleName"]
                error_details_role = None
                role_specific_details = {}
                try:
                    role_specific_details = await get_iam_role_details(role_name, client)
                    # AssumeRolePolicyDocument é parte do role_dict principal
                    # RoleLastUsed também é parte do role_dict principal
                except Exception as e_details:
                    logger.error(f"Failed to get all details for role {role_name}: {e_details}")
                    error_details_role = f"Failed to retrieve some details: {str(e_details)}"

                # O AssumeRolePolicyDocument pode precisar ser decodificado se estiver em string URL-encoded
                assume_role_policy_doc = role_dict.get("AssumeRolePolicyDocument")
                if isinstance(assume_role_policy_doc, str):
                    try:
                        assume_role_policy_doc = json.loads(assume_role_policy_doc)
                    except json.JSONDecodeError:
                        logger.warning(f"Could not decode AssumeRolePolicyDocument for role {role_name}")
                        assume_role_policy_doc = {"Error": "Failed to decode policy document"}

                role_last_used = role_dict.get("RoleLastUsed")

                iam_role = IAMRoleData(
                    **role_dict, # Passa todos os campos do dicionário da role
                    AssumeRolePolicyDocument=assume_role_policy_doc, # Sobrescreve com o decodificado
                    RoleLastUsed=IAMRoleLastUsed(**role_last_used) if role_last_used else None,
                    **role_specific_details,
                    error_details=error_details_role
                )
                roles_data.append(iam_role)

    except ClientError as e:
        logger.error(f"ClientError listing IAM roles: {e.response['Error']['Message']}")
        raise HTTPException(status_code=500, detail=f"ClientError listing IAM roles: {e.response['Error']['Message']}") from e
    except Exception as e:
        logger.error(f"Unexpected error listing IAM roles: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while listing IAM roles: {str(e)}") from e

    return roles_data


async def get_iam_policies_data(scope: str = "Local") -> List[IAMPolicyData]:
    """
    Coleta dados de políticas IAM gerenciadas.
    Scope: 'All' (todas), 'AWS' (gerenciadas pela AWS), 'Local' (gerenciadas pelo cliente - padrão).
    """
    client = get_iam_client()
    policies_data: List[IAMPolicyData] = []

    try:
        paginator = client.get_paginator('list_policies')
        for page in paginator.paginate(Scope=scope):
            for policy_dict in page.get("Policies", []):
                policy_name = policy_dict["PolicyName"]
                policy_arn = policy_dict["Arn"]
                error_details_policy = None
                policy_document = None

                try:
                    # Obter o documento da política (versão padrão)
                    version_response = client.get_policy_version(
                        PolicyArn=policy_arn,
                        VersionId=policy_dict["DefaultVersionId"]
                    )
                    policy_document = version_response.get("PolicyVersion", {}).get("Document")
                    if isinstance(policy_document, str): # Documento pode vir URL encoded
                         policy_document = json.loads(policy_document)

                except ClientError as e_doc:
                    logger.warning(f"Could not get document for policy {policy_name} ({policy_arn}): {e_doc.response['Error']['Message']}")
                    error_details_policy = f"Failed to retrieve policy document: {e_doc.response['Error']['Message']}"
                except json.JSONDecodeError as e_json:
                    logger.error(f"Error decoding policy document for {policy_name}: {e_json}")
                    error_details_policy = f"Failed to decode policy document: {str(e_json)}"
                except Exception as e_pv:
                    logger.error(f"Unexpected error getting policy version for {policy_name}: {e_pv}")
                    error_details_policy = f"Unexpected error retrieving policy document: {str(e_pv)}"

                iam_policy = IAMPolicyData(
                    **policy_dict,
                    policy_document=policy_document,
                    error_details=error_details_policy
                    # Tags para políticas não são listadas diretamente, requerem list_policy_tags
                )
                policies_data.append(iam_policy)

    except ClientError as e:
        logger.error(f"ClientError listing IAM policies (Scope: {scope}): {e.response['Error']['Message']}")
        raise HTTPException(status_code=500, detail=f"ClientError listing IAM policies: {e.response['Error']['Message']}") from e
    except Exception as e:
        logger.error(f"Unexpected error listing IAM policies (Scope: {scope}): {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while listing IAM policies: {str(e)}") from e

    return policies_data
