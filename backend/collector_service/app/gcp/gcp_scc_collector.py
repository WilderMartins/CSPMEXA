import logging
from typing import List, Optional, Dict, Any
import datetime
import re # Para extrair project_id
import uuid # Para fallback de ID

from google.cloud import securitycenter_v1
from google.auth.exceptions import DefaultCredentialsError
from google.api_core.exceptions import GoogleAPIError
# from google.protobuf.struct_pb2 import Struct # Para type hinting, se necessário

from app.schemas.gcp.gcp_scc_schemas import GCPFinding, GCPSCCFindingCollection, GCPFindingSourceProperties
from app.gcp.gcp_utils import get_gcp_project_id

logger = logging.getLogger(__name__)

def _convert_protobuf_timestamp_to_datetime(pb_timestamp: Any) -> Optional[datetime.datetime]:
    """Converte um google.protobuf.Timestamp para datetime.datetime ou retorna None."""
    if pb_timestamp and hasattr(pb_timestamp, "ToDatetime") and callable(pb_timestamp.ToDatetime):
        try:
            # ToDatetime() pode retornar um datetime naive, garantir que seja timezone-aware (UTC)
            dt = pb_timestamp.ToDatetime()
            if dt.tzinfo is None:
                return dt.replace(tzinfo=datetime.timezone.utc)
            return dt
        except Exception as e:
            logger.warning(f"Could not convert protobuf timestamp to datetime: {e}")
    elif isinstance(pb_timestamp, str): # Se já for uma string ISO
        try:
            dt_str = pb_timestamp
            if dt_str.endswith("Z"):
                 dt_str = dt_str[:-1] + "+00:00"
            return datetime.datetime.fromisoformat(dt_str)
        except ValueError:
            logger.warning(f"Could not parse ISO timestamp string from SCC: {pb_timestamp}")
    return None

def _convert_sdk_finding_to_schema(sdk_finding: securitycenter_v1.types.Finding) -> Optional[GCPFinding]:
    if not sdk_finding:
        return None

    try:
        org_id, source_id_from_name, finding_id_str = None, None, None
        if sdk_finding.name:
            parts = sdk_finding.name.split('/')
            if len(parts) == 6 and parts[0] in ["organizations", "folders", "projects"] and parts[2] == "sources" and parts[4] == "findings":
                if parts[0] == "organizations": org_id = parts[1]
                # folder_id pode ser parts[1] se parts[0] == "folders"
                # project_id pode ser parts[1] se parts[0] == "projects" (menos comum para 'name' de finding global)
                source_id_from_name = parts[3]
                finding_id_str = parts[5]

        source_id_from_parent = None
        if sdk_finding.parent: # Formato: organizations/{org}/sources/{source} ou projects/... ou folders/...
            parent_parts = sdk_finding.parent.split('/')
            if len(parent_parts) == 4 and parent_parts[2] == "sources":
                source_id_from_parent = parent_parts[3]

        source_id_final = source_id_from_name or source_id_from_parent

        project_id_extracted = None
        if sdk_finding.resource_name:
            match = re.search(r"projects/([^/]+)", sdk_finding.resource_name)
            if match:
                project_id_extracted = match.group(1)

        # Se org_id não foi pego do 'name' (ex: finding de projeto), tentar pegar do 'parent'
        if not org_id and sdk_finding.parent and sdk_finding.parent.startswith("organizations/"):
            org_id = sdk_finding.parent.split('/')[1]


        severity_str = securitycenter_v1.types.Finding.Severity(sdk_finding.severity).name \
            if sdk_finding.severity else "SEVERITY_UNSPECIFIED"
        state_str = securitycenter_v1.types.Finding.State(sdk_finding.state).name \
            if sdk_finding.state else "STATE_UNSPECIFIED"

        source_props_dict = {}
        if sdk_finding.source_properties:
            # O objeto Struct do Protobuf pode ser convertido para dict
            # usando dict() ou iterando sobre seus campos.
            try:
                # Tentar converter diretamente para dict. Isso funciona se for um Mapping.
                source_props_dict = dict(sdk_finding.source_properties)
            except TypeError: # Se não for um Mapping direto, iterar
                for key, value in sdk_finding.source_properties.items():
                     # O valor pode ser outro Struct, um ListValue, ou um valor simples.
                     # Para simplificar, vamos apenas pegar a representação string por enquanto,
                     # ou tentar uma conversão mais profunda se o valor for um Struct/ListValue.
                     # Esta parte pode precisar de mais refinamento dependendo da complexidade dos dados.
                    source_props_dict[key] = str(value) # Simplificação
            except Exception as e_sp:
                logger.warning(f"Could not fully parse source_properties for finding {sdk_finding.name}: {e_sp}")
                source_props_dict = {"error_parsing_source_properties": str(e_sp)}

        source_properties_schema = GCPFindingSourceProperties(additional_properties=source_props_dict) \
            if source_props_dict else None

        event_time_dt = _convert_protobuf_timestamp_to_datetime(sdk_finding.event_time)
        create_time_dt = _convert_protobuf_timestamp_to_datetime(sdk_finding.create_time)
        update_time_dt = _convert_protobuf_timestamp_to_datetime(sdk_finding.update_time)

        return GCPFinding(
            name=sdk_finding.name or f"scc_finding_{uuid.uuid4()}", # Obrigatório
            parent=sdk_finding.parent or "UnknownParent", # Obrigatório
            resourceName=sdk_finding.resource_name or "UnknownResource", # Obrigatório
            state=state_str,
            category=sdk_finding.category or "UNCATEGORIZED", # Obrigatório
            externalUri=sdk_finding.external_uri,
            sourceProperties=source_properties_schema,
            eventTime=event_time_dt or datetime.datetime.now(datetime.timezone.utc), # Obrigatório
            createTime=create_time_dt or datetime.datetime.now(datetime.timezone.utc), # Obrigatório
            updateTime=update_time_dt,
            severity=severity_str,
            canonicalName=sdk_finding.canonical_name,
            description=getattr(sdk_finding, 'description', None),
            project_id=project_id_extracted,
            organization_id=org_id,
            source_id=source_id_final,
            finding_id=finding_id_str
        )
    except Exception as e:
        logger.error(f"Critical error converting SDK SCC Finding object to schema: {e}", exc_info=True)
        return GCPFinding(
            name=getattr(sdk_finding, 'name', f'CONVERSION_ERROR_NAME_{uuid.uuid4()}'),
            parent=getattr(sdk_finding, 'parent', 'CONVERSION_ERROR_PARENT'),
            resourceName=getattr(sdk_finding, 'resource_name', 'CONVERSION_ERROR_RESOURCE'),
            state="STATE_UNSPECIFIED",
            category="CONVERSION_ERROR_CATEGORY",
            eventTime=datetime.datetime.now(datetime.timezone.utc),
            createTime=datetime.datetime.now(datetime.timezone.utc),
            severity="SEVERITY_UNSPECIFIED",
            collection_error_details=f"Failed to parse SDK SCC Finding object: {str(e)}"
        )

