import pytest
import datetime
from policy_engine_service.app.engine.huawei_csg_policies import evaluate_huawei_csg_policies
from policy_engine_service.app.schemas.huawei.huawei_csg_input_schemas import (
    CSGRiskCollectionInput,
    CSGRiskItemInput,
    CSGRiskResourceInfoInput
)
from policy_engine_service.app.schemas.alert_schema import AlertSeverityEnum

ACCOUNT_ID_HUAWEI_CSG = "huawei_project_csg_test"

@pytest.fixture
def csg_critical_risk_item():
    return CSGRiskItemInput(
        riskId="csg-risk-crit-123",
        checkName="HighRiskPortOpenedToInternet",
        description="ECS instance has port 22 (SSH) open to 0.0.0.0/0.",
        severity="CRITICAL", # Conforme o CSG reportaria
        status="Unhandled",
        resource=CSGRiskResourceInfoInput(
            id="ecs-instance-id-1",
            name="ecs-prod-server-01",
            type="ECS",
            regionId="cn-north-4",
            projectId=ACCOUNT_ID_HUAWEI_CSG
        ),
        suggestion="Restrict SSH access to known IPs.",
        firstDetectedTime=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=2),
        lastDetectedTime=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
    )

@pytest.fixture
def csg_medium_risk_item_handled():
    return CSGRiskItemInput(
        riskId="csg-risk-med-456",
        checkName="OBSBucketPublicRead",
        description="OBS bucket allows public read access.",
        severity="MEDIUM", # Conforme o CSG reportaria
        status="Handled", # Já tratado
        resource=CSGRiskResourceInfoInput(
            id="obs-bucket-id-2",
            name="obs-public-bucket-temp",
            type="OBS",
            regionId="cn-north-1",
            projectId=ACCOUNT_ID_HUAWEI_CSG
        ),
        suggestion="Remove public read ACL/policy from the bucket.",
        firstDetectedTime=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=5),
        lastDetectedTime=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
    )

def test_evaluate_huawei_csg_critical_risk(csg_critical_risk_item):
    risk_collection = CSGRiskCollectionInput(
        risks=[csg_critical_risk_item],
        project_id_queried=ACCOUNT_ID_HUAWEI_CSG,
        region_id_queried="cn-north-4" # Exemplo
    )
    alerts = evaluate_huawei_csg_policies(risk_collection, ACCOUNT_ID_HUAWEI_CSG)

    assert len(alerts) == 1
    alert = alerts[0]
    # O policy_id é formado a partir do checkName
    assert alert["policy_id"] == "CSG_HIGHRISKPORTOPENEDTOINTERNET"
    assert alert["title"] == "Huawei CSG Finding: HighRiskPortOpenedToInternet"
    assert alert["severity"] == AlertSeverityEnum.CRITICAL # Mapeado corretamente
    assert alert["resource_id"] == "ecs-instance-id-1"
    assert "ECS instance has port 22 (SSH) open" in alert["description"]

def test_evaluate_huawei_csg_medium_risk_creates_alert(csg_medium_risk_item_handled):
    # A política atual cria alertas para todos os riscos reportados, independentemente do status ou severidade.
    # Apenas mapeia a severidade.
    risk_collection = CSGRiskCollectionInput(
        risks=[csg_medium_risk_item_handled],
        project_id_queried=ACCOUNT_ID_HUAWEI_CSG
    )
    alerts = evaluate_huawei_csg_policies(risk_collection, ACCOUNT_ID_HUAWEI_CSG)

    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["policy_id"] == "CSG_OBSBUCKETPUBLICREAD"
    assert alert["severity"] == AlertSeverityEnum.MEDIUM # Mapeado de "MEDIUM"
    assert alert["resource_id"] == "obs-bucket-id-2"
    # O status "Handled" do CSG não impede a criação do alerta CSPMEXA por enquanto.

def test_evaluate_huawei_csg_collection_error():
    error_msg = "Failed to fetch CSG risks due to API timeout."
    risk_collection_error = CSGRiskCollectionInput(
        error_message=error_msg,
        project_id_queried=ACCOUNT_ID_HUAWEI_CSG
    )
    alerts = evaluate_huawei_csg_policies(risk_collection_error, ACCOUNT_ID_HUAWEI_CSG)

    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["policy_id"] == "CSG_GlobalCollection_Error"
    assert alert["severity"] == AlertSeverityEnum.MEDIUM
    assert error_msg in alert["description"]

def test_evaluate_huawei_csg_risk_item_parsing_error():
    risk_with_error = CSGRiskItemInput(
        riskId="error-risk",
        checkName="ErrorCheck",
        resource=CSGRiskResourceInfoInput(id="error-res"), # riskId e resource são obrigatórios no schema
        collection_error_details="Failed to parse this specific CSG risk."
    )
    risk_collection = CSGRiskCollectionInput(
        risks=[risk_with_error],
        project_id_queried=ACCOUNT_ID_HUAWEI_CSG
    )
    alerts = evaluate_huawei_csg_policies(risk_collection, ACCOUNT_ID_HUAWEI_CSG)

    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["policy_id"] == "CSG_RiskItemParsing_Error"
    assert alert["severity"] == AlertSeverityEnum.INFORMATIONAL
    assert "Failed to parse this specific CSG risk" in alert["description"]
