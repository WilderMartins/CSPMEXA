import pytest
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from app.schemas.input_data_schema import (
    GCPComputeInstanceDataInput, GCPComputeServiceAccountInput,
    GCPFirewallDataInput, GCPFirewallAllowedRuleInput
)
from app.schemas.alert_schema import Alert
from app.engine.gcp_compute_policies import (
    evaluate_gcp_compute_instance_policies,
    evaluate_gcp_firewall_policies,
    GCPComputeInstancePublicIPPolicy,
    GCPComputeInstanceDefaultServiceAccountFullAccessPolicy,
    GCPFirewallPublicIngressAnyPortPolicy
)

# --- Fixtures de Dados de Teste para GCP Compute ---

@pytest.fixture
def secure_gcp_instance_input() -> GCPComputeInstanceDataInput:
    now = datetime.now(timezone.utc)
    return GCPComputeInstanceDataInput(
        id="11111", name="secure-instance", project_id="test-project",
        zone="projects/test-project/zones/us-central1-a", # URL completa como viria da API
        machine_type="projects/test-project/machineTypes/n1-standard-1", # URL completa
        status="RUNNING", creation_timestamp=now,
        public_ip_addresses=[], # Sem IP público
        private_ip_addresses=["10.0.0.2"],
        service_accounts=[GCPComputeServiceAccountInput( # SA específica, não default com full access
            email="specific-sa@test-project.iam.gserviceaccount.com",
            scopes=["https://www.googleapis.com/auth/devstorage.read_only"]
        )],
        extracted_zone="us-central1-a", # Campo já extraído pelo collector
        extracted_machine_type="n1-standard-1" # Campo já extraído
    )

@pytest.fixture
def secure_gcp_firewall_input() -> GCPFirewallDataInput:
    now = datetime.now(timezone.utc)
    return GCPFirewallDataInput(
        id="22222", name="allow-internal-ssh", project_id="test-project",
        network="projects/test-project/global/networks/default", # URL
        priority=1000, direction="INGRESS", disabled=False,
        creation_timestamp=now,
        allowed=[GCPFirewallAllowedRuleInput(
            IPProtocol="tcp", ports=["22"] # Permitindo SSH
        )],
        source_ranges=["10.0.0.0/8"], # Apenas de IPs internos
        extracted_network_name="default" # Campo já extraído
    )

# --- Testes para Políticas de Instância ---

def test_gcp_instance_public_ip_policy_no_violation(secure_gcp_instance_input: GCPComputeInstanceDataInput):
    policy = GCPComputeInstancePublicIPPolicy()
    alert = policy.check(secure_gcp_instance_input, "test-project")
    assert alert is None

def test_gcp_instance_public_ip_policy_with_violation(secure_gcp_instance_input: GCPComputeInstanceDataInput):
    policy = GCPComputeInstancePublicIPPolicy()
    secure_gcp_instance_input.public_ip_addresses = ["34.35.36.37"]
    alert = policy.check(secure_gcp_instance_input, "test-project")
    assert alert is not None
    assert alert.policy_id == "GCP_Compute_Instance_Public_IP"
    assert "34.35.36.37" in alert.description

def test_gcp_instance_default_sa_full_access_no_violation(secure_gcp_instance_input: GCPComputeInstanceDataInput):
    policy = GCPComputeInstanceDefaultServiceAccountFullAccessPolicy()
    # Fixture usa SA específica
    alert = policy.check(secure_gcp_instance_input, "test-project")
    assert alert is None

def test_gcp_instance_default_sa_full_access_with_violation(secure_gcp_instance_input: GCPComputeInstanceDataInput):
    policy = GCPComputeInstanceDefaultServiceAccountFullAccessPolicy()
    secure_gcp_instance_input.service_accounts = [GCPComputeServiceAccountInput(
        email="123456-compute@developer.gserviceaccount.com", # Default SA
        scopes=["https://www.googleapis.com/auth/cloud-platform"] # Full access scope
    )]
    alert = policy.check(secure_gcp_instance_input, "test-project")
    assert alert is not None
    assert alert.policy_id == "GCP_Compute_Instance_Default_SA_Full_Access"
    assert "123456-compute@developer.gserviceaccount.com" in alert.description

def test_gcp_instance_default_sa_not_full_access(secure_gcp_instance_input: GCPComputeInstanceDataInput):
    policy = GCPComputeInstanceDefaultServiceAccountFullAccessPolicy()
    secure_gcp_instance_input.service_accounts = [GCPComputeServiceAccountInput(
        email="123456-compute@developer.gserviceaccount.com", # Default SA
        scopes=["https://www.googleapis.com/auth/devstorage.read_only"] # Escopo restrito
    )]
    alert = policy.check(secure_gcp_instance_input, "test-project")
    assert alert is None # Não é violação pois o escopo não é full access

# --- Testes para Políticas de Firewall ---

def test_gcp_firewall_public_ingress_any_port_no_violation(secure_gcp_firewall_input: GCPFirewallDataInput):
    policy = GCPFirewallPublicIngressAnyPortPolicy()
    # Fixture tem source_ranges restrito
    alert = policy.check(secure_gcp_firewall_input, "test-project")
    assert alert is None

