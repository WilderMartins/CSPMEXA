import pytest
from policy_engine_service.app.engine.m365_policies import evaluate_m365_policies, check_m365_user_mfa_disabled, check_m365_ca_policy_disabled
from policy_engine_service.app.schemas.m365.m365_input_schemas import (
    M365UserMFADetailInput,
    M365UserMFAStatusCollectionInput,
    M365ConditionalAccessPolicyDetailInput,
    M365ConditionalAccessPolicyCollectionInput
)
from policy_engine_service.app.schemas.alert_schema import AlertSeverityEnum

TENANT_ID_TEST = "test-tenant-123"

@pytest.fixture
def sample_user_mfa_data_ok():
    return M365UserMFADetailInput(
        id="user1", userPrincipalName="user1@contoso.com", displayName="User One",
        is_mfa_registered=True, is_mfa_enabled_via_policies=True, mfa_state="Enforced"
    )

@pytest.fixture
def sample_user_mfa_not_registered():
    return M365UserMFADetailInput(
        id="user2", userPrincipalName="user2@contoso.com", displayName="User Two",
        is_mfa_registered=False, is_mfa_enabled_via_policies=False, mfa_state="NotRegistered"
    )

@pytest.fixture
def sample_user_mfa_registered_not_enforced():
    return M365UserMFADetailInput(
        id="user3", userPrincipalName="user3@contoso.com", displayName="User Three",
        is_mfa_registered=True, is_mfa_enabled_via_policies=False, mfa_state="RegisteredNotEnforcedBySecurityDefaults"
    )

@pytest.fixture
def sample_ca_policy_enabled():
    return M365ConditionalAccessPolicyDetailInput(
        id="ca_policy1", displayName="CA Policy Enabled", state="enabled"
    )

@pytest.fixture
def sample_ca_policy_disabled():
    return M365ConditionalAccessPolicyDetailInput(
        id="ca_policy2", displayName="CA Policy Disabled", state="disabled"
    )

@pytest.fixture
def sample_ca_policy_report_only():
    return M365ConditionalAccessPolicyDetailInput(
        id="ca_policy3", displayName="CA Policy Report Only", state="enabledForReportingButNotEnforced"
    )

# Testes para check_m365_user_mfa_disabled
def test_mfa_disabled_user_not_registered(sample_user_mfa_not_registered):
    alerts = check_m365_user_mfa_disabled(sample_user_mfa_not_registered, TENANT_ID_TEST)
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["policy_id"] == "M365_User_MFA_Status_Issue"
    assert alert["severity"] == AlertSeverityEnum.CRITICAL
    assert "does not have MFA registered" in alert["description"]
    assert alert["resource_id"] == sample_user_mfa_not_registered.user_id

def test_mfa_disabled_user_registered_not_enforced(sample_user_mfa_registered_not_enforced):
    alerts = check_m365_user_mfa_disabled(sample_user_mfa_registered_not_enforced, TENANT_ID_TEST)
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["policy_id"] == "M365_User_MFA_Status_Issue"
    assert alert["severity"] == AlertSeverityEnum.MEDIUM
    assert "might not be enforced for all sign-ins" in alert["description"]

def test_mfa_disabled_user_ok(sample_user_mfa_data_ok):
    alerts = check_m365_user_mfa_disabled(sample_user_mfa_data_ok, TENANT_ID_TEST)
    assert len(alerts) == 0

# Testes para check_m365_ca_policy_disabled
def test_ca_policy_disabled(sample_ca_policy_disabled):
    alerts = check_m365_ca_policy_disabled(sample_ca_policy_disabled, TENANT_ID_TEST)
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["policy_id"] == "M365_ConditionalAccess_Policy_Disabled"
    assert alert["severity"] == AlertSeverityEnum.MEDIUM
    assert "is currently disabled" in alert["description"]
    assert alert["resource_id"] == sample_ca_policy_disabled.id

def test_ca_policy_report_only(sample_ca_policy_report_only):
    alerts = check_m365_ca_policy_disabled(sample_ca_policy_report_only, TENANT_ID_TEST)
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["policy_id"] == "M365_ConditionalAccess_Policy_ReportOnly"
    assert alert["severity"] == AlertSeverityEnum.INFORMATIONAL
    assert "is in 'Report-only' mode" in alert["description"]

def test_ca_policy_enabled(sample_ca_policy_enabled):
    alerts = check_m365_ca_policy_disabled(sample_ca_policy_enabled, TENANT_ID_TEST)
    assert len(alerts) == 0

