import pytest
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta

from app.schemas.input_data_schema import (
    HuaweiIAMUserDataInput, HuaweiIAMUserLoginProtectInput, HuaweiIAMUserAccessKeyInput
)
from app.schemas.alert_schema import Alert
from app.engine.huawei_iam_policies import (
    evaluate_huawei_iam_user_policies,
    HuaweiIAMUserMFADisabledPolicy,
    HuaweiIAMUserInactiveAccessKeyPolicy
    # Adicionar HuaweiIAMRootUserActiveAccessKeyPolicy se implementada e testável sem dados reais de root
)

# --- Fixtures de Dados de Teste para Huawei IAM ---

@pytest.fixture
def secure_huawei_iam_user_input() -> HuaweiIAMUserDataInput:
    """Retorna um HuaweiIAMUserDataInput seguro por padrão."""
    now = datetime.now(timezone.utc)
    return HuaweiIAMUserDataInput(
        id="user-secure-id",
        name="secure-huawei-user",
        domain_id="domain-123",
        enabled=True,
        login_protect=HuaweiIAMUserLoginProtectInput(enabled=True, verification_method="vmfa"), # MFA habilitado
        access_keys=[ # Chave ativa, mas não temos info de último uso para esta política no MVP
            HuaweiIAMUserAccessKeyInput(
                access="AK_SECURE_ACTIVE",
                status="Active",
                create_time_format=(now - timedelta(days=30))
            )
        ]
    )

# --- Testes para Políticas de Usuário IAM ---

def test_huawei_iam_user_mfa_disabled_policy_no_violation(secure_huawei_iam_user_input: HuaweiIAMUserDataInput):
    policy = HuaweiIAMUserMFADisabledPolicy()
    alert = policy.check(secure_huawei_iam_user_input, "domain-123")
    assert alert is None

def test_huawei_iam_user_mfa_disabled_policy_with_violation_disabled(secure_huawei_iam_user_input: HuaweiIAMUserDataInput):
    policy = HuaweiIAMUserMFADisabledPolicy()
    secure_huawei_iam_user_input.login_protect = HuaweiIAMUserLoginProtectInput(enabled=False, verification_method="sms") # MFA desabilitado
    alert = policy.check(secure_huawei_iam_user_input, "domain-123")
    assert alert is not None
    assert alert.policy_id == "HUAWEI_IAM_User_MFA_Disabled"
    assert alert.severity == "High"

def test_huawei_iam_user_mfa_disabled_policy_with_violation_none(secure_huawei_iam_user_input: HuaweiIAMUserDataInput):
    policy = HuaweiIAMUserMFADisabledPolicy()
    secure_huawei_iam_user_input.login_protect = None # login_protect não configurado
    alert = policy.check(secure_huawei_iam_user_input, "domain-123")
    assert alert is not None
    assert alert.policy_id == "HUAWEI_IAM_User_MFA_Disabled"
    assert "Disabled or Not Configured" in alert.details.get("mfa_console_status", "")


def test_huawei_iam_user_inactive_access_key_policy_no_active_keys(secure_huawei_iam_user_input: HuaweiIAMUserDataInput):
    policy = HuaweiIAMUserInactiveAccessKeyPolicy()
    secure_huawei_iam_user_input.access_keys = [] # Sem chaves
    alert = policy.check(secure_huawei_iam_user_input, "domain-123")
    assert alert is None

def test_huawei_iam_user_inactive_access_key_policy_all_active_keys(secure_huawei_iam_user_input: HuaweiIAMUserDataInput):
    policy = HuaweiIAMUserInactiveAccessKeyPolicy()
    # Fixture já tem uma chave ativa (e a política foca em inativas)
    alert = policy.check(secure_huawei_iam_user_input, "domain-123")
    assert alert is None


def test_huawei_iam_user_inactive_access_key_policy_with_inactive_key_violation(secure_huawei_iam_user_input: HuaweiIAMUserDataInput):
    policy = HuaweiIAMUserInactiveAccessKeyPolicy()
    now = datetime.now(timezone.utc)
    secure_huawei_iam_user_input.access_keys = [
        HuaweiIAMUserAccessKeyInput(access="AK_INACTIVE", status="Inactive", create_time_format=(now - timedelta(days=100))),
        HuaweiIAMUserAccessKeyInput(access="AK_ACTIVE_OK", status="Active", create_time_format=(now - timedelta(days=10)))
    ]
    alert = policy.check(secure_huawei_iam_user_input, "domain-123")
    assert alert is not None
    assert alert.policy_id == "HUAWEI_IAM_User_Inactive_Access_Key"
    assert "AK_INACTIVE' is Inactive" in alert.description
    assert "AK_ACTIVE_OK" not in alert.description # Não deve mencionar a ativa

