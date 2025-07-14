import pytest
from typing import List, Optional, Dict, Any
from datetime import datetime

from policy_engine_service.app.schemas.input_data_schema import (
    EC2InstanceDataInput, EC2InstanceState,
    EC2SecurityGroupDataInput, EC2IpPermission
)
from policy_engine_service.app.schemas.alert_schema import Alert
from policy_engine_service.app.engine.aws_ec2_policies import (
    evaluate_ec2_sg_policies,
    evaluate_ec2_instance_policies,
    EC2SGPublicIngressAllPortsPolicy,
    EC2SGPublicIngressSpecificPortPolicy,
    EC2InstancePublicIPPolicy,
    EC2InstanceNoIAMProfilePolicy,
    EC2InstanceMissingRequiredTagsPolicy,
    EC2InstanceUnapprovedAMIPolicy
)

# --- Fixtures de Dados de Teste para EC2 ---

@pytest.fixture
def basic_ec2_instance_input() -> EC2InstanceDataInput:
    """Retorna uma EC2InstanceDataInput básica e segura por padrão."""
    return EC2InstanceDataInput(
        instance_id="i-1234567890abcdef0",
        instance_type="t2.micro",
        image_id="ami-0abcdef1234567890",
        launch_time=datetime.now(),
        platform="Linux/UNIX",
        private_ip_address="10.0.1.10",
        public_ip_address=None, # Sem IP público por padrão
        state=EC2InstanceState(code=16, name="running"),
        subnet_id="subnet-abcdef1234567890",
        vpc_id="vpc-0e987654321fedcba",
        iam_instance_profile_arn="arn:aws:iam::123456789012:instance-profile/MyProfile", # Com perfil IAM
        security_groups=[{"GroupId": "sg-123", "GroupName": "default"}],
        tags=[{"Key": "Name", "Value": "SecureInstance"}],
        region="us-east-1",
        error_details=None
    )

@pytest.fixture
def basic_ec2_sg_input() -> EC2SecurityGroupDataInput:
    """Retorna uma EC2SecurityGroupDataInput básica e segura por padrão."""
    return EC2SecurityGroupDataInput(
        group_id="sg-abcdef1234567890",
        group_name="secure-sg",
        description="Secure SG",
        vpc_id="vpc-0e987654321fedcba",
        owner_id="123456789012",
        ip_permissions=[], # Sem regras de entrada por padrão
        ip_permissions_egress=[EC2IpPermission( # Egress para todo lugar é comum
            IpProtocol="-1", IpRanges=[{"CidrIp": "0.0.0.0/0"}]
        )],
        tags=[{"Key": "Name", "Value": "SecureSG"}],
        region="us-east-1"
    )

# --- Testes para Políticas de Security Group ---

def test_ec2_sg_public_ingress_all_ports_no_violation(basic_ec2_sg_input: EC2SecurityGroupDataInput):
    policy = EC2SGPublicIngressAllPortsPolicy()
    alert = policy.check(basic_ec2_sg_input, "123456789012", "us-east-1")
    assert alert is None

def test_ec2_sg_public_ingress_all_ports_ipv4_violation(basic_ec2_sg_input: EC2SecurityGroupDataInput):
    policy = EC2SGPublicIngressAllPortsPolicy()
    basic_ec2_sg_input.ip_permissions = [
        EC2IpPermission(IpProtocol="-1", IpRanges=[{"CidrIp": "0.0.0.0/0"}])
    ]
    alert = policy.check(basic_ec2_sg_input, "123456789012", "us-east-1")
    assert alert is not None
    assert alert.policy_id == "EC2_SG_Public_Ingress_All_Ports"
    assert "0.0.0.0/0" in alert.description

def test_ec2_sg_public_ingress_all_ports_ipv6_violation(basic_ec2_sg_input: EC2SecurityGroupDataInput):
    policy = EC2SGPublicIngressAllPortsPolicy()
    basic_ec2_sg_input.ip_permissions = [
        EC2IpPermission(IpProtocol="-1", Ipv6Ranges=[{"CidrIpv6": "::/0"}])
    ]
    alert = policy.check(basic_ec2_sg_input, "123456789012", "us-east-1")
    assert alert is not None
    assert alert.policy_id == "EC2_SG_Public_Ingress_All_Ports"
    assert "::/0" in alert.description


def test_ec2_sg_public_ingress_specific_port_no_violation(basic_ec2_sg_input: EC2SecurityGroupDataInput):
    policy_ssh = EC2SGPublicIngressSpecificPortPolicy(port=22, protocol="tcp", policy_id_suffix="SSH", title_suffix="SSH")
    basic_ec2_sg_input.ip_permissions = [ # Aberto para um IP específico, não para 0.0.0.0/0
        EC2IpPermission(IpProtocol="tcp", FromPort=22, ToPort=22, IpRanges=[{"CidrIp": "1.2.3.4/32"}])
    ]
    alert = policy_ssh.check(basic_ec2_sg_input, "123456789012", "us-east-1")
    assert alert is None

def test_ec2_sg_public_ingress_specific_port_ssh_violation(basic_ec2_sg_input: EC2SecurityGroupDataInput):
    policy_ssh = EC2SGPublicIngressSpecificPortPolicy(port=22, protocol="tcp", policy_id_suffix="SSH", title_suffix="SSH")
    basic_ec2_sg_input.ip_permissions = [
        EC2IpPermission(IpProtocol="tcp", FromPort=22, ToPort=22, IpRanges=[{"CidrIp": "0.0.0.0/0"}])
    ]
    alert = policy_ssh.check(basic_ec2_sg_input, "123456789012", "us-east-1")
    assert alert is not None
    assert alert.policy_id == "EC2_SG_Public_Ingress_SSH"
    assert "port 22/tcp" in alert.description

