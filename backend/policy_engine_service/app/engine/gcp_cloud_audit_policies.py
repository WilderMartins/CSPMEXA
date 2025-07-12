from typing import List, Dict, Any, Optional
from app.schemas.gcp.gcp_cloud_audit_input_schemas import GCPCloudAuditLogCollectionInput, GCPLogEntryInput
from app.schemas.alert_schema import AlertSeverityEnum

# Nomes de métodos IAM críticos do GCP a serem monitorados
CRITICAL_GCP_IAM_METHODS = [
    "SetIamPolicy", # Genérico, pode ser em projeto, bucket, etc.
    "google.iam.admin.v1.SetIamPolicy", # Mais específico
    "google.cloud.resourcemanager.v1.ProjectIamBindings.SetIamPolicy", # legacypb.SetIamPolicy
    # Adicionar outros métodos críticos, como criar/modificar roles, service accounts, keys
    "google.iam.admin.v1.CreateServiceAccount",
    "google.iam.admin.v1.CreateServiceAccountKey",
    "google.iam.admin.v1.DeleteServiceAccount",
    "google.iam.admin.v1.DeleteServiceAccountKey",
]

# Nomes de métodos de Compute Engine críticos
CRITICAL_GCP_COMPUTE_METHODS = [
    "v1.compute.instances.delete",
    "v1.compute.firewalls.patch", # Modificar firewall
    "v1.compute.firewalls.insert", # Criar firewall
    "v1.compute.firewalls.delete", # Deletar firewall
    # Adicionar outros
]


def evaluate_gcp_cloud_audit_log_policies(
    log_collection: Optional[GCPCloudAuditLogCollectionInput],
    account_id: Optional[str] # Project ID ou Org ID do escopo da consulta
) -> List[Dict[str, Any]]:
    """
    Avalia os GCP Cloud Audit Logs em relação às políticas definidas.
    """
    alerts_data: List[Dict[str, Any]] = []

    if not log_collection or not log_collection.entries:
        if log_collection and log_collection.error_message:
            alerts_data.append({
                "resource_id": account_id or "GCPResourceScope",
                "resource_type": "GCP::CloudAuditLog::Collection",
                "provider": "gcp",
                "severity": AlertSeverityEnum.MEDIUM,
                "title": "GCP Cloud Audit Log Collection Failed",
                "description": f"Failed to collect Cloud Audit Logs for '{account_id or 'scope'}': {log_collection.error_message}",
                "policy_id": "GCP_AuditLog_GlobalCollection_Error",
                "account_id": account_id,
                "details": {"filter_used": log_collection.filter_used, "error": log_collection.error_message}
            })
        return alerts_data

    for entry in log_collection.entries:
        if entry.collection_error_details:
            alerts_data.append({
                "resource_id": entry.insert_id or entry.log_name,
                "resource_type": "GCP::CloudAuditLog::LogEntry",
                "provider": "gcp",
                "severity": AlertSeverityEnum.INFORMATIONAL,
                "title": "GCP Audit Log Entry Parsing Issue",
                "description": f"Could not fully parse Audit Log entry '{entry.insert_id}': {entry.collection_error_details}",
                "policy_id": "GCP_AuditLog_EntryParsing_Error",
                "account_id": account_id, # Ou extrair do log_name se possível
                "details": {"log_name": entry.log_name, "insert_id": entry.insert_id, "error": entry.collection_error_details}
            })
            continue

        # Política: GCP_Critical_IAM_Change_Detected
        if entry.audit_log_service_name and "iam" in entry.audit_log_service_name.lower() and \
           entry.audit_log_method_name in CRITICAL_GCP_IAM_METHODS:

            # Detalhes específicos do request podem estar em entry.protoPayload.request
            request_details = entry.proto_payload.get("request") if entry.proto_payload else None

            alerts_data.append({
                "resource_id": entry.audit_log_resource_name or entry.log_name,
                "resource_type": "GCP::IAM::Activity", # Ou um tipo mais específico do recurso
                "provider": "gcp",
                "severity": AlertSeverityEnum.HIGH, # Pode ser CRITICAL dependendo do método/recurso
                "title": f"GCP Critical IAM Change Detected: {entry.audit_log_method_name}",
                "description": (
                    f"Critical IAM operation '{entry.audit_log_method_name}' detected on resource "
                    f"'{entry.audit_log_resource_name or 'UnknownResource'}' by principal '{entry.audit_log_principal_email or 'UnknownUser'}' "
                    f"from IP '{entry.audit_log_caller_ip or 'N/A'}'."
                ),
                "policy_id": "GCP_Critical_IAM_Change_Detected",
                "account_id": account_id, # Ou o projeto do audit_log_resource_name
                "details": {
                    "log_name": entry.log_name,
                    "insert_id": entry.insert_id,
                    "timestamp": entry.timestamp.isoformat(),
                    "service_name": entry.audit_log_service_name,
                    "method_name": entry.audit_log_method_name,
                    "resource_name_log": entry.audit_log_resource_name,
                    "principal_email": entry.audit_log_principal_email,
                    "caller_ip": entry.audit_log_caller_ip,
                    "request_payload": request_details # Cuidado com dados sensíveis
                },
                "recommendation": "Review this IAM change immediately. Verify if it was authorized and expected. If unauthorized, investigate and revert if necessary."
            })

        # Política: GCP_Critical_Compute_Operation_Detected
        if entry.audit_log_service_name and "compute" in entry.audit_log_service_name.lower() and \
           entry.audit_log_method_name in CRITICAL_GCP_COMPUTE_METHODS:

            alerts_data.append({
                "resource_id": entry.audit_log_resource_name or entry.log_name,
                "resource_type": "GCP::ComputeEngine::Activity",
                "provider": "gcp",
                "severity": AlertSeverityEnum.HIGH,
                "title": f"GCP Critical Compute Operation: {entry.audit_log_method_name}",
                "description": (
                    f"Critical Compute Engine operation '{entry.audit_log_method_name}' detected on resource "
                    f"'{entry.audit_log_resource_name or 'UnknownResource'}' by principal '{entry.audit_log_principal_email or 'UnknownUser'}'."
                ),
                "policy_id": "GCP_Critical_Compute_Operation_Detected",
                "account_id": account_id,
                "details": {
                     "log_name": entry.log_name, "insert_id": entry.insert_id, "timestamp": entry.timestamp.isoformat(),
                    "service_name": entry.audit_log_service_name, "method_name": entry.audit_log_method_name,
                    "resource_name_log": entry.audit_log_resource_name, "principal_email": entry.audit_log_principal_email,
                },
                "recommendation": "Review this Compute Engine operation. If it involves deletion or critical modification (e.g., firewall change), verify its legitimacy."
            })

    return alerts_data
```
