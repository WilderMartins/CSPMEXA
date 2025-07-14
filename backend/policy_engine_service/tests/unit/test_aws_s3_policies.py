import pytest
from typing import List, Optional, Dict, Any
from datetime import datetime

from policy_engine_service.app.schemas.input_data_schema import (
    S3BucketDataInput, S3BucketACLDetails, S3BucketACLGrant, S3BucketACLGrantee,
    S3BucketVersioning, S3BucketLogging, S3BucketPublicAccessBlock
)
from policy_engine_service.app.schemas.alert_schema import Alert
from policy_engine_service.app.engine.aws_s3_policies import (
    evaluate_s3_policies,
    S3PublicReadACLPolicy,
    S3PublicPolicyPolicy,
    S3VersioningDisabledPolicy,
    S3LoggingDisabledPolicy
)

# --- Fixtures de Dados de Teste ---

@pytest.fixture
def basic_s3_bucket_input() -> S3BucketDataInput:
    """Retorna um S3BucketDataInput básico e seguro por padrão."""
    return S3BucketDataInput(
        name="test-secure-bucket",
        creation_date=datetime.now(),
        region="us-east-1",
        acl=S3BucketACLDetails(is_public=False, grants=[]),
        policy=None,
        policy_is_public=False,
        versioning=S3BucketVersioning(status="Enabled", mfa_delete="Disabled"),
        public_access_block=S3BucketPublicAccessBlock(
            BlockPublicAcls=True,
            IgnorePublicAcls=True,
            BlockPublicPolicy=True,
            RestrictPublicBuckets=True
        ),
        logging=S3BucketLogging(enabled=True, target_bucket="log-bucket", target_prefix="logs/"),
        error_details=None
    )

# --- Testes para Políticas Individuais (Exemplos) ---

def test_s3_public_read_acl_policy_no_violation(basic_s3_bucket_input: S3BucketDataInput):
    policy = S3PublicReadACLPolicy()
    alert = policy.check(basic_s3_bucket_input, "123456789012")
    assert alert is None

def test_s3_public_read_acl_policy_with_violation(basic_s3_bucket_input: S3BucketDataInput):
    policy = S3PublicReadACLPolicy()

    # Modificar o bucket para ter ACL pública
    public_grants = [S3BucketACLGrant(
        grantee=S3BucketACLGrantee(type="Group", uri="http://acs.amazonaws.com/groups/global/AllUsers"),
        permission="READ"
    )]
    basic_s3_bucket_input.acl = S3BucketACLDetails(is_public=True, grants=public_grants, public_details=["Public (AllUsers) with permission: READ"])

    alert = policy.check(basic_s3_bucket_input, "123456789012")
    assert alert is not None
    assert alert.policy_id == "S3_Public_Read_ACL"
    assert alert.resource_id == basic_s3_bucket_input.name
    assert alert.severity == "High"
    assert "Public (AllUsers) with permission: READ" in alert.description

def test_s3_public_policy_policy_no_violation(basic_s3_bucket_input: S3BucketDataInput):
    policy = S3PublicPolicyPolicy()
    alert = policy.check(basic_s3_bucket_input, "123456789012")
    assert alert is None

def test_s3_public_policy_policy_with_violation(basic_s3_bucket_input: S3BucketDataInput):
    policy = S3PublicPolicyPolicy()
    basic_s3_bucket_input.policy_is_public = True # Simula que o collector detectou política pública
    basic_s3_bucket_input.policy = {"Statement": [{"Effect": "Allow", "Principal": "*"}]} # Exemplo de política

    alert = policy.check(basic_s3_bucket_input, "123456789012")
    assert alert is not None
    assert alert.policy_id == "S3_Public_Policy"
    assert alert.severity == "Critical"

def test_s3_versioning_disabled_policy_no_violation(basic_s3_bucket_input: S3BucketDataInput):
    policy = S3VersioningDisabledPolicy()
    # O fixture já tem versioning habilitado
    alert = policy.check(basic_s3_bucket_input, "123456789012")
    assert alert is None

def test_s3_versioning_disabled_policy_with_violation_suspended(basic_s3_bucket_input: S3BucketDataInput):
    policy = S3VersioningDisabledPolicy()
    basic_s3_bucket_input.versioning = S3BucketVersioning(status="Suspended")
    alert = policy.check(basic_s3_bucket_input, "123456789012")
    assert alert is not None
    assert alert.policy_id == "S3_Versioning_Disabled"
    assert "Status atual: Suspended" in alert.description

def test_s3_versioning_disabled_policy_with_violation_none(basic_s3_bucket_input: S3BucketDataInput):
    policy = S3VersioningDisabledPolicy()
    basic_s3_bucket_input.versioning = None # Não configurado
    alert = policy.check(basic_s3_bucket_input, "123456789012")
    assert alert is not None
    assert alert.policy_id == "S3_Versioning_Disabled"
    assert "Status atual: Não Configurado" in alert.description


