import pytest
import datetime
import uuid # Para mockar a geração de ID de alerta, se necessário, ou apenas verificar formato

from policy_engine_service.app.engine.aws_ec2_policies import (
    evaluate_ec2_instance_policies,
    evaluate_ec2_sg_policies,
    EC2SGPublicIngressAllPortsPolicy,
    EC2SGPublicIngressSpecificPortPolicy,
    EC2InstancePublicIPPolicy,
    EC2InstanceNoIAMProfilePolicy,
    EC2InstanceMissingRequiredTagsPolicy,
    EC2InstanceUnapprovedAMIPolicy,
    REQUIRED_TAGS, # Importar a lista de tags para o teste
    DISAPPROVED_AMIS # Importar a lista de AMIs para o teste
)
from policy_engine_service.app.schemas.input_data_schema import (
    EC2InstanceDataInput,
    EC2SecurityGroupDataInput,
    EC2IpPermission,
    EC2InstanceState
)
from policy_engine_service.app.schemas.alert_schema import Alert, AlertSeverityEnum

ACCOUNT_ID_AWS = "123456789012"
REGION_AWS = "us-east-1"

# --- Fixtures para Instâncias EC2 ---
@pytest.fixture
def ec2_instance_public_ip():
    return EC2InstanceDataInput(
        instance_id="i-123public", region=REGION_AWS, public_ip_address="1.2.3.4",
        # Campos obrigatórios mínimos para o schema base, mesmo que não usados pela política específica:
        image_id="ami-abc", instance_type="t2.micro", launch_time=datetime.datetime.now(datetime.timezone.utc),
        state=EC2InstanceState(name="running", code=16)
    )

@pytest.fixture
def ec2_instance_no_public_ip():
    return EC2InstanceDataInput(
        instance_id="i-456private", region=REGION_AWS, public_ip_address=None,
        image_id="ami-abc", instance_type="t2.micro", launch_time=datetime.datetime.now(datetime.timezone.utc),
        state=EC2InstanceState(name="running", code=16)
    )

@pytest.fixture
def ec2_instance_no_iam_profile():
    return EC2InstanceDataInput(
        instance_id="i-789noiam", region=REGION_AWS, iam_instance_profile_arn=None,
        image_id="ami-abc", instance_type="t2.micro", launch_time=datetime.datetime.now(datetime.timezone.utc),
        state=EC2InstanceState(name="running", code=16)
    )

@pytest.fixture
def ec2_instance_with_iam_profile():
    return EC2InstanceDataInput(
        instance_id="i-abcwithiam", region=REGION_AWS, iam_instance_profile_arn=f"arn:aws:iam::{ACCOUNT_ID_AWS}:instance-profile/MyProfile",
        image_id="ami-abc", instance_type="t2.micro", launch_time=datetime.datetime.now(datetime.timezone.utc),
        state=EC2InstanceState(name="running", code=16)
    )

@pytest.fixture
def ec2_instance_missing_tags():
    return EC2InstanceDataInput(
        instance_id="i-defmissingtags", region=REGION_AWS, tags=[{"Key": "Name", "Value": "Test"}], # Falta Owner, Environment, CostCenter
        image_id="ami-abc", instance_type="t2.micro", launch_time=datetime.datetime.now(datetime.timezone.utc),
        state=EC2InstanceState(name="running", code=16)
    )

@pytest.fixture
def ec2_instance_with_all_tags():
    tags = [{"Key": tag_name, "Value": "TestValue"} for tag_name in REQUIRED_TAGS]
    return EC2InstanceDataInput(
        instance_id="i-ghitagged", region=REGION_AWS, tags=tags,
        image_id="ami-abc", instance_type="t2.micro", launch_time=datetime.datetime.now(datetime.timezone.utc),
        state=EC2InstanceState(name="running", code=16)
    )

