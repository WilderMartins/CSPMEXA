import pytest
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone

from app.schemas.input_data_schema import (
    IAMUserDataInput, IAMUserAccessKeyMetadataInput, IAMUserMFADeviceInput
)
from app.schemas.alert_schema import Alert
from app.engine.aws_iam_policies import (
    evaluate_iam_user_policies,
    IAMUserMFADisabledPolicy,
    IAMUserUnusedAccessKeysPolicy,
    IAMRootUserActiveAccessKeyPolicy
)

# --- Fixtures de Dados de Teste para IAM ---

@pytest.fixture
def basic_iam_user_input() -> IAMUserDataInput:
    """Retorna um IAMUserDataInput básico e seguro por padrão."""
    now = datetime.now(timezone.utc)
    return IAMUserDataInput(
        user_id="AIDACKCEVSQ6C2EXAMPLE",
        user_name="test-secure-user",
        arn="arn:aws:iam::123456789012:user/test-secure-user",
        create_date=now - timedelta(days=100),
        password_last_used=now - timedelta(days=10),
        attached_policies=[],
        inline_policies=[],
        mfa_devices=[IAMUserMFADeviceInput( # MFA Habilitado
            user_name="test-secure-user",
            serial_number="arn:aws:iam::123456789012:mfa/test-secure-user",
            enable_date=now - timedelta(days=30)
        )],
        access_keys=[IAMUserAccessKeyMetadataInput( # Chave ativa, mas usada recentemente
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            status="Active",
            create_date=now - timedelta(days=60),
            last_used_date=now - timedelta(days=5)
        )],
        tags=[],
        error_details=None
    )

@pytest.fixture
def root_user_arn(account_id="123456789012") -> str:
    return f"arn:aws:iam::{account_id}:root"

@pytest.fixture
def root_user_input(root_user_arn: str) -> IAMUserDataInput:
    """Retorna um IAMUserDataInput representando o usuário root, inicialmente seguro."""
    now = datetime.now(timezone.utc)
    return IAMUserDataInput(
        user_id="ROOT_USER_ID_PLACEHOLDER", # O ID do root não é um 'AID...' típico
        user_name="<root_account>", # Nome comum para representar o root
        arn=root_user_arn,
        create_date=now - timedelta(days=1000), # Data de criação da conta
        password_last_used=now - timedelta(days=1),
        attached_policies=[], # Root não deve ter políticas diretamente anexadas assim
        inline_policies=[],
        mfa_devices=[IAMUserMFADeviceInput(
            user_name="<root_account>",
            serial_number=f"arn:aws:iam::{root_user_arn.split(':')[4]}:mfa/root-account-mfa-device",
            enable_date=now - timedelta(days=500)
        )],
        access_keys=[], # Sem chaves de acesso por padrão para root
        tags=[],
        error_details=None
    )


# --- Testes para Políticas de Usuário IAM ---

def test_iam_user_mfa_disabled_policy_no_violation(basic_iam_user_input: IAMUserDataInput):
    policy = IAMUserMFADisabledPolicy()
    alert = policy.check(basic_iam_user_input, "123456789012")
    assert alert is None

def test_iam_user_mfa_disabled_policy_with_violation(basic_iam_user_input: IAMUserDataInput):
    policy = IAMUserMFADisabledPolicy()
    basic_iam_user_input.mfa_devices = [] # Sem MFA
    alert = policy.check(basic_iam_user_input, "123456789012")
    assert alert is not None
    assert alert.policy_id == "IAM_User_MFA_Disabled"
    assert alert.severity == "High" # Para usuário normal

def test_iam_user_mfa_disabled_policy_root_user_violation(root_user_input: IAMUserDataInput):
    policy = IAMUserMFADisabledPolicy()
    root_user_input.mfa_devices = [] # Root sem MFA
    alert = policy.check(root_user_input, root_user_input.arn.split(':')[4])
    assert alert is not None
    assert alert.policy_id == "IAM_User_MFA_Disabled"
    assert alert.severity == "Critical" # Deve ser Crítico para root
    assert "(Usuário Root)" in alert.title


def test_iam_user_unused_access_keys_policy_no_violation(basic_iam_user_input: IAMUserDataInput):
    policy = IAMUserUnusedAccessKeysPolicy(unused_days_threshold=90)
    # Fixture tem chave usada há 5 dias
    alert = policy.check(basic_iam_user_input, "123456789012")
    assert alert is None

def test_iam_user_unused_access_keys_policy_violation_old_last_used(basic_iam_user_input: IAMUserDataInput):
    policy = IAMUserUnusedAccessKeysPolicy(unused_days_threshold=90)
    now = datetime.now(timezone.utc)
    basic_iam_user_input.access_keys = [IAMUserAccessKeyMetadataInput(
        access_key_id="AKIAOLDEXAMPLE", status="Active",
        create_date=now - timedelta(days=200),
        last_used_date=now - timedelta(days=100) # Não usada por 100 dias
    )]
    alert = policy.check(basic_iam_user_input, "123456789012")
    assert alert is not None
    assert alert.policy_id == "IAM_User_Unused_Access_Keys"
    assert "AKIAOLDEXAMPLE" in alert.description

def test_iam_user_unused_access_keys_policy_violation_never_used_old_key(basic_iam_user_input: IAMUserDataInput):
    policy = IAMUserUnusedAccessKeysPolicy(unused_days_threshold=30) # Threshold menor para teste
    now = datetime.now(timezone.utc)
    basic_iam_user_input.access_keys = [IAMUserAccessKeyMetadataInput(
        access_key_id="AKIANEVERUSED", status="Active",
        create_date=now - timedelta(days=40), # Criada há 40 dias
        last_used_date=None # Nunca usada
    )]
    alert = policy.check(basic_iam_user_input, "123456789012")
    assert alert is not None
    assert alert.policy_id == "IAM_User_Unused_Access_Keys"
    assert "AKIANEVERUSED (nunca utilizada" in alert.description

