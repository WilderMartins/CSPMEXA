import logging
from typing import List, Optional, Dict, Any
import datetime
import uuid # Para fallback de ID

from google.cloud import logging_v2
from google.auth.exceptions import DefaultCredentialsError
from google.api_core.exceptions import GoogleAPIError, InvalidArgument
from google.protobuf.json_format import MessageToDict
# Importar o tipo AuditLog se quisermos desempacotar o protoPayload explicitamente
# from google.cloud.audit import audit_log_pb2


from app.schemas.gcp.gcp_cloud_audit_log_schemas import GCPLogEntry, GCPCloudAuditLogCollection, GCPLogEntryOperation, GCPLogEntrySourceLocation
# Não precisamos de get_gcp_project_id aqui, pois os project_ids são passados como parâmetro.

logger = logging.getLogger(__name__)

def _convert_protobuf_timestamp_to_datetime(pb_timestamp: Any) -> Optional[datetime.datetime]:
    if pb_timestamp and hasattr(pb_timestamp, "ToDatetime") and callable(pb_timestamp.ToDatetime):
        try:
            dt = pb_timestamp.ToDatetime() # Geralmente já é UTC, mas o SDK pode variar.
            if dt.tzinfo is None: # Se for naive, assumir UTC.
                return dt.replace(tzinfo=datetime.timezone.utc)
            return dt.astimezone(datetime.timezone.utc) # Garantir que é UTC
        except Exception as e:
            logger.warning(f"Could not convert protobuf timestamp to datetime: {e}")
    elif isinstance(pb_timestamp, str): # Se já for uma string ISO
        try:
            dt_str = pb_timestamp
            if dt_str.endswith("Z"): # Python <3.11 fromisoformat não gosta de 'Z' diretamente
                 dt_str = dt_str[:-1] + "+00:00"
            return datetime.datetime.fromisoformat(dt_str)
        except ValueError:
            logger.warning(f"Could not parse ISO timestamp string from LogEntry: {pb_timestamp}")
    return None


