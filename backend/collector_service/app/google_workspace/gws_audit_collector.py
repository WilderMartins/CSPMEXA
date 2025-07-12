import logging
from typing import List, Optional, Dict, Any
import datetime

from app.google_workspace.google_workspace_client_manager import get_gws_service_client
from app.schemas.google_workspace.gws_audit_log_schemas import (
    GWSAuditLogItem,
    GWSAuditLogCollection,
    GWSAuditLogActor,
    GWSAuditLogEvent,
    GWSAuditLogEventParameter
)
from app.core.config import settings # Para GOOGLE_WORKSPACE_CUSTOMER_ID, GOOGLE_WORKSPACE_DELEGATED_ADMIN_EMAIL

logger = logging.getLogger(__name__)

# Helper para converter o item de atividade do SDK para o nosso schema Pydantic
# Isso dependerá da estrutura exata do objeto retornado pelo SDK (google-api-python-client).
def _convert_sdk_activity_to_schema(sdk_activity: Dict[str, Any]) -> Optional[GWSAuditLogItem]:
    if not sdk_activity:
        return None

    try:
        # Mapeamento de campos do objeto Activity do SDK para GWSAuditLogItem
        # Exemplo de estrutura do Activity:
        # {
        #   "kind": "admin#reports#activity",
        #   "id": {
        #     "time": "2023-10-27T10:00:00.000Z",
        #     "uniqueQualifier": "12345",
        #     "applicationName": "login",
        #     "customerId": "C0xxxxxxx"
        #   },
        #   "actor": {
        #     "email": "user@example.com",
        #     "profileId": "111...",
        #     "callerType": "USER"
        #   },
        #   "ipAddress": "1.2.3.4",
        #   "events": [
        #     {
        #       "type": "login",
        #       "name": "login_success",
        #       "parameters": [
        #         {"name": "login_type", "value": "google_password"},
        #         {"name": "saml_idp_name", "multiValue": ["idp1", "idp2"]},
        #         {"name": "details", "messageValue": {"field1": "val1"}}
        #       ]
        #     }
        #   ]
        # }

        sdk_id_part = sdk_activity.get("id", {})
        sdk_actor_part = sdk_activity.get("actor", {})
        sdk_events_part = sdk_activity.get("events", [])

        actor_schema = None
        if sdk_actor_part:
            actor_schema = GWSAuditLogActor(
                callerType=sdk_actor_part.get("callerType"),
                email=sdk_actor_part.get("email"),
                profileId=sdk_actor_part.get("profileId"),
                key=sdk_actor_part.get("key")
            )

        events_schemas = []
        for sdk_event in sdk_events_part:
            params_schemas = []
            for sdk_param in sdk_event.get("parameters", []):
                params_schemas.append(GWSAuditLogEventParameter(
                    name=sdk_param.get("name"),
                    value=sdk_param.get("value"),
                    multiValue=sdk_param.get("multiValue"),
                    messageValue=sdk_param.get("messageValue"),
                    # boolValue=sdk_param.get("boolValue") # Adicionar se presente
                ))
            events_schemas.append(GWSAuditLogEvent(
                type=sdk_event.get("type"),
                name=sdk_event.get("name"),
                parameters=params_schemas
            ))

        return GWSAuditLogItem(
            kind=sdk_activity.get("kind"),
            id_time=sdk_id_part.get("time"), # Pydantic tentará converter string ISO para datetime
            id_uniqueQualifier=sdk_id_part.get("uniqueQualifier"),
            id_applicationName=sdk_id_part.get("applicationName"),
            id_customerId=sdk_id_part.get("customerId"),
            actor=actor_schema,
            ipAddress=sdk_activity.get("ipAddress"),
            events=events_schemas
        )
    except Exception as e:
        logger.error(f"Error converting SDK GWS Activity object to schema: {e}", exc_info=True)
        # Retornar um objeto de erro parcial se a conversão falhar
        return GWSAuditLogItem(
            id_time=datetime.datetime.now(datetime.timezone.utc), # Placeholder
            id_applicationName=sdk_activity.get("id", {}).get("applicationName", "CONVERSION_ERROR_APP"),
            collection_error_details=f"Failed to parse SDK GWS Activity object: {str(e)}"
        )