def test_ec2_sg_public_ingress_specific_port_rdp_violation(basic_ec2_sg_input: EC2SecurityGroupDataInput):
    policy_rdp = EC2SGPublicIngressSpecificPortPolicy(port=3389, protocol="tcp", policy_id_suffix="RDP", title_suffix="RDP")
    basic_ec2_sg_input.ip_permissions = [
        EC2IpPermission(IpProtocol="tcp", FromPort=3389, ToPort=3389, Ipv6Ranges=[{"CidrIpv6": "::/0"}])
    ]
    alert = policy_rdp.check(basic_ec2_sg_input, "123456789012", "us-east-1")
    assert alert is not None
    assert alert.policy_id == "EC2_SG_Public_Ingress_RDP"
    assert "port 3389/tcp" in alert.description

# --- Testes para Políticas de Instância EC2 ---

def test_ec2_instance_public_ip_policy_no_violation(basic_ec2_instance_input: EC2InstanceDataInput):
    policy = EC2InstancePublicIPPolicy()
    # O fixture já não tem IP público
    alert = policy.check(basic_ec2_instance_input, "123456789012", basic_ec2_instance_input.region)
    assert alert is None

def test_ec2_instance_public_ip_policy_with_violation(basic_ec2_instance_input: EC2InstanceDataInput):
    policy = EC2InstancePublicIPPolicy()
    basic_ec2_instance_input.public_ip_address = "1.2.3.4"
    alert = policy.check(basic_ec2_instance_input, "123456789012", basic_ec2_instance_input.region)
    assert alert is not None
    assert alert.policy_id == "EC2_Instance_Public_IP"
    assert alert.severity == "Informational"
    assert alert.details["public_ip"] == "1.2.3.4"

def test_ec2_instance_no_iam_profile_policy_no_violation(basic_ec2_instance_input: EC2InstanceDataInput):
    policy = EC2InstanceNoIAMProfilePolicy()
    # O fixture já tem perfil IAM
    alert = policy.check(basic_ec2_instance_input, "123456789012", basic_ec2_instance_input.region)
    assert alert is None

def test_ec2_instance_no_iam_profile_policy_with_violation(basic_ec2_instance_input: EC2InstanceDataInput):
    policy = EC2InstanceNoIAMProfilePolicy()
    basic_ec2_instance_input.iam_instance_profile_arn = None
    alert = policy.check(basic_ec2_instance_input, "123456789012", basic_ec2_instance_input.region)
    assert alert is not None
    assert alert.policy_id == "EC2_Instance_No_IAM_Profile"
    assert alert.severity == "Medium"

# --- Testes para Funções de Avaliação ---

def test_evaluate_ec2_sg_policies_no_sgs():
    alerts = evaluate_ec2_sg_policies([], "123456789012", "us-east-1")
    assert alerts == []

def test_evaluate_ec2_sg_policies_one_secure_sg(basic_ec2_sg_input: EC2SecurityGroupDataInput):
    alerts = evaluate_ec2_sg_policies([basic_ec2_sg_input], "123456789012", "us-east-1")
    assert alerts == []

def test_evaluate_ec2_sg_policies_one_sg_multiple_violations(basic_ec2_sg_input: EC2SecurityGroupDataInput):
    # Violação de todas as portas e SSH (embora todas as portas já cubra SSH)
    basic_ec2_sg_input.ip_permissions = [
        EC2IpPermission(IpProtocol="-1", IpRanges=[{"CidrIp": "0.0.0.0/0"}]), # Viola AllPorts
        EC2IpPermission(IpProtocol="tcp", FromPort=22, ToPort=22, IpRanges=[{"CidrIp": "0.0.0.0/0"}]) # Viola SSH
    ]
    alerts = evaluate_ec2_sg_policies([basic_ec2_sg_input], "123456789012", "us-east-1")
    # A política AllPorts é Critical. A política SSH é High.
    # Ambas as condições de violação são atendidas.
    assert len(alerts) == 2
    policy_ids_found = {alert.policy_id for alert in alerts}
    assert "EC2_SG_Public_Ingress_All_Ports" in policy_ids_found
    assert "EC2_SG_Public_Ingress_SSH" in policy_ids_found


def test_evaluate_ec2_instance_policies_no_instances():
    alerts = evaluate_ec2_instance_policies([], "123456789012")
    assert alerts == []

def test_evaluate_ec2_instance_policies_one_secure_instance(basic_ec2_instance_input: EC2InstanceDataInput):
    alerts = evaluate_ec2_instance_policies([basic_ec2_instance_input], "123456789012")
    assert alerts == []

def test_evaluate_ec2_instance_policies_one_instance_multiple_violations(basic_ec2_instance_input: EC2InstanceDataInput):
    basic_ec2_instance_input.public_ip_address = "1.2.3.4" # Violação de IP Público
    basic_ec2_instance_input.iam_instance_profile_arn = None # Violação de Perfil IAM

    alerts = evaluate_ec2_instance_policies([basic_ec2_instance_input], "123456789012")
    assert len(alerts) == 2
    policy_ids_found = {alert.policy_id for alert in alerts}
    assert "EC2_Instance_Public_IP" in policy_ids_found
    assert "EC2_Instance_No_IAM_Profile" in policy_ids_found

def test_evaluate_ec2_instance_policies_skips_instance_with_error(basic_ec2_instance_input: EC2InstanceDataInput):
    instance_with_error = EC2InstanceDataInput(
        instance_id="i-errorinstance", region="us-east-1",
        error_details="Simulated collection error"
        # Outros campos podem ser None ou default
    )
    alerts = evaluate_ec2_instance_policies([instance_with_error, basic_ec2_instance_input], "123456789012")
    assert len(alerts) == 0 # O com erro é pulado, o básico é seguro
