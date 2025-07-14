import pytest
import datetime
from policy_engine_service.app.engine.aws_iam_policies import (
    evaluate_iam_user_policies,
    evaluate_iam_role_policies, # Adicionar quando as políticas de role forem testadas
    check_unused_access_keys,
    check_root_user_active_access_key,
    check_user_has_inline_policies,
    check_user_access_key_needs_rotation,
    check_role_has_inline_policies # Adicionar quando for testar
)
from policy_engine_service.app.schemas.input_data_schema import (
    IAMUserDataInput,
    IAMUserAccessKeyMetadataInput,
    IAMUserPolicyInput,
    IAMRoleDataInput # Adicionar quando for testar
)
from policy_engine_service.app.schemas.alert_schema import AlertSeverityEnum

ACCOUNT_ID_AWS = "123456789012"

# --- Fixtures para Usuários IAM ---
@pytest.fixture
def user_with_mfa():
    return IAMUserDataInput(
        UserId="USERIDWITHMFA", UserName="user_with_mfa", Arn=f"arn:aws:iam::{ACCOUNT_ID_AWS}:user/user_with_mfa",
        CreateDate=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=100),
        PasswordEnabled=True, MFADevices=[{"UserName": "user_with_mfa", "SerialNumber": "mfa123", "EnableDate": datetime.datetime.now(datetime.timezone.utc)}]
    )

@pytest.fixture
def user_no_mfa_console_access():
    return IAMUserDataInput(
        UserId="USERIDNOMFA", UserName="user_no_mfa", Arn=f"arn:aws:iam::{ACCOUNT_ID_AWS}:user/user_no_mfa",
        CreateDate=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=100),
        PasswordEnabled=True, MFADevices=[]
    )

@pytest.fixture
def user_no_mfa_no_console_access():
    return IAMUserDataInput(
        UserId="USERIDNOMFAPASS", UserName="user_no_mfa_no_pass", Arn=f"arn:aws:iam::{ACCOUNT_ID_AWS}:user/user_no_mfa_no_pass",
        CreateDate=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=100),
        PasswordEnabled=False, MFADevices=[]
    )

@pytest.fixture
def user_with_active_old_key():
    return IAMUserDataInput(
        UserId="USERIDOLDKEY", UserName="user_old_key", Arn=f"arn:aws:iam::{ACCOUNT_ID_AWS}:user/user_old_key",
        CreateDate=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=200),
        AccessKeys=[
            IAMUserAccessKeyMetadataInput(AccessKeyId="AKIAOLD", Status="Active", CreateDate=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=100)),
            IAMUserAccessKeyMetadataInput(AccessKeyId="AKIAACTIVEBUTNEW", Status="Active", CreateDate=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=10))
        ]
    )

@pytest.fixture
def user_with_unused_key():
    now = datetime.datetime.now(datetime.timezone.utc)
    return IAMUserDataInput(
        UserId="USERIDUNUSEDKEY", UserName="user_unused_key", Arn=f"arn:aws:iam::{ACCOUNT_ID_AWS}:user/user_unused_key",
        CreateDate=now - datetime.timedelta(days=200),
        AccessKeys=[
            IAMUserAccessKeyMetadataInput(AccessKeyId="AKIAUNUSED", Status="Active", CreateDate=now - datetime.timedelta(days=100), last_used_date=now - datetime.timedelta(days=100)),
            IAMUserAccessKeyMetadataInput(AccessKeyId="AKIAUSEDRECENTLY", Status="Active", CreateDate=now - datetime.timedelta(days=100), last_used_date=now - datetime.timedelta(days=10))
        ]
    )

@pytest.fixture
def user_with_never_used_old_key():
    now = datetime.datetime.now(datetime.timezone.utc)
    return IAMUserDataInput(
        UserId="USERIDNEVERUSEDOLDKEY", UserName="user_never_used_old_key", Arn=f"arn:aws:iam::{ACCOUNT_ID_AWS}:user/user_never_used_old_key",
        CreateDate=now - datetime.timedelta(days=200),
        AccessKeys=[
            IAMUserAccessKeyMetadataInput(AccessKeyId="AKIANEVERUSEDOLD", Status="Active", CreateDate=now - datetime.timedelta(days=100), last_used_date=None)
        ]
    )

@pytest.fixture
def user_with_inline_policy():
    return IAMUserDataInput(
        UserId="USERIDINLINE", UserName="user_with_inline", Arn=f"arn:aws:iam::{ACCOUNT_ID_AWS}:user/user_with_inline",
        CreateDate=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30),
        InlinePolicies=[IAMUserPolicyInput(PolicyName="MyInlinePolicy1", policy_document={"Version": "2012-10-17", "Statement": []})]
    )

@pytest.fixture
def root_user_with_active_key(): # Simulação de usuário root
    return IAMUserDataInput(
        UserId=ACCOUNT_ID_AWS, # Heurística: UserId igual ao AccountId para root
        UserName="<root_account>", # Placeholder comum, mas não confiável
        Arn=f"arn:aws:iam::{ACCOUNT_ID_AWS}:root",
        CreateDate=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1000),
        AccessKeys=[IAMUserAccessKeyMetadataInput(AccessKeyId="AKIAROOTACTIVE", Status="Active", CreateDate=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=50))]
    )

# --- Testes para Políticas de Usuário IAM ---
def test_check_user_mfa_disabled_positive(user_no_mfa_console_access):
    alerts = check_user_mfa_disabled(user_no_mfa_console_access, ACCOUNT_ID_AWS)
    assert len(alerts) == 1
    assert alerts[0]["policy_id"] == "IAM_User_Console_Access_Without_MFA"
    assert alerts[0]["severity"] == AlertSeverityEnum.HIGH

