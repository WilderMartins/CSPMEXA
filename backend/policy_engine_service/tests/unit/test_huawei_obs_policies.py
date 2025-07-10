import pytest
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from app.schemas.input_data_schema import (
    HuaweiOBSBucketDataInput, HuaweiOBSBucketPolicyInput, HuaweiOBSBucketPolicyStatementInput,
    HuaweiOBSBucketACLInput, HuaweiOBSGrantInput, HuaweiOBSGranteeInput, HuaweiOBSOwnerInput,
    HuaweiOBSBucketVersioningInput, HuaweiOBSBucketLoggingInput
)
from app.schemas.alert_schema import Alert
from app.engine.huawei_obs_policies import (
    evaluate_huawei_obs_policies,
    HuaweiOBSBucketPublicAccessPolicy,
    HuaweiOBSBucketVersioningDisabledPolicy,
    HuaweiOBSBucketLoggingDisabledPolicy
)

# --- Fixtures de Dados de Teste para Huawei OBS ---

@pytest.fixture
def secure_huawei_obs_bucket_input() -> HuaweiOBSBucketDataInput:
    """Retorna um HuaweiOBSBucketDataInput seguro por padrão."""
    now = datetime.now(timezone.utc)
    return HuaweiOBSBucketDataInput(
        name="secure-huawei-bucket",
        creation_date=now,
        location="ap-southeast-1",
        storage_class="STANDARD",
        bucket_policy=HuaweiOBSBucketPolicyInput( # Política não pública
            Version="1",
            Statement=[HuaweiOBSBucketPolicyStatementInput(
                Sid="InternalAccess", Effect="Allow",
                Principal={"HUAWEI": ["user-id-internal"]}, # Exemplo de principal interno
                Action=["obs:GetObject"], Resource=["secure-huawei-bucket/*"]
            )]
        ),
        acl=HuaweiOBSBucketACLInput( # ACL não pública
            Owner=HuaweiOBSOwnerInput(ID="owner-id"),
            grants=[]
        ),
        versioning=HuaweiOBSBucketVersioningInput(status="Enabled"),
        logging=HuaweiOBSBucketLoggingInput(enabled=True, target_bucket="log-bucket-huawei", target_prefix="logs/"),
        is_public_by_policy=False, # Preenchido pelo collector
        public_policy_details=[],
        is_public_by_acl=False, # Preenchido pelo collector
        public_acl_details=[],
        error_details=None
    )

# --- Testes para Políticas Individuais ---

def test_huawei_obs_bucket_public_access_policy_no_violation(secure_huawei_obs_bucket_input: HuaweiOBSBucketDataInput):
    policy = HuaweiOBSBucketPublicAccessPolicy()
    alert = policy.check(secure_huawei_obs_bucket_input, "test-project-or-domain-id")
    assert alert is None

def test_huawei_obs_bucket_public_access_policy_via_policy(secure_huawei_obs_bucket_input: HuaweiOBSBucketDataInput):
    policy_checker = HuaweiOBSBucketPublicAccessPolicy()
    secure_huawei_obs_bucket_input.is_public_by_policy = True # Simula detecção pelo collector
    secure_huawei_obs_bucket_input.public_policy_details = ["Policy grants public access to Principal '*'"]
    secure_huawei_obs_bucket_input.bucket_policy = HuaweiOBSBucketPolicyInput(
        Statement=[HuaweiOBSBucketPolicyStatementInput(Effect="Allow", Principal={"HUAWEI": ["*"]}, Action=["obs:GetObject"], Resource=["target-bucket/*"] )]
    )

    alert = policy_checker.check(secure_huawei_obs_bucket_input, "test-project-id")
    assert alert is not None
    assert alert.policy_id == "HUAWEI_OBS_Bucket_Public_Access"
    assert "Policy: " in alert.description

def test_huawei_obs_bucket_public_access_policy_via_acl(secure_huawei_obs_bucket_input: HuaweiOBSBucketDataInput):
    policy_checker = HuaweiOBSBucketPublicAccessPolicy()
    secure_huawei_obs_bucket_input.is_public_by_acl = True # Simula detecção pelo collector
    secure_huawei_obs_bucket_input.public_acl_details = ["ACL grants READ to Everyone"]
    # Simular uma ACL pública (a estrutura exata do grantee para 'Everyone' precisa ser confirmada)
    secure_huawei_obs_bucket_input.acl = HuaweiOBSBucketACLInput(
        Owner=HuaweiOBSOwnerInput(ID="owner"),
        grants=[HuaweiOBSGrantInput(grantee=HuaweiOBSGranteeInput(URI="URI_FOR_EVERYONE_HUAWEI"), permission="READ")]
    )

    alert = policy_checker.check(secure_huawei_obs_bucket_input, "test-project-id")
    assert alert is not None
    assert alert.policy_id == "HUAWEI_OBS_Bucket_Public_Access"
    assert "ACL: " in alert.description


def test_huawei_obs_bucket_versioning_disabled_no_violation(secure_huawei_obs_bucket_input: HuaweiOBSBucketDataInput):
    policy = HuaweiOBSBucketVersioningDisabledPolicy()
    alert = policy.check(secure_huawei_obs_bucket_input, "test-project-id")
    assert alert is None

def test_huawei_obs_bucket_versioning_disabled_with_violation_suspended(secure_huawei_obs_bucket_input: HuaweiOBSBucketDataInput):
    policy = HuaweiOBSBucketVersioningDisabledPolicy()
    secure_huawei_obs_bucket_input.versioning = HuaweiOBSBucketVersioningInput(status="Suspended")
    alert = policy.check(secure_huawei_obs_bucket_input, "test-project-id")
    assert alert is not None
    assert alert.policy_id == "HUAWEI_OBS_Bucket_Versioning_Disabled"
    assert "Status atual: Suspended" in alert.description

