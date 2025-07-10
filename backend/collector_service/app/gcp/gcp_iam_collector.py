from googleapiclient.errors import HttpError
from google.cloud.exceptions import Forbidden, NotFound, GoogleCloudError
from typing import List, Optional, Dict, Any
from app.schemas.gcp_iam import GCPProjectIAMPolicyData, GCPIAMPolicy, GCPIAMBinding
from app.gcp.gcp_client_manager import get_cloud_resource_manager_client, get_gcp_project_id
import logging

logger = logging.getLogger(__name__)

def _parse_native_iam_policy_bindings(native_bindings: Optional[List[Dict[str, Any]]]) -> List[GCPIAMBinding]:
    """Converte a lista de bindings da API GCP para a lista de schemas Pydantic GCPIAMBinding."""
    if not native_bindings:
        return []

    parsed_bindings: List[GCPIAMBinding] = []
    for binding_dict in native_bindings:
        parsed_bindings.append(GCPIAMBinding(
            role=binding_dict.get("role"),
            members=binding_dict.get("members", []),
            condition=binding_dict.get("condition") # condition pode ser None
        ))
    return parsed_bindings

def _check_external_members_in_primitive_roles(iam_policy: GCPIAMPolicy) -> (bool, List[str]):
    """
    Verifica se 'allUsers' ou 'allAuthenticatedUsers' estão presentes em papéis primitivos (owner, editor, viewer).
    """
    has_issue = False
    details = []
    primitive_roles = ["roles/owner", "roles/editor", "roles/viewer"]
    external_principals = ["allUsers", "allAuthenticatedUsers"]

    for binding in iam_policy.bindings:
        if binding.role in primitive_roles:
            for member in binding.members:
                if member in external_principals:
                    has_issue = True
                    details.append(f"Principal externo '{member}' encontrado com papel primitivo '{binding.role}'.")
    return has_issue, details


async def get_gcp_project_iam_policy(project_id: Optional[str] = None) -> Optional[GCPProjectIAMPolicyData]:
    """
    Coleta a política IAM para um projeto GCP especificado.
    Retorna um único objeto GCPProjectIAMPolicyData ou None se houver erro crítico.
    """
    actual_project_id = project_id or get_gcp_project_id()
    if not actual_project_id:
        logger.error("GCP Project ID is required for collecting project IAM policy.")
        # Poderia retornar um objeto de erro específico, mas para uma única política,
        # None ou levantar exceção pode ser mais apropriado se o ID do projeto é fundamental.
        # Para manter consistência com outros coletores que retornam listas,
        # se esta função fosse parte de um loop maior, um objeto de erro seria melhor.
        # Como é uma chamada singular por projeto, None é aceitável.
        return None

    error_details_msg = None
    policy_data = None

    try:
        crm_client = get_cloud_resource_manager_client()
        # A API getIamPolicy para projetos espera 'projects/{projectId}' como resource.
        # Versão 3 da API:
        # request = crm_client.projects().getIamPolicy(resource=actual_project_id, body={"options": {"requestedPolicyVersion": 3}})
        # Versão 1 da API (mais comum em exemplos antigos):
        request_body = {"options": {"requestedPolicyVersion": 3}}
        request = crm_client.projects().getIamPolicy(resource=actual_project_id, body=request_body)

        native_policy = request.execute() # Bloqueante, idealmente usar asyncio com google-api-python-client,
                                      # ou executar em um thread executor com FastAPI.
                                      # Para simplificar no MVP, vamos manter bloqueante e o endpoint FastAPI será async.
                                      # A biblioteca google-cloud-resource-manager é async e pode ser uma alternativa.

        parsed_bindings = _parse_native_iam_policy_bindings(native_policy.get("bindings"))

        policy_data = GCPIAMPolicy(
            version=native_policy.get("version"),
            bindings=parsed_bindings,
            etag=native_policy.get("etag")
        )

    except HttpError as e: # Erro específico do google-api-python-client
        logger.error(f"HttpError getting IAM policy for project {actual_project_id}: {e.resp.status} - {e._get_reason()}")
        error_details_msg = f"HttpError: {e.resp.status} - {e._get_reason()}"
    except Forbidden as e:
        logger.error(f"Forbidden to get IAM policy for project {actual_project_id}: {e}")
        error_details_msg = f"Forbidden: {str(e)}"
    except NotFound as e:
        logger.error(f"Project {actual_project_id} not found when getting IAM policy: {e}")
        error_details_msg = f"Project Not Found: {str(e)}"
    except GoogleCloudError as e:
        logger.error(f"GoogleCloudError getting IAM policy for project {actual_project_id}: {e}")
        error_details_msg = f"GoogleCloudError: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error getting IAM policy for project {actual_project_id}: {e}", exc_info=True)
        error_details_msg = f"Unexpected error: {str(e)}"

    if policy_data:
        has_ext_primitive, ext_primitive_details = _check_external_members_in_primitive_roles(policy_data)
        return GCPProjectIAMPolicyData(
            project_id=actual_project_id,
            iam_policy=policy_data,
            has_external_members_with_primitive_roles=has_ext_primitive,
            external_primitive_role_details=ext_primitive_details,
            error_details=error_details_msg # Pode haver erro parcial se a política foi lida mas algo mais falhou
        )
    elif error_details_msg: # Se policy_data não foi obtido e há um erro
        return GCPProjectIAMPolicyData(
            project_id=actual_project_id,
            iam_policy=GCPIAMPolicy(bindings=[]), # Política vazia em caso de erro total
            error_details=error_details_msg
        )

    return None # Caso de falha não previsto
