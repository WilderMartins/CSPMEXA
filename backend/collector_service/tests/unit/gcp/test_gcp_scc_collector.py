import pytest
from unittest.mock import patch, MagicMock, PropertyMock
import datetime

# Importar a função a ser testada e os schemas
from app.gcp.gcp_scc_collector import get_gcp_scc_findings, _convert_sdk_finding_to_schema
from app.schemas.gcp.gcp_scc_schemas import GCPSCCFindingCollection, GCPFinding

# Mock para google.auth.default() e o cliente SecurityCenterClient
@pytest.fixture(autouse=True)
def mock_gcp_scc_auth_and_client(monkeypatch):
    mock_credentials = MagicMock()
    mock_default_project_id = "mock-gcp-project"

    with patch("app.gcp.gcp_scc_collector.google.auth.default", return_value=(mock_credentials, mock_default_project_id)) as mock_auth_default:
        with patch("app.gcp.gcp_scc_collector.securitycenter_v1.SecurityCenterClient") as mock_scc_client_class:
            mock_scc_client_instance = MagicMock()
            mock_scc_client_class.return_value = mock_scc_client_instance
            yield mock_auth_default, mock_scc_client_instance

# Mock para um objeto Finding do SDK do GCP SCC
class MockSDKGCPFinding:
    def __init__(self, i, org_id, source_id):
        self.name = f"organizations/{org_id}/sources/{source_id}/findings/scc_finding_{i}"
        self.parent = f"organizations/{org_id}/sources/{source_id}"
        self.resource_name = f"//cloudresourcemanager.googleapis.com/projects/project_scc_{i}"
        self.state = 1 # ACTIVE (o enum real seria securitycenter_v1.types.Finding.State.ACTIVE)
        self.category = f"SCC_CAT_{i}"
        self.external_uri = f"https://scc.example.com/finding/{i}"

        # Mock para source_properties (Struct)
        mock_sp_items = {"scanner": f"Scanner_{i}", "rule_id": f"Rule_{i}"}
        self.source_properties = MagicMock()
        # Acessar .items() em um mock de Struct pode ser complicado, vamos simular o resultado de dict()
        # self.source_properties.items.return_value = mock_sp_items.items() # Não funciona bem com dict(Struct)
        # Em vez disso, vamos mockar o comportamento de Struct quando convertido para dict
        # No código real, `dict(sdk_finding.source_properties.items())` é usado.
        # Ou simplesmente `dict(sdk_finding.source_properties)` se for um Mapping.
        # Para o teste, vamos assumir que `sdk_finding.source_properties` se comporta como um dict-like.
        self.source_properties = mock_sp_items # Simular que já é um dict ou pode ser tratado como um

        # Mock para Timestamps (google.protobuf.timestamp_pb2.Timestamp)
        # Eles têm métodos ToDatetime() ou rfc3339()
        now = datetime.datetime.now(datetime.timezone.utc)
        self.event_time = MagicMock()
        self.event_time.ToDatetime.return_value = now - datetime.timedelta(days=i)
        self.create_time = MagicMock()
        self.create_time.ToDatetime.return_value = now - datetime.timedelta(days=i, minutes=5)
        self.update_time = MagicMock()
        self.update_time.ToDatetime.return_value = now - datetime.timedelta(minutes=i)

        self.severity = 2 # HIGH (o enum real seria securitycenter_v1.types.Finding.Severity.HIGH)
        self.canonical_name = f"scc.canonical.name.{i}"
        self.description = f"Description for SCC finding {i}"

# Mock para o ListFindingsResponse e ListFindingsResult
class MockListFindingsResult:
    def __init__(self, finding_obj):
        self.finding = finding_obj

class MockListFindingsResponse:
    def __init__(self, findings_list, next_page_token_val=None, total_size_val=None):
        self.list_findings_results = [MockListFindingsResult(f) for f in findings_list]
        self.next_page_token = next_page_token_val
        self.total_size = total_size_val


def test_convert_sdk_scc_finding_to_schema():
    mock_sdk_finding = MockSDKGCPFinding(1, "org123", "source456")

    # Mockar os enums do SDK para que a conversão para nome funcione
    with patch("app.gcp.gcp_scc_collector.securitycenter_v1.types.Finding.State") as MockStateEnum, \
         patch("app.gcp.gcp_scc_collector.securitycenter_v1.types.Finding.Severity") as MockSeverityEnum:
        MockStateEnum.return_value.name = "ACTIVE" # Simula State(1).name
        MockSeverityEnum.return_value.name = "HIGH" # Simula Severity(2).name

        schema_finding = _convert_sdk_finding_to_schema(mock_sdk_finding)

    assert schema_finding is not None
    assert schema_finding.name == mock_sdk_finding.name
    assert schema_finding.resourceName == mock_sdk_finding.resource_name
    assert schema_finding.state == "ACTIVE"
    assert schema_finding.severity == "HIGH"
    assert schema_finding.project_id == "project_scc_1"
    assert schema_finding.organization_id == "org123"
    assert schema_finding.source_id == "source456"
    assert schema_finding.finding_id == "scc_finding_1"
    assert schema_finding.sourceProperties.additional_properties["scanner"] == "Scanner_1"

@pytest.mark.asyncio
async def test_get_gcp_scc_findings_success(mock_gcp_scc_auth_and_client):
    _, mock_scc_client = mock_gcp_scc_auth_and_client

    mock_response_page1 = MockListFindingsResponse(
        [MockSDKGCPFinding(i, "org123", "sourceAll") for i in range(2)],
        next_page_token_val="next_scc_token"
    )
    mock_response_page2 = MockListFindingsResponse(
        [MockSDKGCPFinding(i + 2, "org123", "sourceAll") for i in range(1)],
        next_page_token_val=None # Última página
    )
    mock_scc_client.list_findings.side_effect = [mock_response_page1, mock_response_page2]

    test_parent = "organizations/org123/sources/-"
    result = await get_gcp_scc_findings( # Chamar a função async diretamente
        parent_resource=test_parent,
        max_total_results=5
    )

    assert isinstance(result, GCPSCCFindingCollection)
    assert result.error_message is None
    assert len(result.findings) == 3
    assert result.findings[0].name == "organizations/org123/sources/sourceAll/findings/scc_finding_0"
    assert result.findings[2].name == "organizations/org123/sources/sourceAll/findings/scc_finding_2"
    assert result.next_page_token is None
    assert mock_scc_client.list_findings.call_count == 2

@pytest.mark.asyncio
async def test_get_gcp_scc_findings_api_error(mock_gcp_scc_auth_and_client):
    _, mock_scc_client = mock_gcp_scc_auth_and_client
    from google.api_core.exceptions import ServiceUnavailable
    mock_scc_client.list_findings.side_effect = ServiceUnavailable("SCC API unavailable")

    result = await get_gcp_scc_findings(parent_resource="projects/proj1/sources/-")
    assert result.error_message is not None
    assert "Google API Error: 503 SCC API unavailable" in result.error_message # O mock de GoogleAPIError pode ser mais específico
    assert len(result.findings) == 0

@pytest.mark.asyncio
async def test_get_gcp_scc_findings_no_credentials(monkeypatch):
    # Testar o caso onde google.auth.default() falha
    with patch("app.gcp.gcp_scc_collector.google.auth.default", side_effect=DefaultCredentialsError("Creds not found")) as mock_auth_default_fail:
        # Não precisamos mockar o SCC client aqui, pois a falha ocorre antes
        result = await get_gcp_scc_findings(parent_resource="organizations/org1/sources/-")

    assert result.error_message is not None
    assert "GCP default credentials not found" in result.error_message
```