def test_huawei_obs_bucket_versioning_disabled_with_violation_none(secure_huawei_obs_bucket_input: HuaweiOBSBucketDataInput):
    policy = HuaweiOBSBucketVersioningDisabledPolicy()
    secure_huawei_obs_bucket_input.versioning = None
    alert = policy.check(secure_huawei_obs_bucket_input, "test-project-id")
    assert alert is not None
    assert alert.policy_id == "HUAWEI_OBS_Bucket_Versioning_Disabled"
    assert "Status atual: Não Configurado" in alert.description


def test_huawei_obs_bucket_logging_disabled_no_violation(secure_huawei_obs_bucket_input: HuaweiOBSBucketDataInput):
    policy = HuaweiOBSBucketLoggingDisabledPolicy()
    alert = policy.check(secure_huawei_obs_bucket_input, "test-project-id")
    assert alert is None

def test_huawei_obs_bucket_logging_disabled_with_violation(secure_huawei_obs_bucket_input: HuaweiOBSBucketDataInput):
    policy = HuaweiOBSBucketLoggingDisabledPolicy()
    secure_huawei_obs_bucket_input.logging = HuaweiOBSBucketLoggingInput(enabled=False)
    alert = policy.check(secure_huawei_obs_bucket_input, "test-project-id")
    assert alert is not None
    assert alert.policy_id == "HUAWEI_OBS_Bucket_Logging_Disabled"

def test_huawei_obs_bucket_logging_disabled_logging_none(secure_huawei_obs_bucket_input: HuaweiOBSBucketDataInput):
    policy = HuaweiOBSBucketLoggingDisabledPolicy()
    secure_huawei_obs_bucket_input.logging = None
    alert = policy.check(secure_huawei_obs_bucket_input, "test-project-id")
    assert alert is not None
    assert alert.policy_id == "HUAWEI_OBS_Bucket_Logging_Disabled"
    assert "logging_status\": \"Não Configurado\"" in str(alert.details)

# --- Testes para evaluate_huawei_obs_policies ---

def test_evaluate_huawei_obs_policies_no_buckets():
    alerts = evaluate_huawei_obs_policies([], "test-project-id")
    assert alerts == []

def test_evaluate_huawei_obs_policies_one_secure_bucket(secure_huawei_obs_bucket_input: HuaweiOBSBucketDataInput):
    alerts = evaluate_huawei_obs_policies([secure_huawei_obs_bucket_input], "test-project-id")
    assert alerts == []

def test_evaluate_huawei_obs_policies_one_bucket_multiple_violations():
    now = datetime.now(timezone.utc)
    vulnerable_bucket = HuaweiOBSBucketDataInput(
        name="vuln-huawei-bucket", creation_date=now, location="cn-north-1",
        is_public_by_policy=True, # Violação 1
        public_policy_details=["Policy: Public via HUAWEI:*"],
        bucket_policy=HuaweiOBSBucketPolicyInput(Statement=[]), # Dummy
        is_public_by_acl=True, # Violação 2
        public_acl_details=["ACL: Public via Everyone URI"],
        acl=HuaweiOBSBucketACLInput(Owner=HuaweiOBSOwnerInput(ID="owner"), grants=[]), # Dummy
        versioning=HuaweiOBSBucketVersioningInput(status="Suspended"), # Violação 3
        logging=HuaweiOBSBucketLoggingInput(enabled=False) # Violação 4
    )
    alerts = evaluate_huawei_obs_policies([vulnerable_bucket], "test-project-vuln")

    # A política PublicAccessPolicy agora combina policy e acl, então gera 1 alerta se qualquer um for público.
    # Então esperamos 1 (PublicAccess) + 1 (Versioning) + 1 (Logging) = 3 alertas
    assert len(alerts) == 3
    policy_ids_found = {alert.policy_id for alert in alerts}
    expected_policy_ids = {
        "HUAWEI_OBS_Bucket_Public_Access",
        "HUAWEI_OBS_Bucket_Versioning_Disabled",
        "HUAWEI_OBS_Bucket_Logging_Disabled"
    }
    assert policy_ids_found == expected_policy_ids

def test_evaluate_huawei_obs_policies_skips_bucket_with_error(secure_huawei_obs_bucket_input: HuaweiOBSBucketDataInput):
    bucket_with_error = HuaweiOBSBucketDataInput(
        name="error-huawei-bucket", creation_date=datetime.now(), location="eu-west-0",
        error_details="Simulated Huawei OBS collection error"
    )
    alerts = evaluate_huawei_obs_policies([bucket_with_error, secure_huawei_obs_bucket_input], "test-project-id")
    assert len(alerts) == 0
```

Ajustes feitos durante a escrita dos testes em `huawei_obs_policies.py`:
*   Na política `HuaweiOBSBucketPublicAccessPolicy`, a lógica de `check` foi atualizada para combinar as informações de `is_public_by_policy` e `is_public_by_acl`. Se qualquer um for verdadeiro, um único alerta de acesso público é gerado, com os detalhes combinados. Isso simplifica a política para uma verificação geral de "acesso público", em vez de ter políticas separadas para ACL e Política de Bucket que poderiam gerar alertas redundantes para o mesmo problema subjacente.
*   O `account_id` passado para `policy.check` é usado no alerta.
*   Os testes para `evaluate_huawei_obs_policies` foram ajustados para refletir que a política de acesso público agora é unificada.

Este arquivo agora contém testes para as políticas de OBS implementadas.
