import pytest
import datetime
from app.engine.gcp_scc_processing import process_gcp_scc_findings
from app.schemas.gcp.gcp_scc_input_schemas import (
    GCPSCCFindingCollectionInput,
    GCPFindingInput,
    GCPFindingSourcePropertiesInput
)
from app.schemas.alert_schema import AlertSeverityEnum

GCP_PARENT_RESOURCE = "organizations/1234567890" # Exemplo

@pytest.fixture
def scc_critical_finding():
    return GCPFindingInput(
        name=f"{GCP_PARENT_RESOURCE}/sources/source1/findings/finding_crit",
        parent=f"{GCP_PARENT_RESOURCE}/sources/source1",
        resourceName="//cloudresourcemanager.googleapis.com/projects/project-crit",
        state="ACTIVE",
        category="PERSISTENCE", # Exemplo de categoria
        externalUri="http://scc.example.com/crit",
        sourceProperties=GCPFindingSourcePropertiesInput(additional_properties={"DisplayName": "Critical Vulnerability Found"}),
        eventTime=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1),
        createTime=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1),
        severity="CRITICAL", # String do GCP SCC
        canonicalName="gcp.scc.persistence.critical_finding_type",
        description="A critical persistence technique was detected.",
        project_id="project-crit",
        organization_id="org123", # Extraído no coletor
        source_id="source1",      # Extraído no coletor
        finding_id="finding_crit" # Extraído no coletor
    )

@pytest.fixture
def scc_medium_misconfig_finding():
    return GCPFindingInput(
        name=f"{GCP_PARENT_RESOURCE}/sources/source2/findings/finding_med_misconfig",
        parent=f"{GCP_PARENT_RESOURCE}/sources/source2",
        resourceName="//compute.googleapis.com/projects/project-med/zones/us-central1-a/instances/vm-123",
        state="ACTIVE",
        category="MISCONFIGURATION",
        externalUri="http://scc.example.com/med_misconfig",
        sourceProperties=GCPFindingSourcePropertiesInput(additional_properties={
            "DisplayName": "Public IP Address on VM",
            "ResourceType": "Instance",
            "Explanation": "VM instance has a public IP address."
        }),
        eventTime=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=5),
        createTime=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=5),
        severity="MEDIUM",
        canonicalName="gcp.scc.misconfig.public_ip_vm",
        project_id="project-med"
    )

def test_process_gcp_scc_findings_maps_correctly(scc_critical_finding, scc_medium_misconfig_finding):
    finding_collection = GCPSCCFindingCollectionInput(
        findings=[scc_critical_finding, scc_medium_misconfig_finding],
        parent_resource_queried=GCP_PARENT_RESOURCE
    )
    alerts = process_gcp_scc_findings(finding_collection, GCP_PARENT_RESOURCE)

    assert len(alerts) == 2

    # Checar alerta crítico
    alert_crit = next(a for a in alerts if a["policy_id"] == "SCC_PERSISTENCE") # SCC_category
    assert alert_crit["severity"] == AlertSeverityEnum.CRITICAL
    assert alert_crit["title"] == "GCP SCC: PERSISTENCE" # Usa a categoria como título se canonical_name não for formatado
    assert alert_crit["resource_id"] == scc_critical_finding.resource_name
    assert alert_crit["account_id"] == "project-crit"
    assert "A critical persistence technique was detected." in alert_crit["description"]
    assert alert_crit["details"]["scc_finding_name"] == scc_critical_finding.name

    # Checar alerta de misconfiguração média
    # O policy_id pode ser SCC_public_ip_vm se canonical_name for "gcp.scc.misconfig.public_ip_vm"
    alert_med = next(a for a in alerts if "public_ip_vm" in a["policy_id"])
    assert alert_med["severity"] == AlertSeverityEnum.MEDIUM
    assert "Public IP Address on VM" in alert_med["description"] # Descrição de source_properties
    assert alert_med["resource_id"] == scc_medium_misconfig_finding.resource_name
    assert alert_med["account_id"] == "project-med"
    assert alert_med["details"]["scc_finding_category"] == "MISCONFIGURATION"


def test_process_gcp_scc_findings_collection_error():
    error_msg = "Global SCC collection failed."
    finding_collection_error = GCPSCCFindingCollectionInput(
        error_message=error_msg,
        parent_resource_queried=GCP_PARENT_RESOURCE
    )
    alerts = process_gcp_scc_findings(finding_collection_error, GCP_PARENT_RESOURCE)

    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["policy_id"] == "GCP_SCC_GlobalCollection_Error"
    assert alert["severity"] == AlertSeverityEnum.MEDIUM
    assert error_msg in alert["description"]

def test_process_gcp_scc_findings_item_parsing_error():
    finding_with_error = GCPFindingInput(
        name="error_finding_name",
        parent="error_parent",
        resource_name="error_resource",
        state="ACTIVE",
        category="ERROR_CAT",
        event_time=datetime.datetime.now(datetime.timezone.utc),
        create_time=datetime.datetime.now(datetime.timezone.utc),
        severity="HIGH",
        collection_error_details="Failed to parse this specific finding."
    )
    finding_collection = GCPSCCFindingCollectionInput(
        findings=[finding_with_error],
        parent_resource_queried=GCP_PARENT_RESOURCE
    )
    alerts = process_gcp_scc_findings(finding_collection, GCP_PARENT_RESOURCE)

    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["policy_id"] == "GCP_SCC_FindingParsing_Error"
    assert alert["severity"] == AlertSeverityEnum.INFORMATIONAL
    assert "Failed to parse this specific finding" in alert["description"]
    assert alert["resource_id"] == "error_finding_name"

def test_process_gcp_scc_findings_empty_list():
    finding_collection_empty = GCPSCCFindingCollectionInput(
        findings=[],
        parent_resource_queried=GCP_PARENT_RESOURCE
    )
    alerts = process_gcp_scc_findings(finding_collection_empty, GCP_PARENT_RESOURCE)
    assert len(alerts) == 0

def test_process_gcp_scc_findings_no_collection_input():
    alerts = process_gcp_scc_findings(None, GCP_PARENT_RESOURCE)
    assert len(alerts) == 0

```