def test_iam_user_unused_access_keys_policy_no_violation_never_used_new_key(basic_iam_user_input: IAMUserDataInput):
    policy = IAMUserUnusedAccessKeysPolicy(unused_days_threshold=90)
    now = datetime.now(timezone.utc)
    basic_iam_user_input.access_keys = [IAMUserAccessKeyMetadataInput(
        access_key_id="AKIANEWEXAMPLE", status="Active",
        create_date=now - timedelta(days=10), # Criada há 10 dias, nunca usada
        last_used_date=None
    )]
    alert = policy.check(basic_iam_user_input, "123456789012")
    assert alert is None # Não deve alertar para chaves novas nunca usadas ainda


def test_iam_root_user_active_access_key_policy_no_violation(root_user_input: IAMUserDataInput):
    policy = IAMRootUserActiveAccessKeyPolicy()
    # Fixture root_user_input não tem chaves de acesso
    alert = policy.check(root_user_input, root_user_input.arn.split(':')[4])
    assert alert is None

def test_iam_root_user_active_access_key_policy_with_violation(root_user_input: IAMUserDataInput):
    policy = IAMRootUserActiveAccessKeyPolicy()
    now = datetime.now(timezone.utc)
    root_user_input.access_keys = [IAMUserAccessKeyMetadataInput(
        access_key_id="AKIAFORROOTEXAMPLE", status="Active", # Chave ativa para root
        create_date=now - timedelta(days=10)
    )]
    alert = policy.check(root_user_input, root_user_input.arn.split(':')[4])
    assert alert is not None
    assert alert.policy_id == "IAM_Root_User_Active_Access_Key"
    assert alert.severity == "Critical"
    assert "AKIAFORROOTEXAMPLE" in alert.description

def test_iam_root_user_active_access_key_policy_not_root_user(basic_iam_user_input: IAMUserDataInput):
    policy = IAMRootUserActiveAccessKeyPolicy()
    now = datetime.now(timezone.utc)
    # Usuário normal com chave ativa não deve disparar esta política específica do root
    basic_iam_user_input.access_keys = [IAMUserAccessKeyMetadataInput(
        access_key_id="AKIAFORNORMALUSER", status="Active",
        create_date=now - timedelta(days=10)
    )]
    alert = policy.check(basic_iam_user_input, "123456789012")
    assert alert is None


# --- Testes para a função evaluate_iam_user_policies ---

def test_evaluate_iam_user_policies_no_users():
    alerts = evaluate_iam_user_policies([], "123456789012")
    assert alerts == []

def test_evaluate_iam_user_policies_one_secure_user(basic_iam_user_input: IAMUserDataInput):
    alerts = evaluate_iam_user_policies([basic_iam_user_input], "123456789012")
    assert alerts == [] # Nenhuma violação esperada

def test_evaluate_iam_user_policies_one_user_multiple_violations(basic_iam_user_input: IAMUserDataInput, root_user_input: IAMUserDataInput):
    user_vulnerable = basic_iam_user_input
    user_vulnerable.user_name = "vulnerable-user"
    user_vulnerable.arn = "arn:aws:iam::123456789012:user/vulnerable-user"
    user_vulnerable.mfa_devices = [] # Violação de MFA

    now = datetime.now(timezone.utc)
    user_vulnerable.access_keys = [IAMUserAccessKeyMetadataInput( # Violação de chave não usada
        access_key_id="AKIAVULNEXAMPLE", status="Active",
        create_date=now - timedelta(days=200),
        last_used_date=now - timedelta(days=100)
    )]

    # Root user com chave ativa
    root_user_vulnerable = root_user_input
    root_user_vulnerable.access_keys = [IAMUserAccessKeyMetadataInput(
        access_key_id="AKIAFORROOTVULN", status="Active", create_date=now - timedelta(days=5)
    )]
    root_user_vulnerable.mfa_devices = [] # Root sem MFA também

    all_users = [user_vulnerable, root_user_vulnerable]
    alerts = evaluate_iam_user_policies(all_users, "123456789012")

    # Esperado:
    # user_vulnerable: MFA disabled (High), Unused Key (Medium) = 2 alertas
    # root_user_vulnerable: Root Active Key (Critical), MFA disabled (Critical) = 2 alertas
    assert len(alerts) == 4

    policy_ids_found = sorted([alert.policy_id for alert in alerts])
    expected_policy_ids = sorted([
        "IAM_User_MFA_Disabled", "IAM_User_Unused_Access_Keys", # para user_vulnerable
        "IAM_Root_User_Active_Access_Key", "IAM_User_MFA_Disabled"  # para root_user_vulnerable
    ])
    assert policy_ids_found == expected_policy_ids

    # Verificar severidades para o root
    root_alerts = [a for a in alerts if a.resource_id == root_user_vulnerable.arn]
    assert len(root_alerts) == 2
    for alert in root_alerts:
        assert alert.severity == "Critical"


def test_evaluate_iam_user_policies_skips_user_with_error_details(basic_iam_user_input: IAMUserDataInput):
    user_with_error = IAMUserDataInput(
        user_id="ERRORUSERID", user_name="error-user", arn="arn:aws:iam::123456789012:user/error-user",
        create_date=datetime.now(),
        error_details="Simulated collection error for this user."
    )
    alerts = evaluate_iam_user_policies([user_with_error, basic_iam_user_input], "123456789012")
    assert len(alerts) == 0 # O com erro é pulado, o básico é seguro