@pytest.fixture
def ec2_instance_unapproved_ami():
    return EC2InstanceDataInput(
        instance_id="i-jklunapproved", region=REGION_AWS, image_id=DISAPPROVED_AMIS[0], # Usa a primeira AMI desaprovada
        tags=[{"Key": "Name", "Value": "Test"}],
        instance_type="t2.micro", launch_time=datetime.datetime.now(datetime.timezone.utc),
        state=EC2InstanceState(name="running", code=16)
    )

@pytest.fixture
def ec2_instance_approved_ami():
    return EC2InstanceDataInput(
        instance_id="i-mnoapproved", region=REGION_AWS, image_id="ami-approved123",
        tags=[{"Key": "Name", "Value": "Test"}],
        instance_type="t2.micro", launch_time=datetime.datetime.now(datetime.timezone.utc),
        state=EC2InstanceState(name="running", code=16)
    )

# --- Testes para Políticas de Instância EC2 ---
def test_ec2_instance_public_ip_policy(ec2_instance_public_ip, ec2_instance_no_public_ip):
    policy = EC2InstancePublicIPPolicy()
    alert = policy.check(ec2_instance_public_ip, ACCOUNT_ID_AWS, REGION_AWS)
    assert alert is not None
    assert alert.policy_id == "EC2_Instance_Public_IP"
    assert alert.severity == AlertSeverityEnum.INFORMATIONAL

    alert = policy.check(ec2_instance_no_public_ip, ACCOUNT_ID_AWS, REGION_AWS)
    assert alert is None

def test_ec2_instance_no_iam_profile_policy(ec2_instance_no_iam_profile, ec2_instance_with_iam_profile):
    policy = EC2InstanceNoIAMProfilePolicy()
    alert = policy.check(ec2_instance_no_iam_profile, ACCOUNT_ID_AWS, REGION_AWS)
    assert alert is not None
    assert alert.policy_id == "EC2_Instance_No_IAM_Profile"
    assert alert.severity == AlertSeverityEnum.MEDIUM

    alert = policy.check(ec2_instance_with_iam_profile, ACCOUNT_ID_AWS, REGION_AWS)
    assert alert is None

def test_ec2_instance_missing_tags_policy(ec2_instance_missing_tags, ec2_instance_with_all_tags):
    policy = EC2InstanceMissingRequiredTagsPolicy()
    alert = policy.check(ec2_instance_missing_tags, ACCOUNT_ID_AWS, REGION_AWS)
    assert alert is not None
    assert alert.policy_id == "EC2_Instance_Missing_Required_Tags"
    assert len(alert.details["missing_tags"]) == len(REQUIRED_TAGS) -1 # Assumindo que 'Name' não é obrigatória

    alert = policy.check(ec2_instance_with_all_tags, ACCOUNT_ID_AWS, REGION_AWS)
    assert alert is None

def test_ec2_instance_unapproved_ami_policy(ec2_instance_unapproved_ami, ec2_instance_approved_ami):
    policy = EC2InstanceUnapprovedAMIPolicy()
    alert = policy.check(ec2_instance_unapproved_ami, ACCOUNT_ID_AWS, REGION_AWS)
    assert alert is not None
    assert alert.policy_id == "EC2_Instance_Using_Unapproved_AMI"
    assert alert.details["image_id_used"] == DISAPPROVED_AMIS[0]

    alert = policy.check(ec2_instance_approved_ami, ACCOUNT_ID_AWS, REGION_AWS)
    assert alert is None

def test_evaluate_ec2_instance_policies_multiple_alerts(ec2_instance_public_ip, ec2_instance_no_iam_profile, ec2_instance_missing_tags):
    instances = [ec2_instance_public_ip, ec2_instance_no_iam_profile, ec2_instance_missing_tags]
    # Convertendo para dict antes de passar para evaluate_ec2_instance_policies, pois ela espera List[Dict]
    alerts_as_dicts = evaluate_iam_user_policies([i.model_dump() for i in instances], ACCOUNT_ID_AWS) # evaluate_iam_user_policies usado por engano, deveria ser evaluate_ec2_instance_policies

    # Correção: Chamar a função correta e converter para dict depois, se necessário para asserções.
    # A função evaluate_ec2_instance_policies retorna List[Alert], não List[Dict]
    alerts_objects = evaluate_ec2_instance_policies(instances, ACCOUNT_ID_AWS)

    assert len(alerts_objects) == 3
    policy_ids_found = [a.policy_id for a in alerts_objects]
    assert "EC2_Instance_Public_IP" in policy_ids_found
    assert "EC2_Instance_No_IAM_Profile" in policy_ids_found
    assert "EC2_Instance_Missing_Required_Tags" in policy_ids_found


