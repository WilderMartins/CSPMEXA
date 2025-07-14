from typing import List, Dict, Any, Optional
from ..schemas.gcp.gcp_scc_input_schemas import GCPSCCFindingCollectionInput, GCPFindingInput
from ..schemas.alert_schema import AlertSeverityEnum # Para mapear severidades do SCC

# Mapeamento de severidade do GCP SCC para AlertSeverityEnum
# GCP SCC: CRITICAL, HIGH, MEDIUM, LOW, SEVERITY_UNSPECIFIED
# AlertSeverityEnum: CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL
SCC_SEVERITY_MAP = {
    "CRITICAL": AlertSeverityEnum.CRITICAL,
    "HIGH": AlertSeverityEnum.HIGH,
    "MEDIUM": AlertSeverityEnum.MEDIUM,
    "LOW": AlertSeverityEnum.LOW,
    "SEVERITY_UNSPECIFIED": AlertSeverityEnum.INFORMATIONAL, # Ou Low, dependendo da preferência
}

def process_gcp_scc_findings(
    scc_finding_collection: Optional[GCPSCCFindingCollectionInput],
    # account_id (project_id ou org_id) já está no finding.project_id ou finding.organization_id
    # Se o parent_resource da coleção for um projeto, esse é o account_id principal.
    # Se for organização, cada finding terá seu project_id.
    # O 'account_id' passado para esta função pelo core_engine será o 'parent_resource' da consulta.
    # Isso pode ser usado para dar contexto se um finding não tiver project_id explícito.
    gcp_parent_resource_id: Optional[str]
) -> List[Dict[str, Any]]:
    """
    Processa os findings do GCP Security Command Center e os transforma em dados para AlertCreate.
    Os findings do SCC já são "alertas", então esta função principalmente mapeia os campos.
    """
    alerts_data: List[Dict[str, Any]] = []

    if not scc_finding_collection or not scc_finding_collection.findings:
        if scc_finding_collection and scc_finding_collection.error_message:
            # Erro global na coleta de findings
            alerts_data.append({
                "resource_id": gcp_parent_resource_id or "GCPResource",
                "resource_type": "GCP::SCC::FindingCollection",
                "provider": "gcp",
                "severity": AlertSeverityEnum.MEDIUM,
                "title": "GCP SCC Finding Collection Failed",
                "description": f"Failed to collect Security Command Center findings for parent '{gcp_parent_resource_id}': {scc_finding_collection.error_message}",
                "policy_id": "GCP_SCC_GlobalCollection_Error",
                "account_id": gcp_parent_resource_id, # O pai da consulta (org, folder, project)
                "details": {"parent_resource": gcp_parent_resource_id, "filter_used": scc_finding_collection.filter_used, "error": scc_finding_collection.error_message}
            })
        return alerts_data

    for finding in scc_finding_collection.findings:
        if finding.collection_error_details:
            alerts_data.append({
                "resource_id": finding.name, # O nome completo do finding como ID
                "resource_type": "GCP::SCC::Finding",
                "provider": "gcp",
                "severity": AlertSeverityEnum.INFORMATIONAL,
                "title": "GCP SCC Finding Parsing Issue",
                "description": f"Could not fully parse SCC finding '{finding.name}' for parent '{gcp_parent_resource_id}': {finding.collection_error_details}",
                "policy_id": "GCP_SCC_FindingParsing_Error",
                "account_id": finding.project_id or finding.organization_id or gcp_parent_resource_id,
                "details": {"finding_name": finding.name, "error": finding.collection_error_details}
            })
            continue

        # Mapear severidade do SCC para a nossa enumeração interna
        mapped_severity = SCC_SEVERITY_MAP.get(finding.severity, AlertSeverityEnum.INFORMATIONAL)

        # Usar a categoria do SCC como parte do título ou policy_id
        # O `canonical_name` ou `category` do finding são bons candidatos para o título/policy_id.
        # Policy ID pode ser algo como "SCC_{finding.category}" ou "SCC_{finding.canonical_name}"
        scc_policy_id = f"SCC_{finding.category.replace(' ', '_').upper()}" if finding.category else "SCC_UNCATEGORIZED"
        if finding.canonical_name: # Se canonical_name existir, pode ser mais específico
            scc_policy_id = f"SCC_{finding.canonical_name.split('.')[-1]}" # Pega a última parte do canonical_name

        finding_title = finding.canonical_name or finding.category or "GCP Security Finding"
        if ":" in finding_title : finding_title = finding_title.split(":")[-1].replace("_", " ")


        # O `resource_name` do finding já é o recurso afetado.
        # O `account_id` para o alerta deve ser o `project_id` do recurso, se disponível,
        # ou o `organization_id` se for um finding a nível de organização.
        alert_account_id = finding.project_id or finding.organization_id or gcp_parent_resource_id

        # Extrair uma descrição mais amigável se possível, ou usar a do finding.
        # A descrição pode estar em source_properties. Por exemplo, para Security Health Analytics:
        # source_properties["Properties"]["Explanation"]
        description = finding.description
        if not description and finding.source_properties and finding.source_properties.additional_properties:
            # Tentar heurísticas comuns para descrições de fontes conhecidas
            if "Explanation" in finding.source_properties.additional_properties: # Security Health Analytics
                description = finding.source_properties.additional_properties["Explanation"]
            elif "description" in finding.source_properties.additional_properties: # Event Threat Detection
                description = finding.source_properties.additional_properties["description"]

        if not description: # Fallback
            description = f"Security finding '{finding_title}' reported by GCP Security Command Center for resource '{finding.resource_name}'. State: {finding.state}."


        alerts_data.append({
            "resource_id": finding.resource_name,
            "resource_type": "GCP::" + (finding.source_properties.additional_properties.get("ResourceType", "UnknownResource") if finding.source_properties and finding.source_properties.additional_properties else "UnknownResource"), # Tentar obter tipo de recurso de source_properties
            "provider": "gcp",
            "severity": mapped_severity,
            "title": f"GCP SCC: {finding_title}",
            "description": description,
            "policy_id": scc_policy_id, # Usar a categoria/canonical_name como ID da "política"
            "account_id": alert_account_id,
            # "region": extrair de resource_name se possível, SCC findings são geralmente regionais ou globais
            "details": {
                "scc_finding_name": finding.name,
                "scc_finding_category": finding.category,
                "scc_finding_state": finding.state,
                "scc_event_time": finding.event_time.isoformat() if finding.event_time else None,
                "scc_external_uri": finding.external_uri,
                "scc_source_properties": finding.source_properties.additional_properties if finding.source_properties else None,
                "scc_canonical_name": finding.canonical_name,
                "scc_update_time": finding.update_time.isoformat() if finding.update_time else None,
            },
            "recommendation": f"Review the finding details in GCP Security Command Center: {finding.external_uri if finding.external_uri else 'N/A'}. Follow remediation steps provided by the specific security source."
        })

    return alerts_data