# Teste para a parte de "não usada por X dias" (atualmente não implementável completamente)
def test_huawei_iam_user_inactive_access_key_policy_active_key_no_last_used_info(secure_huawei_iam_user_input: HuaweiIAMUserDataInput):
    policy = HuaweiIAMUserInactiveAccessKeyPolicy(inactive_days_threshold=30)
    now = datetime.now(timezone.utc)
    # Chave ativa, criada há muito tempo, sem info de último uso.
    # A política atual apenas pega chaves 'Inactive'.
    secure_huawei_iam_user_input.access_keys = [
        HuaweiIAMUserAccessKeyInput(access="AK_ACTIVE_OLD_NO_LAST_USE", status="Active", create_time_format=(now - timedelta(days=100)))
    ]
    alert = policy.check(secure_huawei_iam_user_input, "domain-123")
    assert alert is None # Pois a política atual só foca em 'Inactive'


# --- Testes para evaluate_huawei_iam_user_policies ---

def test_evaluate_huawei_iam_user_policies_no_users():
    alerts = evaluate_huawei_iam_user_policies([], "domain-123")
    assert alerts == []

def test_evaluate_huawei_iam_user_policies_one_secure_user(secure_huawei_iam_user_input: HuaweiIAMUserDataInput):
    alerts = evaluate_huawei_iam_user_policies([secure_huawei_iam_user_input], "domain-123")
    assert alerts == []

def test_evaluate_huawei_iam_user_policies_one_user_multiple_violations():
    now = datetime.now(timezone.utc)
    vulnerable_user = HuaweiIAMUserDataInput(
        id="vuln-user-id", name="vulnerable-huawei-user", domain_id="domain-vuln", enabled=True,
        login_protect=HuaweiIAMUserLoginProtectInput(enabled=False, verification_method=None), # Violação MFA
        access_keys=[
            HuaweiIAMUserAccessKeyInput(access="AK_VULN_INACTIVE", status="Inactive", create_time_format=(now - timedelta(days=50))), # Violação Chave Inativa
            HuaweiIAMUserAccessKeyInput(access="AK_VULN_ACTIVE", status="Active", create_time_format=(now - timedelta(days=10)))
        ]
    )
    alerts = evaluate_huawei_iam_user_policies([vulnerable_user], "domain-vuln")

    assert len(alerts) == 2
    policy_ids_found = {alert.policy_id for alert in alerts}
    expected_policy_ids = {
        "HUAWEI_IAM_User_MFA_Disabled",
        "HUAWEI_IAM_User_Inactive_Access_Key"
    }
    assert policy_ids_found == expected_policy_ids

def test_evaluate_huawei_iam_user_policies_skips_user_with_error(secure_huawei_iam_user_input: HuaweiIAMUserDataInput):
    user_with_error = HuaweiIAMUserDataInput(
        id="error-user-id", name="error-iam-user", domain_id="domain-err", enabled=True,
        error_details="Simulated Huawei IAM collection error"
    )
    alerts = evaluate_huawei_iam_user_policies([user_with_error, secure_huawei_iam_user_input], "domain-mixed")
    assert len(alerts) == 0 # Erro é pulado, seguro não gera alertas
```

Ajustes feitos durante a escrita dos testes em `huawei_iam_policies.py`:
*   Na política `HuaweiIAMUserInactiveAccessKeyPolicy`, a descrição e o título foram ajustados para refletir que, devido à falta de dados de "último uso" do coletor, ela primariamente identifica chaves com status "Inactive". A lógica de "não usada por X dias" para chaves ativas foi comentada, pois não é implementável sem esses dados.
*   O `account_id` passado para `policy.check` (que é o `domain_id` para IAM Huawei) é usado no alerta.

Este arquivo agora contém testes para as políticas de usuários IAM da Huawei Cloud implementadas.
