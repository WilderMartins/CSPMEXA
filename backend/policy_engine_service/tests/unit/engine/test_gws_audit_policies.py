import pytest
import datetime
from policy_engine_service.app.engine.gws_audit_policies import evaluate_gws_audit_log_policies
from policy_engine_service.app.schemas.google_workspace.gws_audit_input_schemas import (
    GWSAuditLogCollectionInput,
    GWSAuditLogItemInput,
    GWSAuditLogEventInput,
    GWSAuditLogActorInput,
    GWSAuditLogEventParameterInput
)
from policy_engine_service.app.schemas.alert_schema import AlertSeverityEnum

CUSTOMER_ID_GWS = "C012345test"

@pytest.fixture
def admin_privilege_granted_log_item():
    return GWSAuditLogItemInput(
        id_time=datetime.datetime.now(datetime.timezone.utc),
        id_applicationName="admin",
        actor=GWSAuditLogActorInput(email="admin@example.com"),
        ip_address="192.168.1.100",
        events=[GWSAuditLogEventInput(
            name="GRANT_ADMIN_PRIVILEGE",
            type="ADMIN_SETTINGS",
            parameters=[
                GWSAuditLogEventParameterInput(name="USER_EMAIL", value="new_admin@example.com"),
                GWSAuditLogEventParameterInput(name="PRIVILEGE_NAME", value="Super Admin")
            ]
        )]
    )

@pytest.fixture
def login_failure_log_item():
    return GWSAuditLogItemInput(
        id_time=datetime.datetime.now(datetime.timezone.utc),
        id_applicationName="login",
        actor=GWSAuditLogActorInput(email="user_with_bad_pass@example.com"),
        ip_address="10.20.30.40",
        events=[GWSAuditLogEventInput(
            name="login_failure",
            type="LOGIN",
            parameters=[GWSAuditLogEventParameterInput(name="login_type", value="password")]
        )]
    )

@pytest.fixture
def normal_drive_activity_log_item():
    return GWSAuditLogItemInput(
        id_time=datetime.datetime.now(datetime.timezone.utc),
        id_applicationName="drive",
        actor=GWSAuditLogActorInput(email="user@example.com"),
        ip_address="10.0.0.1",
        events=[GWSAuditLogEventInput(
            name="download",
            type="ACCESS",
            parameters=[GWSAuditLogEventParameterInput(name="doc_id", value="doc123")]
        )]
    )

def test_gws_admin_privilege_granted(admin_privilege_granted_log_item):
    log_collection = GWSAuditLogCollectionInput(
        items=[admin_privilege_granted_log_item],
        application_name_queried="admin"
    )
    alerts = evaluate_gws_audit_log_policies(log_collection, CUSTOMER_ID_GWS)

    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["policy_id"] == "GWS_AdminEvent_GRANT_ADMIN_PRIVILEGE"
    assert alert["title"] == "GWS Admin Event: Admin Privilege Granted to User"
    assert alert["severity"] == AlertSeverityEnum.CRITICAL
    assert "new_admin@example.com" in alert["description"]
    assert "Super Admin" in alert["description"]

def test_gws_login_failure_detected(login_failure_log_item):
    log_collection = GWSAuditLogCollectionInput(
        items=[login_failure_log_item],
        application_name_queried="login"
    )
    alerts = evaluate_gws_audit_log_policies(log_collection, CUSTOMER_ID_GWS)

    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["policy_id"] == "GWS_LoginEvent_login_failure"
    assert alert["title"] == "GWS Login Event: User Login Failure Detected"
    assert alert["severity"] == AlertSeverityEnum.MEDIUM
    assert "user_with_bad_pass@example.com" in alert["description"]

def test_gws_normal_drive_activity(normal_drive_activity_log_item):
    log_collection = GWSAuditLogCollectionInput(
        items=[normal_drive_activity_log_item],
        application_name_queried="drive" # Nenhuma política específica para "drive" está definida para gerar alerta
    )
    alerts = evaluate_gws_audit_log_policies(log_collection, CUSTOMER_ID_GWS)
    assert len(alerts) == 0

def test_gws_audit_log_collection_error():
    error_msg = "Failed to fetch GWS audit logs for 'login' app."
    log_collection_error = GWSAuditLogCollectionInput(
        error_message=error_msg,
        application_name_queried="login"
    )
    alerts = evaluate_gws_audit_log_policies(log_collection_error, CUSTOMER_ID_GWS)

    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["policy_id"] == "GWS_AuditLog_GlobalCollection_Error"
    assert alert["severity"] == AlertSeverityEnum.MEDIUM
    assert error_msg in alert["description"]
    assert "login" in alert["description"]

def test_gws_audit_log_item_parsing_error():
    log_item_with_error = GWSAuditLogItemInput(
        id_time=datetime.datetime.now(datetime.timezone.utc),
        id_applicationName="admin",
        collection_error_details="Failed to parse this specific log item."
    )
    log_collection = GWSAuditLogCollectionInput(
        items=[log_item_with_error],
        application_name_queried="admin"
    )
    alerts = evaluate_gws_audit_log_policies(log_collection, CUSTOMER_ID_GWS)

    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["policy_id"] == "GWS_AuditLog_ItemParsing_Error"
    assert alert["severity"] == AlertSeverityEnum.INFORMATIONAL
    assert "Failed to parse this specific log item" in alert["description"]
