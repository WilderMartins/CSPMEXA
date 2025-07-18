import logging
from typing import List, Dict, Any, Optional, Callable

# Importar as funções de verificação
from .aws_cloudtrail_policies import check_cloudtrail_multi_region, check_cloudtrail_log_file_validation
from .aws_iam_policies import check_root_mfa_enabled, check_stale_key_s3_write_access

logger = logging.getLogger(__name__)

# --- Registro de Funções de Verificação ---
# Mapeia o nome da função no YAML para a função Python real.
POLICY_CHECK_REGISTRY: Dict[str, Callable[[Any], List[Dict[str, Any]]]] = {
    "check_cloudtrail_multi_region": check_cloudtrail_multi_region,
    "check_cloudtrail_log_file_validation": check_cloudtrail_log_file_validation,
    "check_root_mfa_enabled": check_root_mfa_enabled,
    "check_stale_key_s3_write_access": check_stale_key_s3_write_access,
    # Adicionar outras funções de verificação aqui
}

def evaluate_policy(policy: Dict[str, Any], data: List[Dict[str, Any]], account_id: str) -> List[Dict[str, Any]]:
    """
    Avalia uma única política contra um conjunto de dados.
    Determina se a avaliação deve usar uma função de verificação personalizada ou a lógica baseada em regras.
    """
    check_function_name = policy.get("check_function")

    if check_function_name:
        # --- Avaliação baseada em função ---
        check_function = POLICY_CHECK_REGISTRY.get(check_function_name)
        if not check_function:
            logger.error(f"Função de verificação '{check_function_name}' para a política '{policy['id']}' não encontrada no registro.")
            return []

        try:
            # A função de verificação é responsável por iterar sobre os dados e retornar uma lista de violações.
            violations = check_function(data)
            alerts = []
            for violation in violations:
                alerts.append({
                    "resource_id": violation.get("resource_id", "N/A"),
                    "resource_type": violation.get("resource_type", policy.get("service")),
                    "account_id": account_id,
                    "region": violation.get("region", "global"),
                    "provider": policy["provider"],
                    "severity": policy["severity"],
                    "title": policy["title"],
                    "description": violation.get("details"),
                    "policy_id": policy["id"],
                    "recommendation": policy.get("recommendation"),
                    "remediation_guide": policy.get("remediation_guide"),
                })
            return alerts
        except Exception as e:
            logger.exception(f"Erro ao executar a função de verificação '{check_function_name}': {e}")
            return []

    else:
        # --- Avaliação baseada em regras (lógica legada) ---
        # Esta lógica precisa ser adaptada para iterar sobre a lista de dados
        # e não apenas um único recurso.
        # Por enquanto, vamos pular a implementação detalhada da lógica de regras
        # para focar na avaliação baseada em função.
        return []
