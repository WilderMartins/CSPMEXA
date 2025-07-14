import logging
from typing import List, Optional, Dict, Any
import datetime
import json # Para parsing de request/response se forem strings JSON
import uuid # Para fallback de traceId

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcts.v3 import CtsClient, ListTracesRequest
# O nome real do objeto Trace do SDK pode variar, SdkTrace é um placeholder.
# from huaweicloudsdkcts.v3.model import Trace as SdkTrace

from app.schemas.huawei.huawei_cts_schemas import CTSTrace, CTSTraceCollection, CTSUserIdentity
from app.core.config import settings

logger = logging.getLogger(__name__)

def _convert_sdk_trace_to_schema(sdk_trace_obj: Any, tracker_name: Optional[str], domain_id_sdk: Optional[str]) -> Optional[CTSTrace]:
    if not sdk_trace_obj:
        return None

    try:
        # User Identity processing
        user_identity_schema = None
        sdk_user_identity = getattr(sdk_trace_obj, 'user_identity', getattr(sdk_trace_obj, 'user', None))
        if sdk_user_identity:
            try:
                user_identity_schema = CTSUserIdentity(
                    type=str(getattr(sdk_user_identity, 'type', 'N/A')),
                    principalId=str(getattr(sdk_user_identity, 'principal_id', getattr(sdk_user_identity, 'id', 'N/A'))),
                    userName=str(getattr(sdk_user_identity, 'name', getattr(sdk_user_identity, 'user_name', 'N/A'))),
                    domainName=str(getattr(sdk_user_identity, 'domain_name', getattr(sdk_user_identity, 'domain', {}).get('name', 'N/A'))),
                    accessKeyId=str(getattr(sdk_user_identity, 'access_key_id', 'N/A'))
                )
            except Exception as e_user:
                logger.warning(f"Could not fully parse user identity for trace: {e_user}")
                user_identity_schema = CTSUserIdentity(type="ErrorParsing")


        # Request Parameters processing
        parsed_request_params = None
        raw_request_params = getattr(sdk_trace_obj, 'request_parameters', getattr(sdk_trace_obj, 'request', None))
        if isinstance(raw_request_params, str):
            try:
                parsed_request_params = json.loads(raw_request_params)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse requestParameters JSON for trace {getattr(sdk_trace_obj, 'trace_id', 'UNKNOWN')}")
                parsed_request_params = {"raw_unparsed_request": raw_request_params}
        elif isinstance(raw_request_params, dict):
            parsed_request_params = raw_request_params

        # Response Elements processing
        parsed_response_elements = None
        raw_response_elements = getattr(sdk_trace_obj, 'response_elements', getattr(sdk_trace_obj, 'response', None))
        if isinstance(raw_response_elements, str):
            try:
                parsed_response_elements = json.loads(raw_response_elements)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse responseElements JSON for trace {getattr(sdk_trace_obj, 'trace_id', 'UNKNOWN')}")
                parsed_response_elements = {"raw_unparsed_response": raw_response_elements}
        elif isinstance(raw_response_elements, dict):
            parsed_response_elements = raw_response_elements

        # Event Time processing
        event_time_dt = None
        event_time_val = getattr(sdk_trace_obj, 'event_time', getattr(sdk_trace_obj, 'time', None))
        if isinstance(event_time_val, (int, float)): # Epoch ms or s
            try:
                # Se for ms, dividir por 1000. Se for s, não. Precisaria saber qual é. Assumindo ms.
                event_time_dt = datetime.datetime.fromtimestamp(event_time_val / 1000.0, tz=datetime.timezone.utc)
            except ValueError:
                logger.warning(f"Could not parse epoch timestamp '{event_time_val}' for trace.")
        elif isinstance(event_time_val, str): # ISO 8601 string
            try:
                # Remover 'Z' e adicionar offset UTC se Pydantic/datetime precisar
                if event_time_val.endswith("Z"):
                    event_time_val = event_time_val[:-1] + "+00:00"
                event_time_dt = datetime.datetime.fromisoformat(event_time_val)
            except ValueError:
                logger.warning(f"Could not parse ISO timestamp string '{event_time_val}' for trace.")
        elif isinstance(event_time_val, datetime.datetime):
             event_time_dt = event_time_val

        if not event_time_dt: # Fallback
            event_time_dt = datetime.datetime.now(datetime.timezone.utc)
            logger.warning(f"Event time missing or unparseable for trace {getattr(sdk_trace_obj, 'trace_id', 'UNKNOWN')}, using current time.")

        # traceId e traceName são obrigatórios no schema, usar fallbacks.
        trace_id_val = str(getattr(sdk_trace_obj, 'trace_id', getattr(sdk_trace_obj, 'id', getattr(sdk_trace_obj, 'record_id', None) or uuid.uuid4())))
        trace_name_val = str(getattr(sdk_trace_obj, 'trace_name', getattr(sdk_trace_obj, 'name', 'UnknownTraceName')))
        event_name_val = str(getattr(sdk_trace_obj, 'event_name', getattr(sdk_trace_obj, 'operation', trace_name_val))) # Tentar 'operation' como fallback


        return CTSTrace(
            traceId=trace_id_val,
            traceName=trace_name_val,
            traceRating=str(getattr(sdk_trace_obj, 'trace_rating', '')),
            eventSource=str(getattr(sdk_trace_obj, 'service_type', getattr(sdk_trace_obj, 'service_name', getattr(sdk_trace_obj, 'event_source', '')))),
            eventTime=event_time_dt,
            eventName=event_name_val,
            userIdentity=user_identity_schema,
            sourceIPAddress=str(getattr(sdk_trace_obj, 'source_ip_address', getattr(sdk_trace_obj, 'source_ip', ''))),
            requestParameters=parsed_request_params,
            responseElements=parsed_response_elements,
            resourceType=str(getattr(sdk_trace_obj, 'resource_type', '')),
            resourceName=str(getattr(sdk_trace_obj, 'resource_name', '')),
            regionId=str(getattr(sdk_trace_obj, 'region_id', getattr(sdk_trace_obj, 'region', ''))),
            errorCode=str(getattr(sdk_trace_obj, 'error_code', getattr(sdk_trace_obj, 'code', ''))),
            errorMessage=str(getattr(sdk_trace_obj, 'error_message', getattr(sdk_trace_obj, 'message', ''))),
            apiVersion=str(getattr(sdk_trace_obj, 'api_version', '')),
            readOnly=bool(getattr(sdk_trace_obj, 'read_only', False)),
            trackerName=str(tracker_name or ''),
            domainId=str(domain_id_sdk or (user_identity_schema.domainName if user_identity_schema else None) or '')
        )
    except Exception as e:
        logger.error(f"Critical error converting SDK trace object to schema: {e}", exc_info=True)
        return CTSTrace(
            traceId=str(getattr(sdk_trace_obj, 'trace_id', 'CONVERSION_ERROR_ID_' + str(uuid.uuid4()))),
            traceName="CONVERSION_ERROR_NAME",
            eventTime=datetime.datetime.now(datetime.timezone.utc),
            collection_error_details=f"Failed to parse SDK trace object due to critical error: {str(e)}"
        )

