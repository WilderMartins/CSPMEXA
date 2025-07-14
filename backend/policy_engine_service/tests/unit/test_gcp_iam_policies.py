import pytest
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from policy_engine_service.app.schemas.input_data_schema import (
    GCPProjectIAMPolicyDataInput, GCPIAMBindingInput
)
from policy_engine_service.app.schemas.alert_schema import Alert
from policy_engine_service.app.engine.gcp_iam_policies import (
    evaluate_gcp_project_iam_policies,
    GCPProjectIAMExternalPrimitiveRolesPolicy
)

# --- Fixtures de Dados de Teste para GCP IAM ---

@pytest.fixture
def secure_gcp_project_iam_input() -> GCPProjectIAMPolicyDataInput:
    """Retorna um GCPProjectIAMPolicyDataInput seguro por padrão."""
    return GCPProjectIAMPolicyDataInput(
        project_id="secure-project-123",
        iam_policy=GCPIAMPolicyInput(
            version=3,
            bindings=[
                GCPIAMBindingInput(role="roles/owner", members=["user:owner@secure.com"]),
                GCPIAMBindingInput(role="roles/editor", members=["serviceAccount:sa@secure-project-123.iam.gserviceaccount.com"]),
                GCPIAMBindingInput(role="roles/viewer", members=["group:viewers@secure.com"])
            ],
            etag="secure-etag"
        ),
        has_external_members_with_primitive_roles=False, # Preenchido pelo collector
        external_primitive_role_details=[], # Preenchido pelo collector
        error_details=None
    )

# --- Testes para Políticas de IAM de Projeto ---

def test_gcp_project_iam_external_primitive_roles_no_violation(secure_gcp_project_iam_input: GCPProjectIAMPolicyDataInput):
    policy = GCPProjectIAMExternalPrimitiveRolesPolicy()
    # O fixture já está seguro em relação a esta política
    alert = policy.check(secure_gcp_project_iam_input, "secure-project-123")
    assert alert is None

def test_gcp_project_iam_external_primitive_roles_with_allusers_owner_violation(secure_gcp_project_iam_input: GCPProjectIAMPolicyDataInput):
    policy_checker = GCPProjectIAMExternalPrimitiveRolesPolicy()

    # Modificar para simular violação - allUsers como Owner
    secure_gcp_project_iam_input.iam_policy.bindings.append(
        GCPIAMBindingInput(role="roles/owner", members=["allUsers", "user:another@example.com"])
    )
    # Simular o que o collector faria:
    secure_gcp_project_iam_input.has_external_members_with_primitive_roles = True
    secure_gcp_project_iam_input.external_primitive_role_details = [
        "Principal externo 'allUsers' encontrado com papel primitivo 'roles/owner'."
    ]

    alert = policy_checker.check(secure_gcp_project_iam_input, "test-project-allusers")
    assert alert is not None
    assert alert.policy_id == "GCP_Project_IAM_External_Primitive_Roles"
    assert alert.severity == "Critical" # Owner é Critical
    assert "allUsers" in alert.description
    assert "roles/owner" in alert.description

def test_gcp_project_iam_external_primitive_roles_with_allauthenticatedusers_viewer_violation(secure_gcp_project_iam_input: GCPProjectIAMPolicyDataInput):
    policy_checker = GCPProjectIAMExternalPrimitiveRolesPolicy()

    secure_gcp_project_iam_input.iam_policy.bindings.append(
        GCPIAMBindingInput(role="roles/viewer", members=["allAuthenticatedUsers"])
    )
    secure_gcp_project_iam_input.has_external_members_with_primitive_roles = True
    secure_gcp_project_iam_input.external_primitive_role_details = [
        "Principal externo 'allAuthenticatedUsers' encontrado com papel primitivo 'roles/viewer'."
    ]

    alert = policy_checker.check(secure_gcp_project_iam_input, "test-project-allauth")
    assert alert is not None
    assert alert.policy_id == "GCP_Project_IAM_External_Primitive_Roles"
    assert alert.severity == "High" # Viewer externo é High
    assert "allAuthenticatedUsers" in alert.description
    assert "roles/viewer" in alert.description

def test_gcp_project_iam_external_primitive_roles_allusers_non_primitive_role(secure_gcp_project_iam_input: GCPProjectIAMPolicyDataInput):
    policy_checker = GCPProjectIAMExternalPrimitiveRolesPolicy()
    # allUsers com papel não primitivo não deve ser pego por *esta* política específica
    secure_gcp_project_iam_input.iam_policy.bindings.append(
        GCPIAMBindingInput(role="roles/storage.objectViewer", members=["allUsers"])
    )
    # Collector não marcaria has_external_members_with_primitive_roles como True para este caso
    secure_gcp_project_iam_input.has_external_members_with_primitive_roles = False
    secure_gcp_project_iam_input.external_primitive_role_details = []

    alert = policy_checker.check(secure_gcp_project_iam_input, "test-project-nonprimitive")
    assert alert is None


# --- Testes para a função evaluate_gcp_project_iam_policies ---

def test_evaluate_gcp_project_iam_policies_no_data():
    alerts = evaluate_gcp_project_iam_policies(None, "test-project-nodata")
    assert alerts == []

def test_evaluate_gcp_project_iam_policies_secure_policy(secure_gcp_project_iam_input: GCPProjectIAMPolicyDataInput):
    alerts = evaluate_gcp_project_iam_policies(secure_gcp_project_iam_input, "secure-project-123")
    assert alerts == []

def test_evaluate_gcp_project_iam_policies_vulnerable_policy():
    vulnerable_policy_data = GCPProjectIAMPolicyDataInput(
        project_id="vuln-project-456",
        iam_policy=GCPIAMPolicyInput(
            version=3,
            bindings=[
                GCPIAMBindingInput(role="roles/editor", members=["allUsers"])
            ],
            etag="vuln-etag"
        ),
        has_external_members_with_primitive_roles=True,
        external_primitive_role_details=["Principal externo 'allUsers' encontrado com papel primitivo 'roles/editor'."],
    )
    alerts = evaluate_gcp_project_iam_policies(vulnerable_policy_data, "vuln-project-456")
    assert len(alerts) == 1
    assert alerts[0].policy_id == "GCP_Project_IAM_External_Primitive_Roles"
    assert alerts[0].severity == "Critical" # Editor é Critical

def test_evaluate_gcp_project_iam_policies_skips_on_collection_error():
    error_policy_data = GCPProjectIAMPolicyDataInput(
        project_id="error-project-789",
        iam_policy=GCPIAMPolicyInput(bindings=[]), # Política vazia
        error_details="Simulated GCP IAM collection error"
    )
    alerts = evaluate_gcp_project_iam_policies(error_policy_data, "error-project-789")
    assert len(alerts) == 0 # Pulado devido ao error_details
