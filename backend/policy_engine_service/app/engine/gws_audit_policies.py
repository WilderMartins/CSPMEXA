from typing import List, Dict, Any, Optional
from ..schemas.google_workspace.gws_audit_input_schemas import GWSAuditLogCollectionInput, GWSAuditLogItemInput
from ..schemas.alert_schema import AlertSeverityEnum

# Eventos de auditoria do Google Workspace a serem monitorados
# Os nomes exatos dos eventos ("eventName") e applicationName precisam ser verificados na documentação do Google.
GWS_MONITORED_ADMIN_EVENTS = {
    "GRANT_ADMIN_PRIVILEGE": "Admin Privilege Granted to User",
    "CREATE_USER": "New User Created", # Monitorar criação de usuário
    "DELETE_USER": "User Deleted", # Monitorar deleção de usuário
    "SUSPEND_USER": "User Suspended",
    # Adicionar outros eventos de admin relevantes
}

GWS_MONITORED_LOGIN_EVENTS = {
    "login_failure": "User Login Failure Detected",
    "logout": "User Logout Detected", # Informativo
    "login_success": "User Login Success Detected", # Informativo, pode ser ruidoso
    # "gov_attack_warning": "Government Attack Warning" # Se disponível e relevante
}

def evaluate_gws_audit_log_policies(
    gws_log_collection: Optional[GWSAuditLogCollectionInput],
    account_id: Optional[str] # Customer ID do Google Workspace
) -> List[Dict[str, Any]]:
    """
    Avalia os logs de auditoria do Google Workspace em relação às políticas definidas.
    """
    alerts_data: List[Dict[str, Any]] = []

    if not gws_log_collection or not gws_log_collection.items:
        if gws_log_collection and gws_log_collection.error_message:
            alerts_data.append({
                "resource_id": account_id or "GoogleWorkspaceTenant",
                "resource_type": f"GoogleWorkspace::AuditLogCollection::{gws_log_collection.application_name_queried or 'UnknownApp'}",
                "provider": "google_workspace",
                "severity": AlertSeverityEnum.MEDIUM,
                "title": f"GWS Audit Log Collection Failed for app '{gws_log_collection.application_name_queried or 'UnknownApp'}'",
                "description": f"Failed to collect Google Workspace Audit Logs for application '{gws_log_collection.application_name_queried or 'UnknownApp'}' in account '{account_id}': {gws_log_collection.error_message}",
                "policy_id": "GWS_AuditLog_GlobalCollection_Error",
                "account_id": account_id,
                "details": {"application_name": gws_log_collection.application_name_queried, "error": gws_log_collection.error_message}
            })
        return alerts_data

    app_name = gws_log_collection.application_name_queried or "unknown_app"

    for log_item in gws_log_collection.items:
        if log_item.collection_error_details:
            # Alerta para erro de parsing do item de log
            alerts_data.append({
                "resource_id": str(log_item.id_time), # Usar timestamp como um ID se outros não estiverem disponíveis
                "resource_type": f"GoogleWorkspace::AuditLogItem::{app_name}",
                "provider": "google_workspace",
                "severity": AlertSeverityEnum.INFORMATIONAL,
                "title": f"GWS Audit Log Item Parsing Issue for app '{app_name}'",
                "description": f"Could not fully parse GWS Audit Log item at '{log_item.id_time}' for account '{account_id}': {log_item.collection_error_details}",
                "policy_id": "GWS_AuditLog_ItemParsing_Error",
                "account_id": account_id,
                "details": {"log_item_id_time": str(log_item.id_time), "error": log_item.collection_error_details}
            })
            continue

        if not log_item.events:
            continue

        for event in log_item.events:
            actor_email = log_item.actor.email if log_item.actor else "Unknown Actor"
            ip_address = log_item.ip_address or "N/A"

            # Política para eventos de Admin
            if app_name == "admin" and event.name in GWS_MONITORED_ADMIN_EVENTS:
                target_user_param = next((p.value for p in event.parameters if p.name == "USER_EMAIL"), None)
                privilege_param = next((p.value for p in event.parameters if p.name == "PRIVILEGE_NAME"), None)

                description = (
                    f"Administrative event '{event.name}' performed by '{actor_email}' from IP '{ip_address}'. "
                    f"Target User: {target_user_param or 'N/A'}. "
                    f"Privilege: {privilege_param or 'N/A'}."
                )
                severity = AlertSeverityEnum.HIGH
                if event.name == "GRANT_ADMIN_PRIVILEGE":
                    severity = AlertSeverityEnum.CRITICAL
                elif event.name == "DELETE_USER":
                    severity = AlertSeverityEnum.CRITICAL

                alerts_data.append({
                    "resource_id": target_user_param or actor_email, # O recurso é o usuário afetado ou o ator
                    "resource_type": "GoogleWorkspace::AdminEvent",
                    "provider": "google_workspace",
                    "severity": severity,
                    "title": f"GWS Admin Event: {GWS_MONITORED_ADMIN_EVENTS[event.name]}",
                    "description": description,
                    "policy_id": f"GWS_AdminEvent_{event.name}",
                    "account_id": account_id,
                    "details": {
                        "event_name": event.name,
                        "event_type": event.type,
                        "actor_email": actor_email,
                        "ip_address": ip_address,
                        "target_user": target_user_param,
                        "privilege_name": privilege_param,
                        "event_time": str(log_item.id_time),
                        "parameters": [p.model_dump() for p in event.parameters]
                    },
                    "recommendation": "Review this administrative action for legitimacy. Ensure it aligns with your organization's policies and was performed by an authorized administrator."
                })

            # Política para eventos de Login
            if app_name == "login" and event.name in GWS_MONITORED_LOGIN_EVENTS:
                severity = AlertSeverityEnum.MEDIUM # Default para falha de login
                if event.name == "login_failure":
                    severity = AlertSeverityEnum.MEDIUM
                elif event.name == "login_success":
                    severity = AlertSeverityEnum.INFORMATIONAL # Login sucesso é geralmente informativo
                elif event.name == "logout":
                     severity = AlertSeverityEnum.INFORMATIONAL

                alerts_data.append({
                    "resource_id": actor_email, # O recurso é o usuário que tentou logar/deslogar
                    "resource_type": "GoogleWorkspace::LoginEvent",
                    "provider": "google_workspace",
                    "severity": severity,
                    "title": f"GWS Login Event: {GWS_MONITORED_LOGIN_EVENTS[event.name]}",
                    "description": f"Login event '{event.name}' for user '{actor_email}' from IP '{ip_address}'.",
                    "policy_id": f"GWS_LoginEvent_{event.name}",
                    "account_id": account_id,
                    "details": {
                        "event_name": event.name,
                        "event_type": event.type,
                        "actor_email": actor_email,
                        "ip_address": ip_address,
                        "event_time": str(log_item.id_time),
                        "parameters": [p.model_dump() for p in event.parameters]
                    },
                    "recommendation": "For login failures, monitor for repeated attempts which might indicate brute-force attacks. For successful logins, ensure they originate from expected locations/devices."
                })

            # Adicionar mais lógicas para outras application_name (drive, token, etc.) e event_name aqui
            # Ex: if app_name == "drive" and event.name == "download_compromised_content": ...

    return alerts_data
