import logging
from typing import List, Dict, Any, Optional
from dpath import util as dpath_util
import uuid

logger = logging.getLogger(__name__)

def evaluate_resource(resource: Dict[str, Any], policy: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Avalia um único recurso contra uma única política definida em formato de dicionário (do YAML).

    Args:
        resource: Um dicionário representando o recurso da nuvem (ex: um bucket S3).
        policy: Um dicionário representando a política carregada.

    Returns:
        Um dicionário com os dados do alerta se a política for violada, caso contrário None.
    """
    all_rules_match = True
    violation_details_list = []

    for rule in policy.get('rules', []):
        field = rule.get('field')
        operator = rule.get('operator')
        expected_value = rule.get('value')

        try:
            # Usa dpath para obter valores de campos aninhados, ex: 'acl.is_public'
            actual_values = [v for _, v in dpath_util.search(resource, field, yielded=True)]

            if not actual_values:
                # Se o campo não existe no recurso, a regra não pode ser violada.
                # Ex: se um bucket não tem 'acl', a regra sobre 'acl.grants' não se aplica.
                all_rules_match = False
                break

            actual_value = actual_values[0] # Pega o primeiro valor encontrado
            rule_matched = False

            if operator == 'is_true':
                if actual_value is True:
                    rule_matched = True
            elif operator == 'is_false':
                if actual_value is False:
                    rule_matched = True
            elif operator == 'is_none':
                if actual_value is None:
                    rule_matched = True
            elif operator == 'is_not_none':
                if actual_value is not None:
                    rule_matched = True
            elif operator == 'equals':
                if actual_value == expected_value:
                    rule_matched = True
            elif operator == 'not_equals':
                if actual_value != expected_value:
                    rule_matched = True
            elif operator == 'contains_any_of':
                # Verifica se algum item na lista 'actual_value' está em 'expected_value'
                if isinstance(actual_value, list) and isinstance(expected_value, list):
                    # Para ACLs, actual_value é uma lista de dicts. Precisamos de uma lógica mais específica.
                    # Esta é uma simplificação. Uma implementação real precisaria de "handlers" por operador.
                    # Vamos adaptar para o caso específico de ACLs do S3.
                    if policy['id'] == 'aws_s3_public_acls':
                        for grant in actual_value:
                            grantee_uri = grant.get('Grantee', {}).get('URI')
                            if grantee_uri in expected_value:
                                rule_matched = True
                                violation_details_list.append(f"Acesso público concedido a '{grantee_uri}'")
                                break # Para de verificar os grants assim que um público é encontrado

            if not rule_matched:
                all_rules_match = False
                break
        except Exception as e:
            logger.error(f"Erro ao avaliar a regra {rule} para o recurso: {e}")
            all_rules_match = False
            break

    if all_rules_match:
        # Se todas as regras corresponderam, a política foi violada. Gerar dados do alerta.
        logger.info(f"VIOLAÇÃO: Recurso '{resource.get('id') or resource.get('name')}' violou a política '{policy['id']}'.")
        return {
            "id": str(uuid.uuid4()),
            "resource_id": resource.get('id') or resource.get('name', 'N/A'),
            "resource_type": policy['resource_type'],
            "account_id": resource.get('account_id', 'N/A'),
            "region": resource.get('region', 'N/A'),
            "provider": policy['provider'],
            "severity": policy['severity'],
            "title": policy['description'], # A descrição da política se torna o título do alerta
            "description": f"O recurso violou a política '{policy['id']}'. Detalhes: {'. '.join(violation_details_list) if violation_details_list else 'Verifique os detalhes do recurso.'}",
            "policy_id": policy['id'],
            "details": resource, # Inclui o recurso inteiro para contexto
            "recommendation": policy.get('remediation', 'Nenhuma recomendação fornecida.'),
            "status": "open",
        }

    return None
