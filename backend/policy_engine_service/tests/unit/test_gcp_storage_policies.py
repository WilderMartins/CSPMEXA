import pytest
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from policy_engine_service.app.schemas.input_data_schema import (
    GCPStorageBucketDataInput, GCPBucketIAMPolicyInput, GCPBucketIAMBindingInput,
    GCPBucketVersioningInput, GCPBucketLoggingInput
)
from policy_engine_service.app.schemas.alert_schema import Alert
from policy_engine_service.app.engine.gcp_storage_policies import (
    evaluate_gcp_storage_policies,
    GCPStorageBucketPublicIAMPolicy,
    GCPStorageBucketVersioningDisabledPolicy,
    GCPStorageBucketLoggingDisabledPolicy
)
from policy_engine_service.app.schemas.input_data_schema import (
    GCPStorageBucketDataInput, GCPBucketIAMPolicyInput, GCPBucketIAMBindingInput,
    GCPBucketVersioningInput, GCPBucketLoggingInput
)

# --- Fixtures de Dados de Teste para GCP Storage ---

@pytest.fixture
def secure_gcp_bucket_input() -> GCPStorageBucketDataInput:
    """Retorna um GCPStorageBucketDataInput seguro por padrão."""
    now = datetime.now(timezone.utc)
    return GCPStorageBucketDataInput(
        id="secure-gcp-bucket-id",
        name="secure-gcp-bucket",
        project_number="123456789",
        location="US-CENTRAL1",
        storage_class="STANDARD",
        time_created=now,
        updated=now,
        iam_policy=GCPBucketIAMPolicyInput(bindings=[
            GCPBucketIAMBindingInput(role="roles/storage.objectViewer", members=["user:test@example.com"])
        ]),
        versioning=GCPBucketVersioningInput(enabled=True),
        logging=GCPBucketLoggingInput(log_bucket="my-log-bucket", log_object_prefix="logs/"),
        is_public_by_iam=False, # Preenchido pelo collector
        public_iam_details=[],   # Preenchido pelo collector
        error_details=None
    )

# --- Testes para Políticas Individuais ---

def test_gcp_storage_bucket_public_iam_policy_no_violation(secure_gcp_bucket_input: GCPStorageBucketDataInput):
    policy = GCPStorageBucketPublicIAMPolicy()
    # O collector já teria definido is_public_by_iam = False
    alert = policy.check(secure_gcp_bucket_input, "test-project-id")
    assert alert is None

def test_gcp_storage_bucket_public_iam_policy_with_violation(secure_gcp_bucket_input: GCPStorageBucketDataInput):
    policy = GCPStorageBucketPublicIAMPolicy()
    secure_gcp_bucket_input.is_public_by_iam = True # Simula detecção pelo collector
    secure_gcp_bucket_input.public_iam_details = ["Role 'roles/storage.objectViewer' granted to public members: allUsers"]
    secure_gcp_bucket_input.iam_policy = GCPBucketIAMPolicyInput(bindings=[
        GCPBucketIAMBindingInput(role="roles/storage.objectViewer", members=["allUsers"])
    ])

    alert = policy.check(secure_gcp_bucket_input, "test-project-id")
    assert alert is not None
    assert alert.policy_id == "GCP_Storage_Bucket_Public_IAM"
    assert alert.severity == "Critical"
    assert "allUsers" in alert.description

def test_gcp_storage_bucket_versioning_disabled_policy_no_violation(secure_gcp_bucket_input: GCPStorageBucketDataInput):
    policy = GCPStorageBucketVersioningDisabledPolicy()
    # Fixture já tem versioning habilitado
    alert = policy.check(secure_gcp_bucket_input, "test-project-id")
    assert alert is None

def test_gcp_storage_bucket_versioning_disabled_policy_with_violation(secure_gcp_bucket_input: GCPStorageBucketDataInput):
    policy = GCPStorageBucketVersioningDisabledPolicy()
    secure_gcp_bucket_input.versioning = GCPBucketVersioningInput(enabled=False)
    alert = policy.check(secure_gcp_bucket_input, "test-project-id")
    assert alert is not None
    assert alert.policy_id == "GCP_Storage_Bucket_Versioning_Disabled"
    assert "Status atual: Desabilitado" in alert.description