def _convert_sdk_log_entry_to_schema(sdk_log_entry: logging_v2.types.LogEntry) -> Optional[GCPLogEntry]:
    if not sdk_log_entry:
        return None

    try:
        proto_payload_dict = None
        # O SDK google-cloud-logging >v2.0.0 parseia o protoPayload para um dict se for AuditLog.
        # Se for um proto genérico, pode ser um objeto 'Any'.
        if sdk_log_entry.proto_payload:
            if isinstance(sdk_log_entry.proto_payload, dict): # Já parseado pelo SDK (comum para AuditLog)
                 proto_payload_dict = sdk_log_entry.proto_payload
            elif hasattr(sdk_log_entry.proto_payload, "type_url"): # Objeto 'Any'
                try:
                    # Tentar desempacotar se soubermos o tipo, ex: AuditLog
                    # if sdk_log_entry.proto_payload.Is(audit_log_pb2.AuditLog.DESCRIPTOR):
                    #    unpacked_payload = audit_log_pb2.AuditLog()
                    #    sdk_log_entry.proto_payload.Unpack(unpacked_payload)
                    #    proto_payload_dict = MessageToDict(unpacked_payload)
                    # else: # Fallback para MessageToDict genérico se não for AuditLog
                    proto_payload_dict = MessageToDict(sdk_log_entry.proto_payload)
                    logger.debug(f"ProtoPayload (type: {sdk_log_entry.proto_payload.type_url}) converted to dict.")
                except Exception as e_proto:
                    logger.warning(f"Could not fully parse protoPayload for log {sdk_log_entry.log_name} insertId {sdk_log_entry.insert_id}: {e_proto}")
                    proto_payload_dict = {"error_parsing_protoPayload": str(e_proto), "type_url": getattr(sdk_log_entry.proto_payload, "type_url", "UnknownType")}
            else: # Outro tipo inesperado
                logger.warning(f"Unexpected protoPayload type for log {sdk_log_entry.log_name}: {type(sdk_log_entry.proto_payload)}")
                proto_payload_dict = {"raw_proto_payload_representation": str(sdk_log_entry.proto_payload)}


        json_payload_dict = None
        if sdk_log_entry.json_payload: # json_payload já é um dict-like (Struct)
            try:
                json_payload_dict = dict(sdk_log_entry.json_payload.items())
            except Exception as e_json:
                 logger.warning(f"Could not convert jsonPayload Struct to dict for log {sdk_log_entry.log_name} insertId {sdk_log_entry.insert_id}: {e_json}")
                 json_payload_dict = {"error_parsing_jsonPayload": str(e_json)}

        audit_service_name, audit_method_name, audit_resource_name = None, None, None
        audit_principal, audit_caller_ip = None, None

        # Extrair campos específicos do AuditLog se o protoPayload for um AuditLog
        if proto_payload_dict and isinstance(proto_payload_dict, dict) and \
           proto_payload_dict.get("@type") == "type.googleapis.com/google.cloud.audit.AuditLog":
            audit_service_name = proto_payload_dict.get("serviceName")
            audit_method_name = proto_payload_dict.get("methodName")
            audit_resource_name = proto_payload_dict.get("resourceName")
            auth_info = proto_payload_dict.get("authenticationInfo")
            if isinstance(auth_info, dict):
                audit_principal = auth_info.get("principalEmail")
            req_meta = proto_payload_dict.get("requestMetadata")
            if isinstance(req_meta, dict):
                audit_caller_ip = req_meta.get("callerIp")

        timestamp_dt = _convert_protobuf_timestamp_to_datetime(sdk_log_entry.timestamp)
        receive_timestamp_dt = _convert_protobuf_timestamp_to_datetime(sdk_log_entry.receive_timestamp)

        # O SDK retorna resource como um MonitoredResource protobuf.
        # resource.labels é um protobuf MapField que se comporta como um dict.
        resource_labels_dict = dict(sdk_log_entry.resource.labels.items()) if sdk_log_entry.resource and hasattr(sdk_log_entry.resource, 'labels') else {}
        resource_dict_for_schema = {
            "type": getattr(sdk_log_entry.resource, 'type', None),
            "labels": resource_labels_dict
        }

        return GCPLogEntry(
            logName=sdk_log_entry.log_name or f"unknown_log_{uuid.uuid4()}",
            resource=resource_dict_for_schema,
            timestamp=timestamp_dt or datetime.datetime.now(datetime.timezone.utc),
            receiveTimestamp=receive_timestamp_dt,
            severity=logging_v2.types.LogSeverity(sdk_log_entry.severity).name if sdk_log_entry.severity else "DEFAULT",
            insertId=sdk_log_entry.insert_id or str(uuid.uuid4()),
            httpRequest=dict(sdk_log_entry.http_request.items()) if sdk_log_entry.http_request and hasattr(sdk_log_entry.http_request, 'items') else None,
            labels=dict(sdk_log_entry.labels.items()) if sdk_log_entry.labels else None,
            operation=GCPLogEntryOperation(**dict(sdk_log_entry.operation.items())) if sdk_log_entry.operation and hasattr(sdk_log_entry.operation, 'items') else None,
            trace=sdk_log_entry.trace,
            spanId=sdk_log_entry.span_id,
            traceSampled=sdk_log_entry.trace_sampled,
            sourceLocation=GCPLogEntrySourceLocation(**dict(sdk_log_entry.source_location.items())) if sdk_log_entry.source_location and hasattr(sdk_log_entry.source_location, 'items') else None,
            textPayload=sdk_log_entry.text_payload,
            jsonPayload=json_payload_dict,
            protoPayload=proto_payload_dict,
            audit_log_service_name=audit_service_name,
            audit_log_method_name=audit_method_name,
            audit_log_resource_name=audit_resource_name,
            audit_log_principal_email=audit_principal,
            audit_log_caller_ip=audit_caller_ip
        )
    except Exception as e:
        logger.error(f"Critical error converting SDK LogEntry: {e}", exc_info=True)
        return GCPLogEntry(
            logName=getattr(sdk_log_entry, 'log_name', f'CONVERSION_ERROR_LOG_{uuid.uuid4()}'),
            resource={},
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            insertId=getattr(sdk_log_entry, 'insert_id', str(uuid.uuid4())),
            collection_error_details=f"Failed to parse SDK LogEntry: {str(e)}"
        )