def test_check_user_mfa_disabled_negative(user_with_mfa, user_no_mfa_no_console_access):
    assert len(check_user_mfa_disabled(user_with_mfa, ACCOUNT_ID_AWS)) == 0
    assert len(check_user_mfa_disabled(user_no_mfa_no_console_access, ACCOUNT_ID_AWS)) == 0

def test_check_unused_access_keys_positive(user_with_unused_key):
    alerts = check_unused_access_keys(user_with_unused_key, ACCOUNT_ID_AWS)
    assert len(alerts) == 1
    assert alerts[0]["policy_id"] == "IAM_Unused_Access_Key"
    assert alerts[0]["resource_id"] == "AKIAUNUSED"
    assert alerts[0]["details"]["days_inactive_or_since_creation_if_never_used"] == 100

def test_check_unused_access_keys_never_used_old(user_with_never_used_old_key):
    alerts = check_unused_access_keys(user_with_never_used_old_key, ACCOUNT_ID_AWS)
    assert len(alerts) == 1
    assert alerts[0]["policy_id"] == "IAM_Unused_Access_Key"
    assert alerts[0]["resource_id"] == "AKIANEVERUSEDOLD"
    assert alerts[0]["details"]["days_inactive_or_since_creation_if_never_used"] == 100 # Idade da chave

def test_check_root_user_active_access_key_positive(root_user_with_active_key):
    alerts = check_root_user_active_access_key(root_user_with_active_key, ACCOUNT_ID_AWS)
    assert len(alerts) == 1
    assert alerts[0]["policy_id"] == "IAM_Root_Account_Active_Access_Key"
    assert alerts[0]["severity"] == AlertSeverityEnum.CRITICAL

def test_check_user_has_inline_policies_positive(user_with_inline_policy):
    alerts = check_user_has_inline_policies(user_with_inline_policy, ACCOUNT_ID_AWS)
    assert len(alerts) == 1
    assert alerts[0]["policy_id"] == "IAM_User_Has_Inline_Policies"
    assert alerts[0]["details"]["inline_policy_names"] == ["MyInlinePolicy1"]

def test_check_user_access_key_needs_rotation_positive(user_with_active_old_key):
    alerts = check_user_access_key_needs_rotation(user_with_active_old_key, ACCOUNT_ID_AWS)
    assert len(alerts) == 1 # Apenas a chave AKIAOLD
    alert = alerts[0]
    assert alert["policy_id"] == "IAM_User_AccessKey_Needs_Rotation"
    assert alert["resource_id"] == "AKIAOLD"
    assert alert["details"]["age_days"] == 100

# Teste para evaluate_iam_user_policies (função principal)
def test_evaluate_iam_user_policies_multiple_alerts(user_no_mfa_console_access, user_with_active_old_key, user_with_inline_policy):
    users = [user_no_mfa_console_access, user_with_active_old_key, user_with_inline_policy]
    alerts_data = evaluate_iam_user_policies(users, ACCOUNT_ID_AWS)
    # Espera-se: 1 (MFA) + 1 (Rotação Chave) + 1 (Inline) = 3 alertas
    assert len(alerts_data) == 3
    policy_ids_found = [a["policy_id"] for a in alerts_data]
    assert "IAM_User_Console_Access_Without_MFA" in policy_ids_found
    assert "IAM_User_AccessKey_Needs_Rotation" in policy_ids_found
    assert "IAM_User_Has_Inline_Policies" in policy_ids_found


# --- Fixtures para Roles IAM ---
@pytest.fixture
def role_with_inline_policy():
    # O schema IAMRoleDataInput precisa ser definido ou importado corretamente
    # Vou usar os campos que a política espera, mas o schema completo pode ser mais extenso.
    return IAMRoleDataInput(
        Arn=f"arn:aws:iam::{ACCOUNT_ID_AWS}:role/role_with_inline",
        RoleName="role_with_inline",
        Path="/", RoleId="ROLEIDINLINE", CreateDate=datetime.datetime.now(datetime.timezone.utc),
        InlinePolicies=[IAMUserPolicyInput(PolicyName="MyRoleInlinePolicy", policy_document={})]
    )

@pytest.fixture
def role_without_inline_policy():
    return IAMRoleDataInput(
        Arn=f"arn:aws:iam::{ACCOUNT_ID_AWS}:role/role_no_inline",
        RoleName="role_no_inline",
        Path="/", RoleId="ROLEIDNOINLINE", CreateDate=datetime.datetime.now(datetime.timezone.utc),
        InlinePolicies=[]
    )

# --- Testes para Políticas de Role IAM ---
def test_check_role_has_inline_policies_positive(role_with_inline_policy):
    alerts = check_role_has_inline_policies(role_with_inline_policy, ACCOUNT_ID_AWS) # A função check retorna Alert, não dict
    assert alerts is not None # Deve retornar um único alerta
    assert alerts.policy_id == "IAM_Role_Has_Inline_Policies"
    assert alerts.details["inline_policy_names"] == ["MyRoleInlinePolicy"]

def test_check_role_has_inline_policies_negative(role_without_inline_policy):
    alerts = check_role_has_inline_policies(role_without_inline_policy, ACCOUNT_ID_AWS)
    assert alerts is None

# Teste para evaluate_iam_role_policies
def test_evaluate_iam_role_policies(role_with_inline_policy, role_without_inline_policy):
    roles = [role_with_inline_policy, role_without_inline_policy]
    alerts_data = evaluate_iam_role_policies(roles, ACCOUNT_ID_AWS)
    assert len(alerts_data) == 1
    assert alerts_data[0]["policy_id"] == "IAM_Role_Has_Inline_Policies"
