import logging
from typing import List, Optional, Dict, Any
import datetime
import re # Para extrair project_id

from google.cloud import securitycenter_v1
from google.auth.exceptions import DefaultCredentialsError
from google.api_core.exceptions import GoogleAPIError

from app.schemas.gcp.gcp_scc_schemas import GCPFinding, GCPSCCFindingCollection, GCPFindingSourceProperties
from app.gcp.gcp_utils import get_gcp_project_id # Para obter o projeto padrão se necessário

logger = logging.getLogger(__name__)

# Helper para converter o objeto Finding do SDK para o nosso schema Pydantic GCPFinding
def _convert_sdk_finding_to_schema(sdk_finding: securitycenter_v1.types.Finding) -> Optional[GCPFinding]:
    if not sdk_finding:
        return None

    try:
        # Extrair IDs do nome e pai
        org_id, source_id_from_name, finding_id_str = None, None, None
        if sdk_finding.name:
            name_parts = sdk_finding.name.split('/')
            if len(name_parts) == 6 and name_parts[0] == "organizations" and name_parts[2] == "sources" and name_parts[4] == "findings":
                org_id = name_parts[1]
                source_id_from_name = name_parts[3]
                finding_id_str = name_parts[5]
            elif len(name_parts) == 6 and name_parts[0] == "projects" and name_parts[2] == "sources" and name_parts[4] == "findings":
                # Não é o formato esperado para 'name', mas sim para 'parent' de um finding específico
                pass # project_id será extraído de resource_name
            elif len(name_parts) == 4 and name_parts[0] == "folders": # folders/{folder_id}/sources/{source_id}/findings/{finding_id}
                 # Similar, org_id não está aqui
                source_id_from_name = name_parts[3]
                finding_id_str = name_parts[5]


        source_id_from_parent = None
        if sdk_finding.parent:
            parent_parts = sdk_finding.parent.split('/')
            if len(parent_parts) == 4 and parent_parts[2] == "sources":
                source_id_from_parent = parent_parts[3]

        source_id_final = source_id_from_name or source_id_from_parent

        # Extrair project_id do resource_name (ex: "//cloudresourcemanager.googleapis.com/projects/12345")
        project_id_match = re.search(r"//cloudresourcemanager\.googleapis\.com/projects/([^/]+)", sdk_finding.resource_name)
        project_id_extracted = project_id_match.group(1) if project_id_match else None
        if not project_id_extracted: # Tentar outro formato comum
            project_id_match_alt = re.search(r"projects/([^/]+)", sdk_finding.resource_name)
            project_id_extracted = project_id_match_alt.group(1) if project_id_match_alt else None


        # Severity é um Enum no SDK, converter para string
        severity_str = securitycenter_v1.types.Finding.Severity(sdk_finding.severity).name

        # source_properties é um Struct no SDK, converter para dict
        source_props_dict = None
        if sdk_finding.source_properties:
            source_props_dict = dict(sdk_finding.source_properties.items())

        source_properties_schema = None
        if source_props_dict:
            source_properties_schema = GCPFindingSourceProperties(additional_properties=source_props_dict)


        return GCPFinding(
            name=sdk_finding.name,
            parent=sdk_finding.parent,
            resourceName=sdk_finding.resource_name,
            state=securitycenter_v1.types.Finding.State(sdk_finding.state).name,
            category=sdk_finding.category,
            externalUri=sdk_finding.external_uri,
            sourceProperties=source_properties_schema,
            eventTime=sdk_finding.event_time.ToDatetime(tzinfo=datetime.timezone.utc) if hasattr(sdk_finding.event_time, 'ToDatetime') else None,
            createTime=sdk_finding.create_time.ToDatetime(tzinfo=datetime.timezone.utc) if hasattr(sdk_finding.create_time, 'ToDatetime') else None,
            updateTime=sdk_finding.update_time.ToDatetime(tzinfo=datetime.timezone.utc) if sdk_finding.update_time and hasattr(sdk_finding.update_time, 'ToDatetime') else None,
            severity=severity_str,
            canonicalName=sdk_finding.canonical_name,
            description=getattr(sdk_finding, 'description', None),
            # Adicionar outros campos como vulnerability, misconfiguration se necessário
            project_id=project_id_extracted,
            organization_id=org_id,
            source_id=source_id_final,
            finding_id=finding_id_str
        )
    except Exception as e:
        logger.error(f"Error converting SDK SCC Finding object to schema: {e}", exc_info=True)
        return GCPFinding(
            name=getattr(sdk_finding, 'name', 'CONVERSION_ERROR_NAME'),
            parent=getattr(sdk_finding, 'parent', 'CONVERSION_ERROR_PARENT'),
            resourceName=getattr(sdk_finding, 'resource_name', 'CONVERSION_ERROR_RESOURCE'),
            state="STATE_UNSPECIFIED",
            category="CATEGORY_UNSPECIFIED",
            eventTime=datetime.datetime.now(datetime.timezone.utc), # Placeholder
            createTime=datetime.datetime.now(datetime.timezone.utc), # Placeholder
            severity="SEVERITY_UNSPECIFIED",
            collection_error_details=f"Failed to parse SDK SCC Finding object: {str(e)}"
        )

