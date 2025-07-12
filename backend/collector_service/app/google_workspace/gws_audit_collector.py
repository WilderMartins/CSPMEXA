import logging
from typing import List, Optional, Dict, Any
import datetime
import uuid # Para fallback de ID

from app.google_workspace.google_workspace_client_manager import get_gws_service_client
from app.schemas.google_workspace.gws_audit_log_schemas import (
    GWSAuditLogItem,
    GWSAuditLogCollection,
    GWSAuditLogActor, # Renomeado para Input no schema do policy engine, mas aqui é output do collector
    GWSAuditLogEvent,
    GWSAuditLogEventParameter
)
from app.core.config import settings

logger = logging.getLogger(__name__)

def _parse_gws_timestamp(timestamp_str: Optional[str]) -> Optional[datetime.datetime]:
    if not timestamp_str:
        return None
    try:
        # Formato comum: "2023-10-27T10:00:00.123Z"
        if timestamp_str.endswith("Z"):
            timestamp_str = timestamp_str[:-1] + "+00:00"
        return datetime.datetime.fromisoformat(timestamp_str)
    except ValueError:
        logger.warning(f"Could not parse GWS timestamp string '{timestamp_str}'")
        return None

def _convert_sdk_activity_to_schema(sdk_activity_dict: Dict[str, Any]) -> Optional[GWSAuditLogItem]:
    if not sdk_activity_dict:
        return None

    try:
        sdk_id_part = sdk_activity_dict.get("id", {})
        sdk_actor_part = sdk_activity_dict.get("actor", {})
        sdk_events_part = sdk_activity_dict.get("events", [])

        actor_schema = None
        if sdk_actor_part:
            actor_schema = GWSAuditLogActor( # Usando o schema do collector
                callerType=sdk_actor_part.get("callerType"),
                email=sdk_actor_part.get("email"),
                profileId=sdk_actor_part.get("profileId"),
                key=sdk_actor_part.get("key")
            )

        events_schemas = []
        for sdk_event in sdk_events_part:
            params_schemas = []
            for sdk_param in sdk_event.get("parameters", []):
                params_schemas.append(GWSAuditLogEventParameter( # Usando o schema do collector
                    name=sdk_param.get("name"),
                    value=sdk_param.get("value"),
                    multiValue=sdk_param.get("multiValue"),
                    messageValue=sdk_param.get("messageValue"),
                ))
            events_schemas.append(GWSAuditLogEvent( # Usando o schema do collector
                type=sdk_event.get("type"),
                name=sdk_event.get("name"),
                parameters=params_schemas
            ))

        id_time_parsed = _parse_gws_timestamp(sdk_id_part.get("time"))
        if not id_time_parsed: # Se o timestamp do ID for crucial e não puder ser parseado, pode ser um problema
            logger.error(f"Failed to parse mandatory id.time for GWS audit event: {sdk_id_part.get('time')}")
            # Retornar um item de erro ou pular este item
            return GWSAuditLogItem(
                id_time=datetime.datetime.now(datetime.timezone.utc), # Fallback
                id_applicationName=sdk_id_part.get("applicationName", "UNKNOWN_APP_ON_ERROR"),
                collection_error_details=f"Invalid or missing id.time: {sdk_id_part.get('time')}"
            )

        return GWSAuditLogItem( # Usando o schema do collector
            kind=sdk_activity_dict.get("kind"),
            id_time=id_time_parsed,
            id_uniqueQualifier=sdk_id_part.get("uniqueQualifier"),
            id_applicationName=sdk_id_part.get("applicationName", "UnknownApp"), # Default se ausente
            id_customerId=sdk_id_part.get("customerId"),
            actor=actor_schema,
            ipAddress=sdk_activity_dict.get("ipAddress"),
            events=events_schemas
        )
    except Exception as e:
        logger.error(f"Error converting GWS Activity dict to schema: {e}", exc_info=True)
        return GWSAuditLogItem(
            id_time=datetime.datetime.now(datetime.timezone.utc),
            id_applicationName=sdk_activity_dict.get("id", {}).get("applicationName", "CONVERSION_ERROR_APP"),
            collection_error_details=f"Failed to parse GWS Activity dict: {str(e)}"
        )


