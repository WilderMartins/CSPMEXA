import pytest
import datetime
from policy_engine_service.app.engine.gcp_cloud_audit_policies import evaluate_gcp_cloud_audit_log_policies, CRITICAL_GCP_IAM_METHODS, CRITICAL_GCP_COMPUTE_METHODS
from policy_engine_service.app.schemas.gcp.gcp_cloud_audit_input_schemas import GCPCloudAuditLogCollectionInput, GCPLogEntryInput
from policy_engine_service.app.schemas.alert_schema import AlertSeverityEnum

GCP_PROJECT_ID = "gcp-project-audit-test"

@pytest.fixture
def critical_iam_change_log_entry():
    return GCPLogEntryInput(
        logName=f"projects/{GCP_PROJECT_ID}/logs/cloudaudit.googleapis.com%2Factivity",
        resource={"type": "project", "labels": {"project_id": GCP_PROJECT_ID}},
        timestamp=datetime.datetime.now(datetime.timezone.utc),
        protoPayload={ # Simula a estrutura do AuditLog dentro do protoPayload
            "@type": "type.googleapis.com/google.cloud.audit.AuditLog",
            "serviceName": "iam.googleapis.com",
            "methodName": CRITICAL_GCP_IAM_METHODS[0], # Ex: SetIamPolicy
            "resourceName": f"projects/{GCP_PROJECT_ID}",
            "authenticationInfo": {"principalEmail": "malicious_actor@example.com"},
            "requestMetadata": {"callerIp": "1.2.3.4"}
        },
        audit_log_service_name="iam.googleapis.com", # Campos extraídos pelo coletor
        audit_log_method_name=CRITICAL_GCP_IAM_METHODS[0],
        audit_log_resource_name=f"projects/{GCP_PROJECT_ID}",
        audit_log_principal_email="malicious_actor@example.com",
        audit_log_caller_ip="1.2.3.4"
    )

@pytest.fixture
def critical_compute_delete_log_entry():
    return GCPLogEntryInput(
        logName=f"projects/{GCP_PROJECT_ID}/logs/cloudaudit.googleapis.com%2Factivity",
        resource={"type": "gce_instance", "labels": {"project_id": GCP_PROJECT_ID, "instance_id": "vm-to-delete"}},
        timestamp=datetime.datetime.now(datetime.timezone.utc),
        protoPayload={
            "@type": "type.googleapis.com/google.cloud.audit.AuditLog",
            "serviceName": "compute.googleapis.com",
            "methodName": "v1.compute.instances.delete", # Evento crítico
            "resourceName": f"projects/{GCP_PROJECT_ID}/zones/us-central1-a/instances/vm-to-delete",
            "authenticationInfo": {"principalEmail": "admin_user@example.com"},
        },
        audit_log_service_name="compute.googleapis.com",
        audit_log_method_name="v1.compute.instances.delete",
        audit_log_resource_name=f"projects/{GCP_PROJECT_ID}/zones/us-central1-a/instances/vm-to-delete",
        audit_log_principal_email="admin_user@example.com",
    )

@pytest.fixture
def normal_compute_get_log_entry():
    return GCPLogEntryInput(
        logName=f"projects/{GCP_PROJECT_ID}/logs/cloudaudit.googleapis.com%2Factivity",
        resource={"type": "gce_instance", "labels": {"project_id": GCP_PROJECT_ID}},
        timestamp=datetime.datetime.now(datetime.timezone.utc),
        protoPayload={
            "@type": "type.googleapis.com/google.cloud.audit.AuditLog",
            "serviceName": "compute.googleapis.com",
            "methodName": "v1.compute.instances.get", # Não é um método crítico listado
            "resourceName": f"projects/{GCP_PROJECT_ID}/zones/us-central1-a/instances/vm-readonly",
            "authenticationInfo": {"principalEmail": "auditor@example.com"},
        },
        audit_log_service_name="compute.googleapis.com",
        audit_log_method_name="v1.compute.instances.get",
        audit_log_resource_name=f"projects/{GCP_PROJECT_ID}/zones/us-central1-a/instances/vm-readonly",
        audit_log_principal_email="auditor@example.com",
    )

def test_gcp_critical_iam_change_detected(critical_iam_change_log_entry):
    log_collection = GCPCloudAuditLogCollectionInput(entries=[critical_iam_change_log_entry], projects_queried=[GCP_PROJECT_ID])
    alerts = evaluate_gcp_cloud_audit_log_policies(log_collection, GCP_PROJECT_ID)

    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["policy_id"] == "GCP_Critical_IAM_Change_Detected"
    assert alert["title"] == f"GCP Critical IAM Change Detected: {CRITICAL_GCP_IAM_METHODS[0]}"
    assert alert["severity"] == AlertSeverityEnum.HIGH # Ou CRITICAL dependendo da política
    assert alert["resource_id"] == f"projects/{GCP_PROJECT_ID}"

def test_gcp_critical_compute_operation_detected(critical_compute_delete_log_entry):
    log_collection = GCPCloudAuditLogCollectionInput(entries=[critical_compute_delete_log_entry], projects_queried=[GCP_PROJECT_ID])
    alerts = evaluate_gcp_cloud_audit_log_policies(log_collection, GCP_PROJECT_ID)

    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["policy_id"] == "GCP_Critical_Compute_Operation_Detected"
    assert alert["title"] == "GCP Critical Compute Operation: v1.compute.instances.delete"
    assert alert["severity"] == AlertSeverityEnum.HIGH

def test_gcp_normal_compute_operation_no_alert(normal_compute_get_log_entry):
    log_collection = GCPCloudAuditLogCollectionInput(entries=[normal_compute_get_log_entry], projects_queried=[GCP_PROJECT_ID])
    alerts = evaluate_gcp_cloud_audit_log_policies(log_collection, GCP_PROJECT_ID)
    assert len(alerts) == 0

def test_gcp_audit_log_collection_error():
    error_msg = "Global Audit Log collection failed for GCP."
    log_collection_error = GCPCloudAuditLogCollectionInput(error_message=error_msg, projects_queried=[GCP_PROJECT_ID])
    alerts = evaluate_gcp_cloud_audit_log_policies(log_collection_error, GCP_PROJECT_ID)

    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["policy_id"] == "GCP_AuditLog_GlobalCollection_Error"
    assert alert["severity"] == AlertSeverityEnum.MEDIUM
    assert error_msg in alert["description"]

def test_gcp_audit_log_entry_parsing_error():
    log_entry_with_error = GCPLogEntryInput(
        logName="error_log",
        resource={},
        timestamp=datetime.datetime.now(datetime.timezone.utc),
        collection_error_details="Failed to parse this log entry."
    )
    log_collection = GCPCloudAuditLogCollectionInput(entries=[log_entry_with_error], projects_queried=[GCP_PROJECT_ID])
    alerts = evaluate_gcp_cloud_audit_log_policies(log_collection, GCP_PROJECT_ID)

    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["policy_id"] == "GCP_AuditLog_EntryParsing_Error"
    assert alert["severity"] == AlertSeverityEnum.INFORMATIONAL
    assert "Failed to parse this log entry" in alert["description"]