async def get_gws_audit_logs(
    application_name: str, # e.g., "login", "drive", "admin", "token"
    customer_id: Optional[str] = None,
    delegated_admin_email: Optional[str] = None,
    max_results_per_call: int = 1000, # Max permitido pela API é 1000
    max_total_results: int = 10000, # Limite total para evitar buscar logs demais
    start_time: Optional[datetime.datetime] = None, # Período de início (UTC)
    end_time: Optional[datetime.datetime] = None    # Período de fim (UTC)
) -> GWSAuditLogCollection:
    """
    Coleta logs de auditoria do Google Workspace para uma aplicação específica.
    Requer escopo OAuth: https://www.googleapis.com/auth/admin.reports.audit.readonly
    """
    final_customer_id = customer_id or settings.GOOGLE_WORKSPACE_CUSTOMER_ID or "my_customer"
    final_delegated_admin_email = delegated_admin_email or settings.GOOGLE_WORKSPACE_DELEGATED_ADMIN_EMAIL

    if not final_delegated_admin_email:
        msg = "Google Workspace Delegated Admin Email not configured. Cannot fetch audit logs."
        logger.error(msg)
        return GWSAuditLogCollection(error_message=msg, application_name_queried=application_name)

    try:
        # Obter o cliente de serviço para a Reports API
        # O get_gws_service_client deve ser capaz de retornar um cliente para 'reports_v1'
        service = await get_gws_service_client(
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

    # Definir período de tempo padrão se não fornecido (ex: últimas 24 horas)
    if end_time is None:
        end_time = datetime.datetime.now(datetime.timezone.utc)
    if start_time is None:
        start_time = end_time - datetime.timedelta(days=1)

    # Formatar datas para o formato RFC3339 esperado pela API (ex: "2023-10-27T10:00:00.000Z")
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

            # A chamada ao SDK do Google é síncrona. Usar run_in_threadpool no controller.
            # Aqui, vamos simular a chamada síncrona direta para o coletor.
            # request_obj = service.activities().list( # Chamada real ao SDK
            #     userKey='all', # Para todos os usuários
            #     applicationName=application_name,
            #     customerId=final_customer_id, # Pode não ser necessário se já no contexto do admin
            #     startTime=start_time_str,
            #     endTime=end_time_str,
            #     maxResults=current_limit,
            #     pageToken=page_token
            # )
            # A chamada real ao SDK é síncrona. O controller deve usar run_in_threadpool.
            request_obj = service.activities().list(
                userKey='all', # Para todos os usuários
                applicationName=application_name,
                customerId=final_customer_id, # Pode não ser necessário se já no contexto do admin
                startTime=start_time_str,
                endTime=end_time_str,
                maxResults=current_limit,
                pageToken=page_token
            )
            result = request_obj.execute() # Chamada síncrona real ao SDK Google

            # O código abaixo processa a resposta do SDK.
            # É crucial que a estrutura de `result` (especialmente `items` e `nextPageToken`)
            # corresponda ao que o SDK `google-api-python-client` para Reports API retorna.

            sdk_items = result.get('items', [])
            if sdk_items:
                for sdk_item_dict in sdk_items: # O SDK retorna uma lista de dicionários
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
            next_page_token=page_token, # Retorna o último token para possível continuação
            application_name_queried=application_name,
            start_time_queried=start_time,
            end_time_queried=end_time
        )

    except Exception as e:
        # Lidar com erros específicos da API do Google (ex: HttpError)
        # from googleapiclient.errors import HttpError
        # if isinstance(e, HttpError): ...
        logger.error(f"Error collecting GWS Audit Logs for app '{application_name}': {e}", exc_info=True)
        return GWSAuditLogCollection(
            error_message=f"Failed to collect GWS Audit Logs: {str(e)}",
            application_name_queried=application_name,
            start_time_queried=start_time,
            end_time_queried=end_time
        )

if __name__ == "__main__":
    # Teste local
    # import asyncio
    # async def run_gws_audit_test():
    #     # Mock settings ou carregar de .env do collector_service
    #     settings.GOOGLE_WORKSPACE_DELEGATED_ADMIN_EMAIL = "SEU_EMAIL_DELEGADO_AQUI"
    #     settings.GOOGLE_SERVICE_ACCOUNT_KEY_PATH = "CAMINHO_PARA_SUA_CHAVE_SA_JSON_AQUI"

    #     if not settings.GOOGLE_WORKSPACE_DELEGATED_ADMIN_EMAIL or not settings.GOOGLE_SERVICE_ACCOUNT_KEY_PATH:
    #         print("Pulando teste GWS Audit Logs: GOOGLE_WORKSPACE_DELEGATED_ADMIN_EMAIL ou GOOGLE_SERVICE_ACCOUNT_KEY_PATH não configurados.")
    #         return

    #     print("Testando coletor de Audit Logs do Google Workspace (login)...")
    #     log_collection = await get_gws_audit_logs(application_name="login", max_total_results=5)

    #     if log_collection.error_message:
    #         print(f"Erro: {log_collection.error_message}")
    #     else:
    #         print(f"Coletados {len(log_collection.items)} logs de login.")
    #         for item in log_collection.items:
    #             print(f"  Evento: {item.events[0].name if item.events else 'N/A'} por {item.actor.email if item.actor else 'N/A'} em {item.id_time}")
    #         if log_collection.next_page_token:
    #             print(f"  Próximo token de página: {log_collection.next_page_token}")

    # asyncio.run(run_gws_audit_test())
    print("Coletor GWS Audit Logs (estrutura com mock) criado. Adapte com chamadas reais ao SDK.")

```