def test_gcp_storage_bucket_versioning_disabled_policy_none(secure_gcp_bucket_input: GCPStorageBucketDataInput):
    policy = GCPStorageBucketVersioningDisabledPolicy()
    secure_gcp_bucket_input.versioning = None
    alert = policy.check(secure_gcp_bucket_input, "test-project-id")
    assert alert is not None
    assert alert.policy_id == "GCP_Storage_Bucket_Versioning_Disabled"
    assert "Status atual: Não Configurado" in alert.description


def test_gcp_storage_bucket_logging_disabled_policy_no_violation(secure_gcp_bucket_input: GCPStorageBucketDataInput):
    policy = GCPStorageBucketLoggingDisabledPolicy()
    # Fixture já tem logging habilitado
    alert = policy.check(secure_gcp_bucket_input, "test-project-id")
    assert alert is None

def test_gcp_storage_bucket_logging_disabled_policy_with_violation_no_logbucket(secure_gcp_bucket_input: GCPStorageBucketDataInput):
    policy = GCPStorageBucketLoggingDisabledPolicy()
    secure_gcp_bucket_input.logging = GCPBucketLoggingInput(log_bucket=None, log_object_prefix=None)
    alert = policy.check(secure_gcp_bucket_input, "test-project-id")
    assert alert is not None
    assert alert.policy_id == "GCP_Storage_Bucket_Logging_Disabled"

def test_gcp_storage_bucket_logging_disabled_policy_logging_none(secure_gcp_bucket_input: GCPStorageBucketDataInput):
    policy = GCPStorageBucketLoggingDisabledPolicy()
    secure_gcp_bucket_input.logging = None
    alert = policy.check(secure_gcp_bucket_input, "test-project-id")
    assert alert is not None
    assert alert.policy_id == "GCP_Storage_Bucket_Logging_Disabled"
    assert "logging_status\": \"Não Configurado\"" in str(alert.details)


# --- Testes para evaluate_gcp_storage_policies ---

def test_evaluate_gcp_storage_policies_no_buckets():
    alerts = evaluate_gcp_storage_policies([], "test-project-id")
    assert alerts == []

def test_evaluate_gcp_storage_policies_one_secure_bucket(secure_gcp_bucket_input: GCPStorageBucketDataInput):
    alerts = evaluate_gcp_storage_policies([secure_gcp_bucket_input], "test-project-id")
    assert alerts == []

def test_evaluate_gcp_storage_policies_one_bucket_multiple_violations():
    now = datetime.now(timezone.utc)
    vulnerable_bucket = GCPStorageBucketDataInput(
        id="vuln-gcp-bucket-id", name="vuln-gcp-bucket", project_number="98765", location="US-WEST1",
        storage_class="STANDARD", time_created=now, updated=now,
        iam_policy=GCPBucketIAMPolicyInput(bindings=[ # Política IAM pública
            GCPBucketIAMBindingInput(role="roles/storage.objectViewer", members=["allUsers"])
        ]),
        is_public_by_iam=True, # Simula detecção pelo collector
        public_iam_details=["Role 'roles/storage.objectViewer' granted to public members: allUsers"],
        versioning=GCPBucketVersioningInput(enabled=False), # Versionamento desabilitado
        logging=GCPBucketLoggingInput(log_bucket=None) # Logging desabilitado
    )
    alerts = evaluate_gcp_storage_policies([vulnerable_bucket], "test-project-id-vuln")

    assert len(alerts) == 3
    policy_ids_found = {alert.policy_id for alert in alerts}
    expected_policy_ids = {
        "GCP_Storage_Bucket_Public_IAM",
        "GCP_Storage_Bucket_Versioning_Disabled",
        "GCP_Storage_Bucket_Logging_Disabled"
    }
    assert policy_ids_found == expected_policy_ids

def test_evaluate_gcp_storage_policies_skips_bucket_with_error(secure_gcp_bucket_input: GCPStorageBucketDataInput):
    bucket_with_error = GCPStorageBucketDataInput(
        id="error-gcp-bucket-id", name="error-gcp-bucket", project_number="err", location="ERR",
        storage_class="ERR", time_created=datetime.now(), updated=datetime.now(),
        error_details="Simulated GCP collection error"
    )
    alerts = evaluate_gcp_storage_policies([bucket_with_error, secure_gcp_bucket_input], "test-project-id")
    assert len(alerts) == 0 # Erro é pulado, seguro não gera alertas
