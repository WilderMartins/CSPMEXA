from typing import List, Dict, Any, Optional
from app.schemas.huawei.huawei_cts_input_schemas import CTSTraceCollectionInput, CTSTraceInput
from app.schemas.alert_schema import AlertSeverityEnum

# Lista de eventNames considerados críticos. Esta lista pode ser expandida.
# Os nomes exatos dos eventos precisam ser verificados na documentação do CTS da Huawei.
CRITICAL_CTS_EVENT_NAMES = [
    # CTS specific
    "DeleteTracker",
    "StopTracker",
    # IAM specific
    "CreateAccessKey", # Pode ser mais crítico para certos usuários (ex: root/admin)
    "DeleteUser", # Deleção de usuário
    "CreateUser", # Criação de usuário (monitorar)
    "UpdateLoginPolicy", # Mudança na política de login
    "CreatePolicy", # Criação de política IAM
    "DeletePolicy",
    "AttachUserPolicy", # Anexar política a usuário
    "DetachUserPolicy",
    # OBS specific
    "DeleteBucket",
    "PutBucketPolicy", # Alteração de política de bucket
    "PutBucketAcl",    # Alteração de ACL de bucket
    # ECS specific
    "DeleteServer",
    "CreateServer", # Monitorar criação de novas instâncias
    # VPC specific
    "DeleteSecurityGroup",
    "AuthorizeSecurityGroupEgress", # Mudanças em SGs que permitem saída total
    "AuthorizeSecurityGroupIngress",# Mudanças em SGs que permitem entrada total (0.0.0.0/0)
    # Outros serviços...
]

def evaluate_huawei_cts_policies(
    cts_trace_collection: Optional[CTSTraceCollectionInput],
    account_id: Optional[str] # Geralmente o project_id ou domain_id da Huawei
) -> List[Dict[str, Any]]:
    """
    Avalia os logs do Huawei Cloud Trace Service (CTS) em relação às políticas definidas.
    Retorna uma lista de dicionários para AlertCreate.
    """
    alerts_data: List[Dict[str, Any]] = []

    if not cts_trace_collection or not cts_trace_collection.traces:
        if cts_trace_collection and cts_trace_collection.error_message:
            alerts_data.append({
                "resource_id": account_id or "HuaweiTenant",
                "resource_type": "HuaweiCloud::CTS::LogCollection",
                "provider": "huawei",
                "severity": AlertSeverityEnum.MEDIUM,
                "title": "Huawei CTS Log Collection Failed",
                "description": f"Failed to collect Cloud Trace Service logs for account '{account_id}': {cts_trace_collection.error_message}",
                "policy_id": "CTS_GlobalCollection_Error",
                "account_id": account_id,
                "details": {"error": cts_trace_collection.error_message}
            })
        else:
            # Nenhum log para processar, ou nenhuma coleção fornecida
            pass
        return alerts_data

    for trace in cts_trace_collection.traces:
        if trace.collection_error_details:
            alerts_data.append({
                "resource_id": trace.trace_id,
                "resource_type": "HuaweiCloud::CTS::Trace",
                "provider": "huawei",
                "severity": AlertSeverityEnum.INFORMATIONAL,
                "title": "Huawei CTS Trace Data Parsing Issue",
                "description": f"Could not fully parse CTS trace '{trace.trace_id}' for account '{account_id}': {trace.collection_error_details}",
                "policy_id": "CTS_TraceParsing_Error",
                "account_id": account_id,
                "region": trace.region_id,
                "details": {"trace_id": trace.trace_id, "trace_name": trace.trace_name, "error": trace.collection_error_details}
            })
            continue

        # Política: CTS_Critical_Operation_Detected
        if trace.event_name and trace.event_name in CRITICAL_CTS_EVENT_NAMES:
            user_info = "Unknown User"
            if trace.user_identity:
                user_info = trace.user_identity.user_name or trace.user_identity.principal_id or "N/A"
                if trace.user_identity.domain_name:
                    user_info += f"@{trace.user_identity.domain_name}"

            description = (
                f"Critical operation '{trace.event_name}' detected in Huawei Cloud account '{account_id}' "
                f"(Region: {trace.region_id or 'N/A'}). "
                f"Operation performed by user '{user_info}' from IP '{trace.source_ip_address or 'N/A'}'. "
                f"Resource affected: '{trace.resource_name or 'N/A'}' (Type: '{trace.resource_type or 'N/A'}')."
            )
            if trace.error_code or trace.error_message:
                description += f" Operation status: Failed (Error: {trace.error_code or ''} {trace.error_message or ''})."
            else:
                description += " Operation status: Success."

            severity = AlertSeverityEnum.HIGH # Default para operações críticas
            if trace.event_name in ["DeleteTracker", "StopTracker"]:
                severity = AlertSeverityEnum.CRITICAL
            elif "Delete" in trace.event_name: # Aumentar severidade para operações de deleção
                 severity = AlertSeverityEnum.CRITICAL if severity != AlertSeverityEnum.CRITICAL else severity

            alerts_data.append({
                "resource_id": trace.resource_name or trace.trace_id, # Usar trace_id se resource_name não estiver disponível
                "resource_type": trace.resource_type or "HuaweiCloud::CTS::Trace",
                "provider": "huawei",
                "severity": severity,
                "title": f"Huawei CTS: Critical Operation Detected - {trace.event_name}",
                "description": description,
                "policy_id": "CTS_Critical_Operation_Detected",
                "account_id": account_id, # project_id ou domain_id
                "region": trace.region_id,
                "details": {
                    "trace_id": trace.trace_id,
                    "trace_name": trace.trace_name,
                    "event_source": trace.event_source,
                    "event_name": trace.event_name,
                    "event_time": trace.event_time.isoformat() if trace.event_time else None,
                    "user_identity": trace.user_identity.model_dump(by_alias=True) if trace.user_identity else None,
                    "source_ip_address": trace.source_ip_address,
                    "request_parameters": trace.request_parameters,
                    "response_elements": trace.response_elements, # Cuidado com dados sensíveis aqui
                    "error_details_cts": f"{trace.error_code or ''} {trace.error_message or ''}".strip() or None,
                    "tracker_name": trace.tracker_name
                },
                "recommendation": "Review this critical operation immediately. Verify if it was authorized and expected. If unauthorized, investigate for potential security breach and take remediation actions."
            })

    return alerts_data
```