def get_huawei_cts_traces( # Removido async def, pois a chamada SDK é síncrona
    project_id: str,
    region_id: str,
    domain_id: Optional[str] = None,
    tracker_name: str = "system",
    limit_per_call: int = 100,
    max_total_traces: int = 1000,
    time_from: Optional[datetime.datetime] = None,
    time_to: Optional[datetime.datetime] = None,
) -> CTSTraceCollection:
    auth_domain_id = domain_id or settings.HUAWEICLOUD_SDK_DOMAIN_ID or project_id

    if not all([settings.HUAWEICLOUD_SDK_AK, settings.HUAWEICLOUD_SDK_SK, auth_domain_id, project_id, region_id]):
        msg = "Huawei Cloud credentials (AK, SK, Domain ID, Project ID) or region_id are not fully configured."
        logger.error(msg)
        return CTSTraceCollection(error_message=msg)

    credentials = BasicCredentials(
        ak=settings.HUAWEICLOUD_SDK_AK,
        sk=settings.HUAWEICLOUD_SDK_SK,
        project_id=project_id,
        domain_id=auth_domain_id
    )

    cts_client = CtsClient.new_builder() \
        .with_credentials(credentials) \
        .with_region_id(region_id) \
        .build()

    all_traces_schemas: List[CTSTrace] = []
    next_marker: Optional[str] = None
    collected_count = 0

    if time_to is None:
        time_to = datetime.datetime.now(datetime.timezone.utc)
    if time_from is None:
        time_from = time_to - datetime.timedelta(days=1)

    from_timestamp_ms = int(time_from.timestamp() * 1000)
    to_timestamp_ms = int(time_to.timestamp() * 1000)

    try:
        while collected_count < max_total_traces:
            request_limit = min(limit_per_call, max_total_traces - collected_count)
            if request_limit <=0: # Evitar limit 0 se max_total_traces for atingido exatamente
                break

            request = ListTracesRequest(
                tracker_name=tracker_name,
                limit=request_limit,
                next=next_marker if next_marker else None,
                _from=from_timestamp_ms,
                to=to_timestamp_ms,
            )

            logger.info(f"Fetching CTS traces for tracker '{tracker_name}', page_marker: {next_marker}, limit: {request.limit}")

            # Chamada Síncrona Real ao SDK Huawei
            # O controller (FastAPI endpoint) deve chamar esta função get_huawei_cts_traces
            # usando `await run_in_threadpool(...)` para não bloquear o event loop.
            response_sdk = cts_client.list_traces(request)

            sdk_traces = getattr(response_sdk, 'traces', [])
            if sdk_traces:
                for sdk_trace in sdk_traces:
                    schema_trace = _convert_sdk_trace_to_schema(sdk_trace, tracker_name, auth_domain_id)
                    if schema_trace:
                        all_traces_schemas.append(schema_trace)
                collected_count += len(sdk_traces)

            next_marker = getattr(response_sdk, 'next_marker', getattr(response_sdk, 'next', None)) # Alguns SDKs usam 'next'
            if not next_marker or collected_count >= max_total_traces:
                break

        logger.info(f"Collected {collected_count} CTS traces for tracker '{tracker_name}'.")
        return CTSTraceCollection(
            traces=all_traces_schemas,
            next_marker=next_marker,
            total_count=collected_count
        )

    except Exception as e:
        logger.error(f"Error collecting CTS traces for tracker '{tracker_name}': {e}", exc_info=True)
        return CTSTraceCollection(error_message=f"Failed to collect CTS traces: {str(e)}")


if __name__ == "__main__":
    # Teste local já estava comentado, mantendo assim.
    print("Coletor CTS Huawei refinado. Adapte com chamadas reais ao SDK e documentação.")