def test_s3_logging_disabled_policy_no_violation(basic_s3_bucket_input: S3BucketDataInput):
    policy = S3LoggingDisabledPolicy()
    # O fixture já tem logging habilitado
    alert = policy.check(basic_s3_bucket_input, "123456789012")
    assert alert is None

def test_s3_logging_disabled_policy_with_violation(basic_s3_bucket_input: S3BucketDataInput):
    policy = S3LoggingDisabledPolicy()
    basic_s3_bucket_input.logging = S3BucketLogging(enabled=False)
    alert = policy.check(basic_s3_bucket_input, "123456789012")
    assert alert is not None
    assert alert.policy_id == "S3_Logging_Disabled"

def test_s3_logging_disabled_policy_with_violation_none(basic_s3_bucket_input: S3BucketDataInput):
    policy = S3LoggingDisabledPolicy()
    basic_s3_bucket_input.logging = None # Não configurado
    alert = policy.check(basic_s3_bucket_input, "123456789012")
    assert alert is not None
    assert alert.policy_id == "S3_Logging_Disabled"
    assert "logging_status\": \"Não Configurado\"" in alert.details.get("details", str(alert.details)) # Checa se o status é 'Não Configurado' no JSON


# --- Testes para a função evaluate_s3_policies ---

def test_evaluate_s3_policies_no_buckets():
    alerts = evaluate_s3_policies([], "123456789012")
    assert alerts == []

def test_evaluate_s3_policies_one_secure_bucket(basic_s3_bucket_input: S3BucketDataInput):
    alerts = evaluate_s3_policies([basic_s3_bucket_input], "123456789012")
    assert alerts == [] # Nenhuma violação esperada

def test_evaluate_s3_policies_one_bucket_multiple_violations():
    bucket_vulnerable = S3BucketDataInput(
        name="vulnerable-bucket",
        creation_date=datetime.now(),
        region="us-east-1",
        acl=S3BucketACLDetails(is_public=True, grants=[S3BucketACLGrant(grantee=S3BucketACLGrantee(type="Group", uri="http://acs.amazonaws.com/groups/global/AllUsers"), permission="READ")], public_details=["ACL Public Read"]),
        policy_is_public=True, # Violação de política pública
        policy={"Statement": [{"Effect": "Allow", "Principal": "*"}]},
        versioning=S3BucketVersioning(status="Suspended"), # Violação de versionamento
        logging=S3BucketLogging(enabled=False), # Violação de logging
        public_access_block=None, # Pode ser outra violação se tivermos política para isso
        error_details=None
    )
    alerts = evaluate_s3_policies([bucket_vulnerable], "123456789012")
    assert len(alerts) == 4 # Espera-se 4 violações (ACL, Policy, Versioning, Logging)

    policy_ids_found = {alert.policy_id for alert in alerts}
    expected_policy_ids = {
        "S3_Public_Read_ACL",
        "S3_Public_Policy",
        "S3_Versioning_Disabled",
        "S3_Logging_Disabled"
    }
    assert policy_ids_found == expected_policy_ids

def test_evaluate_s3_policies_skips_bucket_with_error_details(basic_s3_bucket_input: S3BucketDataInput):
    bucket_with_error = S3BucketDataInput(
        name="error-bucket",
        creation_date=datetime.now(),
        region="us-east-1",
        acl=None, policy=None, policy_is_public=None, versioning=None, public_access_block=None, logging=None,
        error_details="Simulated collection error for this bucket."
    )
    # Bucket seguro para garantir que a função não retorne vazio apenas por causa do erro
    alerts = evaluate_s3_policies([bucket_with_error, basic_s3_bucket_input], "123456789012")
    # Espera-se 0 alertas, pois o bucket com erro é pulado e o basic_s3_bucket_input é seguro
    assert len(alerts) == 0


def test_evaluate_s3_policies_policy_evaluation_error(basic_s3_bucket_input: S3BucketDataInput):
    # Mockar o check de uma política para levantar uma exceção
    original_check = S3PublicReadACLPolicy.check
    def mock_check_raises_exception(self, bucket, account_id):
        raise ValueError("Simulated policy check error")

    S3PublicReadACLPolicy.check = mock_check_raises_exception

    # Criar um bucket que normalmente violaria S3PublicReadACLPolicy
    bucket_violates_acl = S3BucketDataInput(
        name="violates-acl-bucket",
        creation_date=datetime.now(), region="us-east-1",
        acl=S3BucketACLDetails(is_public=True, grants=[], public_details=["Test Public ACL"]),
        policy=None, policy_is_public=False, versioning=None, public_access_block=None, logging=None,
        error_details=None
    )

    alerts = evaluate_s3_policies([bucket_violates_acl], "123456789012")

    S3PublicReadACLPolicy.check = original_check # Restaurar o método original

    assert len(alerts) == 1
    assert alerts[0].policy_id == "POLICY_ENGINE_ERROR"
    assert alerts[0].title == "Erro ao Avaliar Política S3_Public_Read_ACL"
    assert "Simulated policy check error" in alerts[0].description
    assert alerts[0].details["failed_policy_id"] == "S3_Public_Read_ACL"

# Adicionar mais cenários de teste conforme necessário