def test_gcp_firewall_public_ingress_any_port_with_violation(secure_gcp_firewall_input: GCPFirewallDataInput):
    policy = GCPFirewallPublicIngressAnyPortPolicy()
    secure_gcp_firewall_input.source_ranges = ["0.0.0.0/0"]
    secure_gcp_firewall_input.allowed = [GCPFirewallAllowedRuleInput(IPProtocol="all")] # Protocolo 'all'

    alert = policy.check(secure_gcp_firewall_input, "test-project")
    assert alert is not None
    assert alert.policy_id == "GCP_Firewall_Public_Ingress_Any_Port"
    assert "protocol 'all' (all ports) from 0.0.0.0/0" in alert.description

def test_gcp_firewall_public_ingress_any_port_disabled_rule(secure_gcp_firewall_input: GCPFirewallDataInput):
    policy = GCPFirewallPublicIngressAnyPortPolicy()
    secure_gcp_firewall_input.source_ranges = ["0.0.0.0/0"]
    secure_gcp_firewall_input.allowed = [GCPFirewallAllowedRuleInput(IPProtocol="all")]
    secure_gcp_firewall_input.disabled = True # Regra desabilitada

    alert = policy.check(secure_gcp_firewall_input, "test-project")
    assert alert is None # Regra desabilitada não deve alertar

# --- Testes para Funções de Avaliação ---

def test_evaluate_gcp_compute_instance_policies_no_instances():
    alerts = evaluate_gcp_compute_instance_policies([], "test-project")
    assert alerts == []

def test_evaluate_gcp_compute_instance_policies_one_secure(secure_gcp_instance_input: GCPComputeInstanceDataInput):
    alerts = evaluate_gcp_compute_instance_policies([secure_gcp_instance_input], "test-project")
    assert alerts == []

def test_evaluate_gcp_compute_instance_policies_one_vulnerable():
    now = datetime.now(timezone.utc)
    vulnerable_instance = GCPComputeInstanceDataInput(
        id="vuln-instance-id", name="vuln-instance", project_id="test-project",
        zone="projects/test-project/zones/us-east1-b", machine_type="projects/test-project/machineTypes/e2-medium",
        status="RUNNING", creation_timestamp=now,
        public_ip_addresses=["8.8.8.8"], # Violação
        service_accounts=[GCPComputeServiceAccountInput( # Violação
            email="default-sa-compute@developer.gserviceaccount.com",
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )],
        extracted_zone="us-east1-b", extracted_machine_type="e2-medium"
    )
    alerts = evaluate_gcp_compute_instance_policies([vulnerable_instance], "test-project")
    assert len(alerts) == 2
    policy_ids = {alert.policy_id for alert in alerts}
    assert "GCP_Compute_Instance_Public_IP" in policy_ids
    assert "GCP_Compute_Instance_Default_SA_Full_Access" in policy_ids


def test_evaluate_gcp_firewall_policies_no_firewalls():
    alerts = evaluate_gcp_firewall_policies([], "test-project")
    assert alerts == []

def test_evaluate_gcp_firewall_policies_one_secure(secure_gcp_firewall_input: GCPFirewallDataInput):
    alerts = evaluate_gcp_firewall_policies([secure_gcp_firewall_input], "test-project")
    assert alerts == []

def test_evaluate_gcp_firewall_policies_one_vulnerable():
    now = datetime.now(timezone.utc)
    vulnerable_firewall = GCPFirewallDataInput(
        id="vuln-fw-id", name="allow-all-public", project_id="test-project",
        network="projects/test-project/global/networks/default", priority=1000,
        direction="INGRESS", disabled=False, creation_timestamp=now,
        allowed=[GCPFirewallAllowedRuleInput(IPProtocol="all")], # Violação
        source_ranges=["0.0.0.0/0"], # Violação
        extracted_network_name="default"
    )
    alerts = evaluate_gcp_firewall_policies([vulnerable_firewall], "test-project")
    assert len(alerts) == 1
    assert alerts[0].policy_id == "GCP_Firewall_Public_Ingress_Any_Port"

# Adicionar testes para políticas de firewall de portas específicas quando forem implementadas.
```

Ajustes feitos durante a escrita dos testes em `gcp_compute_policies.py`:
*   Na política `GCPFirewallPublicIngressAnyPortPolicy`, a verificação de `rule.ports` foi ajustada: `not rule.ports` agora também indica "todas as portas" para o protocolo dado, além de `ip_protocol.lower() == "all"`.
*   O `project_id` foi adicionado ao `GCPComputeInstanceDataInput` e `GCPFirewallDataInput` e usado nos detalhes do alerta para consistência.
*   As URLs de `zone` e `machine_type` no `GCPComputeInstanceDataInput` são agora usadas como estão (URLs completas), e os campos `extracted_zone` e `extracted_machine_type` (que seriam preenchidos pelo coletor) são usados para os alertas. Isso corresponde melhor ao que o coletor provavelmente fará.

Este arquivo agora contém uma boa base de testes para as políticas de Compute Engine.
