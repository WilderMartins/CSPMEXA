import pytest
import datetime
from app.engine.huawei_cts_policies import evaluate_huawei_cts_policies
from app.schemas.huawei.huawei_cts_input_schemas import CTSTraceCollectionInput, CTSTraceInput, CTSUserIdentityInput
from app.schemas.alert_schema import AlertSeverityEnum

ACCOUNT_ID_HUAWEI = "huawei_project_123"

@pytest.fixture
def sample_critical_cts_trace():
    return CTSTraceInput(
        traceId="trace-critical-op",
        traceName="DeleteTracker", # Evento crítico
        eventSource="cts.huawei.com",
        eventTime=datetime.datetime.now(datetime.timezone.utc),
        eventName="DeleteTracker",
        userIdentity=CTSUserIdentityInput(userName="attacker", domainName="test-domain"),
        sourceIPAddress="1.2.3.4",
        resourceName="system-tracker",
        resourceType="CTS::Tracker",
        regionId="cn-north-1",
        domainId="test-domain"
    )

@pytest.fixture
def sample_normal_cts_trace():
    return CTSTraceInput(
        traceId="trace-normal-op",
        traceName="ListTrackers",
        eventSource="cts.huawei.com",
        eventTime=datetime.datetime.now(datetime.timezone.utc),
        eventName="ListTrackers",
        userIdentity=CTSUserIdentityInput(userName="auditor", domainName="test-domain"),
        sourceIPAddress="10.0.0.5",
        resourceName="N/A",
        resourceType="CTS::TrackerList",
        regionId="cn-north-1",
        domainId="test-domain"
    )

def test_evaluate_huawei_cts_critical_operation(sample_critical_cts_trace):
    trace_collection = CTSTraceCollectionInput(traces=[sample_critical_cts_trace])
    alerts = evaluate_huawei_cts_policies(trace_collection, ACCOUNT_ID_HUAWEI)

    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["policy_id"] == "CTS_Critical_Operation_Detected"
    assert alert["title"] == "Huawei CTS: Critical Operation Detected - DeleteTracker"
    assert alert["severity"] == AlertSeverityEnum.CRITICAL
    assert alert["resource_id"] == "system-tracker"
    assert ACCOUNT_ID_HUAWEI in alert["description"]
    assert "attacker@test-domain" in alert["description"]

def test_evaluate_huawei_cts_normal_operation(sample_normal_cts_trace):
    trace_collection = CTSTraceCollectionInput(traces=[sample_normal_cts_trace])
    alerts = evaluate_huawei_cts_policies(trace_collection, ACCOUNT_ID_HUAWEI)
    assert len(alerts) == 0

def test_evaluate_huawei_cts_no_traces():
    trace_collection = CTSTraceCollectionInput(traces=[])
    alerts = evaluate_huawei_cts_policies(trace_collection, ACCOUNT_ID_HUAWEI)
    assert len(alerts) == 0

def test_evaluate_huawei_cts_collection_error():
    error_msg = "Failed to fetch any logs."
    trace_collection = CTSTraceCollectionInput(error_message=error_msg)
    alerts = evaluate_huawei_cts_policies(trace_collection, ACCOUNT_ID_HUAWEI)

    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["policy_id"] == "CTS_GlobalCollection_Error"
    assert alert["severity"] == AlertSeverityEnum.MEDIUM
    assert error_msg in alert["description"]

def test_evaluate_huawei_cts_trace_parsing_error():
    trace_with_error = CTSTraceInput(
        traceId="trace-parse-error",
        traceName="SomeOperation",
        eventTime=datetime.datetime.now(datetime.timezone.utc),
        collection_error_details="Failed to parse this specific trace object."
    )
    trace_collection = CTSTraceCollectionInput(traces=[trace_with_error])
    alerts = evaluate_huawei_cts_policies(trace_collection, ACCOUNT_ID_HUAWEI)

    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["policy_id"] == "CTS_TraceParsing_Error"
    assert alert["severity"] == AlertSeverityEnum.INFORMATIONAL
    assert "Failed to parse this specific trace object" in alert["description"]

```