async def get_gcp_scc_findings(
    parent_resource: str, # Ex: "organizations/{org_id}/sources/-" ou "projects/{project_id}/sources/-"
                          # Ou "organizations/{org_id}" para então listar fontes e depois findings.
                          # Para este coletor, vamos assumir que o parent já inclui /sources/-
    scc_filter: Optional[str] = None, # Filtro da API SCC (ex: 'state="ACTIVE" AND severity="HIGH"')
    max_results_per_call: int = 1000,
    max_total_results: int = 10000,
) -> GCPSCCFindingCollection:
    """
    Coleta findings do GCP Security Command Center para um recurso pai específico.
    Requer permissão: securitycenter.findings.list
    """
    all_findings_schemas: List[GCPFinding] = []
    page_token: Optional[str] = None
    collected_count = 0

    try:
        credentials, default_project_id = google.auth.default() # Tenta obter credenciais do ambiente
        scc_client = securitycenter_v1.SecurityCenterClient(credentials=credentials)

        # O 'parent' para list_findings deve ser no formato organizations/ORG_ID/sources/SOURCE_ID
        # ou projects/PROJECT_ID/sources/SOURCE_ID. Usar '-' para SOURCE_ID pega de todas as fontes.
        # Ex: parent_resource = "organizations/1234567890/sources/-"

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

            # A chamada ao SDK é síncrona. Será envolvida em run_in_threadpool no controller.
            response_pager = scc_client.list_findings(request=request) # Retorna um Pager

            # O código abaixo processa a resposta do Pager.
            # É crucial que a estrutura de `item_result.finding` e `response_pager.next_page_token`
            # corresponda ao que o SDK `google-cloud-securitycenter` retorna.

            for item_result in response_pager.list_findings_results: # Iterar sobre os resultados na página atual
                sdk_finding_obj = item_result.finding # Cada item_result contém um 'finding'
                schema_finding = _convert_sdk_finding_to_schema(sdk_finding_obj)
                if schema_finding:
                    all_findings_schemas.append(schema_finding)

            collected_count += len(response_pager.list_findings_results)
            page_token = response_pager.next_page_token

            if not page_token or collected_count >= max_total_results:
                break

        logger.info(f"Collected {collected_count} SCC findings for parent '{parent_resource}'.")
        return GCPSCCFindingCollection(
            findings=all_findings_schemas,
            next_page_token=page_token,
            total_size=response_pager.total_size if hasattr(response_pager, 'total_size') else collected_count, # total_size pode não ser sempre retornado
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
    # Teste local (requer credenciais GCP e SCC API habilitada)
    # import asyncio
    # async def run_scc_test():
    #     # Configurar GOOGLE_APPLICATION_CREDENTIALS no seu ambiente
    #     # Exemplo de parent_resource: "organizations/YOUR_ORG_ID/sources/-"
    #     # Ou "projects/YOUR_PROJECT_ID/sources/-"
    #     test_parent = "organizations/YOUR_ORG_ID/sources/-" # Substituir pelo seu

    #     if "YOUR_ORG_ID" in test_parent:
    #         print(f"Pulando teste local do coletor SCC: substitua YOUR_ORG_ID em test_parent.")
    #         return

    #     print(f"Testando coletor SCC para parent {test_parent}...")
    #     scc_collection = await get_gcp_scc_findings(
    #         parent_resource=test_parent,
    #         scc_filter='state="ACTIVE" AND severity="HIGH"', # Exemplo de filtro
    #         max_total_results=5
    #     )

    #     if scc_collection.error_message:
    #         print(f"Erro na coleta: {scc_collection.error_message}")
    #     else:
    #         print(f"Coletados {len(scc_collection.findings)} findings (total size from API: {scc_collection.total_size}).")
    #         for finding in scc_collection.findings:
    #             print(f"  Finding: {finding.name}, Category: {finding.category}, Severity: {finding.severity}")
    #             # print(finding.model_dump_json(indent=2))
    #         if scc_collection.next_page_token:
    #             print(f"  Próximo token de página: {scc_collection.next_page_token}")

    # asyncio.run(run_scc_test())
    print("Coletor GCP SCC (estrutura com mock) criado. Adapte com chamadas reais ao SDK.")

```