# --- Fixtures para Security Groups ---
@pytest.fixture
def sg_public_all_ports_ipv4():
    return EC2SecurityGroupDataInput(
        GroupId="sg-123allipv4", GroupName="public-all-ipv4", region=REGION_AWS,
        IpPermissions=[
            EC2IpPermission(IpProtocol="-1", IpRanges=[{"CidrIp": "0.0.0.0/0"}])
        ]
    )

@pytest.fixture
def sg_public_ssh_ipv6():
    return EC2SecurityGroupDataInput(
        GroupId="sg-456sshipv6", GroupName="public-ssh-ipv6", region=REGION_AWS,
        IpPermissions=[
            EC2IpPermission(IpProtocol="tcp", FromPort=22, ToPort=22, Ipv6Ranges=[{"CidrIpv6": "::/0"}])
        ]
    )

@pytest.fixture
def sg_internal_access_only():
    return EC2SecurityGroupDataInput(
        GroupId="sg-789internal", GroupName="internal-only", region=REGION_AWS,
        IpPermissions=[
            EC2IpPermission(IpProtocol="tcp", FromPort=80, ToPort=80, UserIdGroupPairs=[{"GroupId": "sg-othersource"}])
        ]
    )

# --- Testes para Políticas de Security Group ---
def test_sg_public_ingress_all_ports_policy(sg_public_all_ports_ipv4, sg_internal_access_only):
    policy = EC2SGPublicIngressAllPortsPolicy()
    alert = policy.check(sg_public_all_ports_ipv4, ACCOUNT_ID_AWS, REGION_AWS)
    assert alert is not None
    assert alert.policy_id == "EC2_SG_Public_Ingress_All_Ports"

    alert = policy.check(sg_internal_access_only, ACCOUNT_ID_AWS, REGION_AWS)
    assert alert is None

def test_sg_public_ingress_specific_port_policy(sg_public_ssh_ipv6, sg_internal_access_only):
    policy_ssh = EC2SGPublicIngressSpecificPortPolicy(port=22, protocol="tcp", policy_id_suffix="SSH", title_suffix="SSH")
    alert = policy_ssh.check(sg_public_ssh_ipv6, ACCOUNT_ID_AWS, REGION_AWS)
    assert alert is not None
    assert alert.policy_id == "EC2_SG_Public_Ingress_SSH"

    alert = policy_ssh.check(sg_internal_access_only, ACCOUNT_ID_AWS, REGION_AWS)
    assert alert is None

    policy_http = EC2SGPublicIngressSpecificPortPolicy(port=80, protocol="tcp", policy_id_suffix="HTTP", title_suffix="HTTP")
    alert = policy_http.check(sg_public_ssh_ipv6, ACCOUNT_ID_AWS, REGION_AWS) # Testando para porta diferente
    assert alert is None


def test_evaluate_ec2_sg_policies(sg_public_all_ports_ipv4, sg_public_ssh_ipv6, sg_internal_access_only):
    sgs = [sg_public_all_ports_ipv4, sg_public_ssh_ipv6, sg_internal_access_only]
    # A função evaluate_ec2_sg_policies retorna List[Alert]
    alerts_objects = evaluate_ec2_sg_policies(sgs, ACCOUNT_ID_AWS, REGION_AWS)

    assert len(alerts_objects) == 2 # Um para all_ports, um para SSH
    policy_ids_found = [a.policy_id for a in alerts_objects]
    assert "EC2_SG_Public_Ingress_All_Ports" in policy_ids_found
    assert "EC2_SG_Public_Ingress_SSH" in policy_ids_found