def get_gcp_cloud_audit_logs(
    resource_names: List[str],
    log_filter: Optional[str] = None,
    max_results_per_call: int = 1000,
    max_total_results: int = 10000,
    order_by: str = "timestamp desc"
) -> GCPCloudAuditLogCollection:
    all_log_entries_schemas: List[GCPLogEntry] = []
    # page_token é gerenciado pelo iterador do SDK para list_log_entries
    collected_count = 0

    # Filtro default para pegar apenas AuditLogs se nenhum filtro específico for fornecido.
    # Se um log_filter for fornecido, ele deve ser específico o suficiente.
    # Este filtro é amplo, mas garante que estamos pegando entradas que são AuditLogs.
    base_audit_filter = 'protoPayload.@type="type.googleapis.com/google.cloud.audit.AuditLog"'
    final_filter = f"({log_filter}) AND ({base_audit_filter})" if log_filter else base_audit_filter

    try:
        credentials, _ = google.auth.default()
        logging_client = logging_v2.LoggingServiceV2Client(credentials=credentials) # Corrigido para nome da classe correta

        logger.info(f"Fetching GCP Cloud Audit Logs for resources: {resource_names}, filter: '{final_filter}'")

        entries_iterator = logging_client.list_log_entries(
            resource_names=resource_names,
            filter_=final_filter,
            order_by=order_by,
            page_size=max_results_per_call
        )

        for entry in entries_iterator:
            if collected_count >= max_total_results:
                logger.info(f"Reached max_total_results ({max_total_results}) for Cloud Audit Logs.")
                break
            schema_entry = _convert_sdk_log_entry_to_schema(entry)
            if schema_entry:
                all_log_entries_schemas.append(schema_entry)
            collected_count += 1

        next_page_token_from_iterator = entries_iterator.next_page_token if hasattr(entries_iterator, 'next_page_token') and collected_count < max_total_results else None

        logger.info(f"Collected {collected_count} GCP Cloud Audit Log entries for resources '{resource_names}'.")
        return GCPCloudAuditLogCollection(
            entries=all_log_entries_schemas,
            next_page_token=next_page_token_from_iterator,
            filter_used=final_filter,
            projects_queried=resource_names # Assumindo que resource_names são projetos para este campo
        )

    except DefaultCredentialsError:
        msg = "GCP default credentials not found for Cloud Logging collector."
        logger.error(msg)
        return GCPCloudAuditLogCollection(error_message=msg, projects_queried=resource_names)
    except InvalidArgument as e:
        logger.error(f"Invalid argument for Cloud Logging for '{resource_names}': {e}", exc_info=True)
        return GCPCloudAuditLogCollection(error_message=f"Invalid argument: {str(e)}", projects_queried=resource_names)
    except GoogleAPIError as e:
        logger.error(f"Google API Error collecting Cloud Logs for '{resource_names}': {e}", exc_info=True)
        return GCPCloudAuditLogCollection(error_message=f"Google API Error: {str(e)}", projects_queried=resource_names)
    except Exception as e:
        logger.error(f"Unexpected error collecting Cloud Logs for '{resource_names}': {e}", exc_info=True)
        return GCPCloudAuditLogCollection(error_message=f"Unexpected error: {str(e)}", projects_queried=resource_names)

if __name__ == "__main__":
    print("Coletor GCP Cloud Audit Logs refinado. Adapte com chamadas reais ao SDK e documentação.")

```
