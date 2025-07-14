import pytest
from unittest.mock import patch, MagicMock
import datetime

from app.huawei.huawei_cts_collector import get_huawei_cts_traces, _convert_sdk_trace_to_schema
from app.schemas.huawei.huawei_cts_schemas import CTSTraceCollection, CTSTrace, CTSUserIdentity
from app.core.config import settings # Para mockar as settings globais

# Mock das settings globais da Huawei
@pytest.fixture(autouse=True) # autouse para aplicar a todos os testes no módulo
def mock_huawei_settings(monkeypatch):
    monkeypatch.setattr(settings, "HUAWEICLOUD_SDK_AK", "test_ak")
    monkeypatch.setattr(settings, "HUAWEICLOUD_SDK_SK", "test_sk")
    monkeypatch.setattr(settings, "HUAWEICLOUD_SDK_PROJECT_ID", "test_project_id")
    monkeypatch.setattr(settings, "HUAWEICLOUD_SDK_DOMAIN_ID", "test_domain_id")

@pytest.fixture
def mock_cts_client():
    with patch("app.huawei.huawei_cts_collector.CtsClient") as mock_client_builder:
        mock_client_instance = MagicMock()
        # Configurar o builder para retornar a instância mockada
        mock_client_builder.new_builder.return_value.with_credentials.return_value.with_region_id.return_value.build.return_value = mock_client_instance
        yield mock_client_instance

# Exemplo de objeto Trace do SDK mockado (estrutura baseada em suposições)
class MockHuaweiSDKTrace:
    def __init__(self, i, region_id_val, domain_id_val):
        self.trace_id = f"sdk_trace_id_{i}"
        self.record_id = f"sdk_record_id_{i}" # Alternativa para traceId
        self.trace_name = f"UserLoginEvent_{i}"
        self.name = self.trace_name
        self.service_type = "IAM"
        self.time = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=i*10)).isoformat() + "Z"
        self.user = MagicMock()
        self.user.id = f"sdk_user_id_{i}"
        self.user.name = f"sdk_user_{i}"
        self.user.domain = MagicMock()
        self.user.domain.name = domain_id_val # Usar o domain_id do mock
        self.user.access_key_id = f"AKIATEST{i}"
        self.user.type = "IAMUser" # Exemplo
        self.source_ip = f"10.0.1.{i}"
        self.request = {"loginType": "Console"}
        self.response = {"status": "success"}
        self.resource_type = "identity.user"
        self.resource_name = f"sdk_user_{i}"
        self.region_id = region_id_val
        self.region = region_id_val # Alias
        self.code = None
        self.message = None
        self.api_version = "v3"
        self.is_read_only = False


def test_convert_sdk_trace_to_schema():
    mock_sdk_trace = MockHuaweiSDKTrace(1, "test-region", "test-domain")
    tracker_name_test = "system"

    schema_trace = _convert_sdk_trace_to_schema(mock_sdk_trace, tracker_name_test, "test-domain")

    assert schema_trace is not None
    assert schema_trace.traceId == "sdk_trace_id_1"
    assert schema_trace.traceName == "UserLoginEvent_1"
    assert schema_trace.eventSource == "IAM"
    assert isinstance(schema_trace.eventTime, datetime.datetime)
    assert schema_trace.userIdentity.userName == "sdk_user_1"
    assert schema_trace.userIdentity.domainName == "test-domain"
    assert schema_trace.trackerName == tracker_name_test


@pytest.mark.asyncio # Embora a função testada seja síncrona, o pytest-asyncio pode ser usado
async def test_get_huawei_cts_traces_success(mock_cts_client, mock_huawei_settings):
    # Configurar o mock do cliente CTS para retornar uma resposta simulada
    mock_response_page1 = MagicMock()
    mock_response_page1.traces = [MockHuaweiSDKTrace(i, "test-region", settings.HUAWEICLOUD_SDK_DOMAIN_ID) for i in range(2)]
    mock_response_page1.next_marker = "marker_next_page"

    mock_response_page2 = MagicMock()
    mock_response_page2.traces = [MockHuaweiSDKTrace(i + 2, "test-region", settings.HUAWEICLOUD_SDK_DOMAIN_ID) for i in range(1)]
    mock_response_page2.next_marker = None # Última página

    mock_cts_client.list_traces.side_effect = [mock_response_page1, mock_response_page2]

    result = get_huawei_cts_traces( # Chamar a função síncrona diretamente
        project_id=settings.HUAWEICLOUD_SDK_PROJECT_ID,
        region_id="test-region",
        domain_id=settings.HUAWEICLOUD_SDK_DOMAIN_ID,
        tracker_name="system",
        max_total_traces=5 # Limitar para o teste
    )

    assert isinstance(result, CTSTraceCollection)
    assert result.error_message is None
    assert len(result.traces) == 3
    assert result.traces[0].traceId == "sdk_trace_id_0"
    assert result.traces[2].traceId == "sdk_trace_id_2"
    assert result.next_marker is None # Deve ser None porque a segunda página foi a última
    assert mock_cts_client.list_traces.call_count == 2


@pytest.mark.asyncio
async def test_get_huawei_cts_traces_api_error(mock_cts_client, mock_huawei_settings):
    # Simular um erro do SDK
    mock_cts_client.list_traces.side_effect = Exception("Huawei SDK API Error")

    result = get_huawei_cts_traces(
        project_id=settings.HUAWEICLOUD_SDK_PROJECT_ID,
        region_id="test-region",
        domain_id=settings.HUAWEICLOUD_SDK_DOMAIN_ID
    )
    assert result.error_message is not None
    assert "Huawei SDK API Error" in result.error_message
    assert len(result.traces) == 0

def test_get_huawei_cts_traces_missing_config(monkeypatch):
    # Testar com configurações faltando
    monkeypatch.setattr(settings, "HUAWEICLOUD_SDK_AK", None)

    result = get_huawei_cts_traces(
        project_id="any_project",
        region_id="any_region"
    )
    assert result.error_message is not None
    assert "Huawei Cloud credentials" in result.error_message