def get_gws_audit_logs( # Removido async def, pois a chamada SDK é síncrona
    application_name: str,
    customer_id: Optional[str] = None,
    delegated_admin_email: Optional[str] = None,
    max_results_per_call: int = 1000,
    max_total_results: int = 10000,
    start_time: Optional[datetime.datetime] = None,
    end_time: Optional[datetime.datetime] = None
) -> GWSAuditLogCollection:
    final_customer_id = customer_id or settings.GOOGLE_WORKSPACE_CUSTOMER_ID or "my_customer"
    final_delegated_admin_email = delegated_admin_email or settings.GOOGLE_WORKSPACE_DELEGATED_ADMIN_EMAIL

    if not final_delegated_admin_email:
        msg = "Google Workspace Delegated Admin Email not configured. Cannot fetch audit logs."
        logger.error(msg)
        return GWSAuditLogCollection(error_message=msg, application_name_queried=application_name)

    try:
        service = get_gws_service_client( # Removido await
            service_name='reports',
            version='v1',
            delegated_admin_email=final_delegated_admin_email
        )
    except Exception as e:
        msg = f"Failed to get Google Workspace service client for Reports API: {e}"
        logger.error(msg, exc_info=True)
        return GWSAuditLogCollection(error_message=msg, application_name_queried=application_name)

    all_log_items_schemas: List[GWSAuditLogItem] = []
    page_token: Optional[str] = None
    collected_count = 0

    if end_time is None:
        end_time = datetime.datetime.now(datetime.timezone.utc)
    if start_time is None:
        start_time = end_time - datetime.timedelta(days=1)

    start_time_str = start_time.isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    end_time_str = end_time.isoformat(timespec='milliseconds').replace('+00:00', 'Z')

    try:
        while collected_count < max_total_results:
            current_limit = min(max_results_per_call, max_total_results - collected_count)
            if current_limit <= 0: break

            logger.info(
                f"Fetching GWS Audit Logs for app '{application_name}', user 'all', customer '{final_customer_id}', "
                f"start: {start_time_str}, end: {end_time_str}, page_token: {'yes' if page_token else 'no'}, limit: {current_limit}"
            )

            request_obj = service.activities().list(
                userKey='all',
                applicationName=application_name,
                customerId=final_customer_id,
                startTime=start_time_str,
                endTime=end_time_str,
                maxResults=current_limit,
                pageToken=page_token
            )
            result = request_obj.execute()

            sdk_items = result.get('items', [])
            if sdk_items:
                for sdk_item_dict in sdk_items:
                    schema_item = _convert_sdk_activity_to_schema(sdk_item_dict)
                    if schema_item:
                        all_log_items_schemas.append(schema_item)
                collected_count += len(sdk_items)

            page_token = result.get('nextPageToken')
            if not page_token or collected_count >= max_total_results:
                break

        logger.info(f"Collected {collected_count} GWS Audit Log items for app '{application_name}'.")
        return GWSAuditLogCollection(
            kind=result.get("kind"),
            items=all_log_items_schemas,
            next_page_token=page_token,
            application_name_queried=application_name,
            start_time_queried=start_time,
            end_time_queried=end_time
        )

    except Exception as e:
        logger.error(f"Error collecting GWS Audit Logs for app '{application_name}': {e}", exc_info=True)
        return GWSAuditLogCollection(
            error_message=f"Failed to collect GWS Audit Logs: {str(e)}",
            application_name_queried=application_name,
            start_time_queried=start_time,
            end_time_queried=end_time
        )

if __name__ == "__main__":
    # Teste local já estava comentado
    print("Coletor GWS Audit Logs refinado. Adapte com chamadas reais ao SDK.")
```