# Testes para evaluate_m365_policies (função principal)
def test_evaluate_m365_policies_all_ok(sample_user_mfa_data_ok, sample_ca_policy_enabled):
    mfa_collection = M365UserMFAStatusCollectionInput(users_mfa_status=[sample_user_mfa_data_ok])
    ca_collection = M365ConditionalAccessPolicyCollectionInput(policies=[sample_ca_policy_enabled])

    alerts = evaluate_m365_policies(mfa_data=mfa_collection, ca_policy_data=ca_collection, tenant_id=TENANT_ID_TEST)
    assert len(alerts) == 0

def test_evaluate_m365_policies_with_issues(sample_user_mfa_not_registered, sample_ca_policy_disabled, sample_ca_policy_report_only):
    mfa_collection = M365UserMFAStatusCollectionInput(users_mfa_status=[sample_user_mfa_not_registered])
    ca_collection = M365ConditionalAccessPolicyCollectionInput(policies=[sample_ca_policy_disabled, sample_ca_policy_report_only])

    alerts = evaluate_m365_policies(mfa_data=mfa_collection, ca_policy_data=ca_collection, tenant_id=TENANT_ID_TEST)
    assert len(alerts) == 3 # 1 MFA + 1 CA Disabled + 1 CA ReportOnly

    assert any(a["policy_id"] == "M365_User_MFA_Status_Issue" and a["severity"] == AlertSeverityEnum.CRITICAL for a in alerts)
    assert any(a["policy_id"] == "M365_ConditionalAccess_Policy_Disabled" and a["severity"] == AlertSeverityEnum.MEDIUM for a in alerts)
    assert any(a["policy_id"] == "M365_ConditionalAccess_Policy_ReportOnly" and a["severity"] == AlertSeverityEnum.INFORMATIONAL for a in alerts)

def test_evaluate_m365_policies_mfa_collection_error(sample_ca_policy_enabled):
    mfa_collection_error = M365UserMFAStatusCollectionInput(error_message="Global MFA collection failed")
    ca_collection = M365ConditionalAccessPolicyCollectionInput(policies=[sample_ca_policy_enabled])

    alerts = evaluate_m365_policies(mfa_data=mfa_collection_error, ca_policy_data=ca_collection, tenant_id=TENANT_ID_TEST)
    assert len(alerts) == 1
    assert alerts[0]["policy_id"] == "M365_MFA_GlobalCollection_Error"
    assert alerts[0]["severity"] == AlertSeverityEnum.MEDIUM

def test_evaluate_m365_policies_ca_collection_error(sample_user_mfa_data_ok):
    mfa_collection = M365UserMFAStatusCollectionInput(users_mfa_status=[sample_user_mfa_data_ok])
    ca_collection_error = M365ConditionalAccessPolicyCollectionInput(error_message="Global CA policy collection failed")

    alerts = evaluate_m365_policies(mfa_data=mfa_collection, ca_policy_data=ca_collection_error, tenant_id=TENANT_ID_TEST)
    assert len(alerts) == 1
    assert alerts[0]["policy_id"] == "M365_CAPolicy_GlobalCollection_Error"
    assert alerts[0]["severity"] == AlertSeverityEnum.MEDIUM

def test_evaluate_m365_policies_individual_item_error(sample_user_mfa_data_ok, sample_ca_policy_enabled):
    user_mfa_with_error = M365UserMFADetailInput(
        user_id="user_err", userPrincipalName="err@contoso.com", error_details="Cannot fetch this user"
    )
    ca_policy_with_error = M365ConditionalAccessPolicyDetailInput(
        id="ca_err", displayName="Error Policy", state="enabled", error_details="Cannot fetch this policy"
    )
    mfa_collection = M365UserMFAStatusCollectionInput(users_mfa_status=[sample_user_mfa_data_ok, user_mfa_with_error])
    ca_collection = M365ConditionalAccessPolicyCollectionInput(policies=[sample_ca_policy_enabled, ca_policy_with_error])

    alerts = evaluate_m365_policies(mfa_data=mfa_collection, ca_policy_data=ca_collection, tenant_id=TENANT_ID_TEST)
    assert len(alerts) == 2 # 1 for MFA item error, 1 for CA item error
    assert any(a["policy_id"] == "M365_MFA_Collection_Error" and a["resource_id"] == "err@contoso.com" for a in alerts)
    assert any(a["policy_id"] == "M365_CAPolicy_Collection_Error" and a["resource_id"] == "ca_err" for a in alerts)

def test_evaluate_m365_policies_no_data():
    alerts = evaluate_m365_policies(mfa_data=None, ca_policy_data=None, tenant_id=TENANT_ID_TEST)
    assert len(alerts) == 0

    mfa_empty_collection = M365UserMFAStatusCollectionInput(users_mfa_status=[])
    ca_empty_collection = M365ConditionalAccessPolicyCollectionInput(policies=[])
    alerts = evaluate_m365_policies(mfa_data=mfa_empty_collection, ca_policy_data=ca_empty_collection, tenant_id=TENANT_ID_TEST)
    assert len(alerts) == 0
