import pytest
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from app.schemas.input_data_schema import (
    HuaweiECSServerDataInput, HuaweiECSAddressInput, HuaweiECSImageInput, HuaweiECSFlavorInput,
    HuaweiVPCSecurityGroupInput, HuaweiVPCSecurityGroupRuleInput
)
from app.schemas.alert_schema import Alert
from app.engine.huawei_ecs_policies import (
    evaluate_huawei_ecs_instance_policies,
    evaluate_huawei_vpc_sg_policies,
    HuaweiECSPublicIPPolicy,
    # Adicionar HuaweiECSMissingKeyPairPolicy se implementada
    HuaweiVPCSGAllowsPublicIngressToPortPolicy
)

# --- Fixtures de Dados de Teste para Huawei ECS e VPC SG ---

@pytest.fixture
def secure_huawei_ecs_instance_input() -> HuaweiECSServerDataInput:
    now = datetime.now(timezone.utc)
    return HuaweiECSServerDataInput(
        id="ecs-secure-uuid", name="secure-ecs-vm", project_id="test-project-huawei", region_id="cn-north-1",
        status="ACTIVE", created=now, updated=now,
        image=HuaweiECSImageInput(id="img-secure"),
        flavor=HuaweiECSFlavorInput(id="s6.large.2", name="s6.large.2"),
        public_ips=[], # Sem IP público
        private_ips=["192.168.1.50"],
        key_name="my-ssh-keypair", # Com key pair
        security_groups=[{"name": "sg-internal-access"}] # 'name' aqui é o ID do SG
    )

@pytest.fixture
def secure_huawei_vpc_sg_input() -> HuaweiVPCSecurityGroupInput:
    return HuaweiVPCSecurityGroupInput(
        id="sg-secure-uuid", name="internal-access-sg",
        project_id_from_collector="test-project-huawei", region_id="cn-north-1",
        description="Allows internal SSH only",
        security_group_rules=[
            HuaweiVPCSecurityGroupRuleInput(
                id="rule-internal-ssh", security_group_id="sg-secure-uuid", direction="ingress",
                protocol="tcp", port_range_min=22, port_range_max=22, remote_ip_prefix="10.0.0.0/8"
            )
        ]
    )

# --- Testes para Políticas de Instância ECS ---

def test_huawei_ecs_public_ip_policy_no_violation(secure_huawei_ecs_instance_input: HuaweiECSServerDataInput):
    policy = HuaweiECSPublicIPPolicy()
    alert = policy.check(secure_huawei_ecs_instance_input, "test-project-huawei", "cn-north-1")
    assert alert is None

def test_huawei_ecs_public_ip_policy_with_violation(secure_huawei_ecs_instance_input: HuaweiECSServerDataInput):
    policy = HuaweiECSPublicIPPolicy()
    secure_huawei_ecs_instance_input.public_ips = ["121.36.0.1"]
    alert = policy.check(secure_huawei_ecs_instance_input, "test-project-huawei", "cn-north-1")
    assert alert is not None
    assert alert.policy_id == "HUAWEI_ECS_Instance_Public_IP"
    assert "121.36.0.1" in alert.description

# --- Testes para Políticas de VPC Security Group ---

def test_huawei_vpc_sg_public_ingress_ssh_no_violation(secure_huawei_vpc_sg_input: HuaweiVPCSecurityGroupInput):
    # O fixture já é seguro para SSH público (só permite de 10.0.0.0/8)
    policy_ssh = HuaweiVPCSGAllowsPublicIngressToPortPolicy(port=22, protocol="tcp", policy_id_suffix="SSH", title_suffix="SSH")
    alert = policy_ssh.check(secure_huawei_vpc_sg_input, "test-project-huawei", "cn-north-1")
    assert alert is None

def test_huawei_vpc_sg_public_ingress_ssh_violation(secure_huawei_vpc_sg_input: HuaweiVPCSecurityGroupInput):
    policy_ssh = HuaweiVPCSGAllowsPublicIngressToPortPolicy(port=22, protocol="tcp", policy_id_suffix="SSH", title_suffix="SSH")
    secure_huawei_vpc_sg_input.security_group_rules = [
        HuaweiVPCSecurityGroupRuleInput(
            id="rule-public-ssh", security_group_id=secure_huawei_vpc_sg_input.id, direction="ingress",
            protocol="tcp", port_range_min=22, port_range_max=22, remote_ip_prefix="0.0.0.0/0" # Violação
        )
    ]
    alert = policy_ssh.check(secure_huawei_vpc_sg_input, "test-project-huawei", "cn-north-1")
    assert alert is not None
    assert alert.policy_id == "HUAWEI_VPC_SG_Public_Ingress_SSH"
    assert "0.0.0.0/0" in alert.description