def get_gcp_scc_findings( # Removido async def
    parent_resource: str,
    scc_filter: Optional[str] = None,
    max_results_per_call: int = 1000,
    max_total_results: int = 10000,
) -> GCPSCCFindingCollection:
    all_findings_schemas: List[GCPFinding] = []
    page_token: Optional[str] = None
    collected_count = 0

    try:
        credentials, _ = google.auth.default()
        scc_client = securitycenter_v1.SecurityCenterClient(credentials=credentials)

        logger.info(f"Fetching GCP SCC findings for parent: {parent_resource}, filter: '{scc_filter or 'None'}'")

        while collected_count < max_total_results:
            current_limit = min(max_results_per_call, max_total_results - collected_count)
            if current_limit <= 0: break

            request = securitycenter_v1.types.ListFindingsRequest(
                parent=parent_resource,
                filter=scc_filter,
                page_size=current_limit,
                page_token=page_token
            )

            # Chamada síncrona ao SDK. O controller usará run_in_threadpool.
            response_pager = scc_client.list_findings(request=request)

            for item_result in response_pager.list_findings_results:
                sdk_finding_obj = item_result.finding
                schema_finding = _convert_sdk_finding_to_schema(sdk_finding_obj)
                if schema_finding:
                    all_findings_schemas.append(schema_finding)

            collected_count += len(response_pager.list_findings_results)
            page_token = response_pager.next_page_token

            if not page_token or collected_count >= max_total_results:
                break

        total_size_from_response = response_pager.total_size if hasattr(response_pager, 'total_size') and response_pager.total_size is not None else collected_count
        logger.info(f"Collected {collected_count} SCC findings (API total: {total_size_from_response}) for parent '{parent_resource}'.")
        return GCPSCCFindingCollection(
            findings=all_findings_schemas,
            next_page_token=page_token,
            total_size=total_size_from_response,
            parent_resource_queried=parent_resource,
            filter_used=scc_filter
        )

    except DefaultCredentialsError:
        msg = "GCP default credentials not found for SCC collector. Ensure GOOGLE_APPLICATION_CREDENTIALS is set or running in a GCP environment with appropriate permissions."
        logger.error(msg)
        return GCPSCCFindingCollection(error_message=msg, parent_resource_queried=parent_resource)
    except GoogleAPIError as e:
        logger.error(f"Google API Error collecting SCC findings for '{parent_resource}': {e}", exc_info=True)
        return GCPSCCFindingCollection(error_message=f"Google API Error: {str(e)}", parent_resource_queried=parent_resource)
    except Exception as e:
        logger.error(f"Unexpected error collecting SCC findings for '{parent_resource}': {e}", exc_info=True)
        return GCPSCCFindingCollection(error_message=f"Unexpected error: {str(e)}", parent_resource_queried=parent_resource)

if __name__ == "__main__":
    # Teste local já estava comentado
    print("Coletor GCP SCC refinado. Adapte com chamadas reais ao SDK e documentação.")