def test_huawei_vpc_sg_public_ingress_any_all_violation(secure_huawei_vpc_sg_input: HuaweiVPCSecurityGroupInput):
    policy_any = HuaweiVPCSGAllowsPublicIngressToPortPolicy(port=0, protocol="any", policy_id_suffix="ANY_ALL", title_suffix="Any/All")
    secure_huawei_vpc_sg_input.security_group_rules = [
        HuaweiVPCSecurityGroupRuleInput( # Qualquer protocolo, qualquer porta, de qualquer lugar
            id="rule-any-any", security_group_id=secure_huawei_vpc_sg_input.id, direction="ingress",
            protocol=None, # Representa 'any'
            port_range_min=None, port_range_max=None, # Representa 'any port'
            remote_ip_prefix="0.0.0.0/0"
        )
    ]
    alert = policy_any.check(secure_huawei_vpc_sg_input, "test-project-huawei", "cn-north-1")
    assert alert is not None
    assert alert.policy_id == "HUAWEI_VPC_SG_Public_Ingress_ANY_ALL" # Suffix é ANY_ALL
    assert "'any'" in alert.description # Protocolo 'any'

def test_huawei_vpc_sg_public_ingress_rule_disabled(secure_huawei_vpc_sg_input: HuaweiVPCSecurityGroupInput):
    # As regras de SG da Huawei não têm um campo "disabled" individual. O SG inteiro é habilitado/desabilitado.
    # Esta política verifica regras individuais. Se o SG estiver desabilitado, o collector não o traria ou o marcaria.
    # Portanto, este teste não é aplicável da mesma forma que para firewalls GCP.
    # A política opera sobre as regras de um SG que se presume estar ativo.
    pass

# --- Testes para Funções de Avaliação ---

def test_evaluate_huawei_ecs_instance_policies_no_instances():
    alerts = evaluate_huawei_ecs_instance_policies([], "test-project", "cn-north-1")
    assert alerts == []

def test_evaluate_huawei_ecs_instance_policies_one_secure(secure_huawei_ecs_instance_input: HuaweiECSServerDataInput):
    alerts = evaluate_huawei_ecs_instance_policies([secure_huawei_ecs_instance_input], "test-project", "cn-north-1")
    assert alerts == []

def test_evaluate_huawei_ecs_instance_policies_one_vulnerable_public_ip(secure_huawei_ecs_instance_input: HuaweiECSServerDataInput):
    secure_huawei_ecs_instance_input.public_ips = ["1.2.3.4"]
    alerts = evaluate_huawei_ecs_instance_policies([secure_huawei_ecs_instance_input], "test-project", "cn-north-1")
    assert len(alerts) == 1
    assert alerts[0].policy_id == "HUAWEI_ECS_Instance_Public_IP"


def test_evaluate_huawei_vpc_sg_policies_no_sgs():
    alerts = evaluate_huawei_vpc_sg_policies([], "test-project", "cn-north-1")
    assert alerts == []

def test_evaluate_huawei_vpc_sg_policies_one_secure_sg(secure_huawei_vpc_sg_input: HuaweiVPCSecurityGroupInput):
    alerts = evaluate_huawei_vpc_sg_policies([secure_huawei_vpc_sg_input], "test-project", "cn-north-1")
    assert alerts == []

def test_evaluate_huawei_vpc_sg_policies_one_vulnerable_sg():
    now = datetime.now(timezone.utc)
    vulnerable_sg = HuaweiVPCSecurityGroupInput(
        id="sg-vuln-uuid", name="public-sg", project_id_from_collector="test-project", region_id="cn-north-1",
        security_group_rules=[
            HuaweiVPCSecurityGroupRuleInput( # SSH Público
                id="rule-ssh", security_group_id="sg-vuln-uuid", direction="ingress",
                protocol="tcp", port_range_min=22, port_range_max=22, remote_ip_prefix="0.0.0.0/0"
            ),
            HuaweiVPCSecurityGroupRuleInput( # RDP Público
                id="rule-rdp", security_group_id="sg-vuln-uuid", direction="ingress",
                protocol="tcp", port_range_min=3389, port_range_max=3389, remote_ip_prefix="0.0.0.0/0"
            )
        ]
    )
    alerts = evaluate_huawei_vpc_sg_policies([vulnerable_sg], "test-project", "cn-north-1")
    assert len(alerts) == 2
    policy_ids = {alert.policy_id for alert in alerts}
    assert "HUAWEI_VPC_SG_Public_Ingress_SSH" in policy_ids
    assert "HUAWEI_VPC_SG_Public_Ingress_RDP" in policy_ids
```

Ajustes feitos durante a escrita dos testes em `huawei_ecs_policies.py`:
*   Na política `HuaweiVPCSGAllowsPublicIngressToPortPolicy`:
    *   A lógica de correspondência de protocolo foi ajustada para que `self.protocol == "any"` também corresponda se `rule.protocol` for `None` (que significa qualquer protocolo na Huawei).
    *   A lógica de correspondência de porta foi ajustada para considerar `port_range_min` e `port_range_max` sendo `None` como "qualquer porta".
*   Os testes agora passam o `region_id` para as funções de avaliação, pois as políticas podem precisar dele para o contexto do alerta.

Este arquivo contém testes para as políticas de ECS e VPC Security Group da Huawei Cloud.
