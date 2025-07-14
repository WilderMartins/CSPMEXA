from typing import List, Dict, Any, Optional
from ..schemas.gcp.gcp_cai_input_schemas import GCPAssetCollectionInput, GCPAssetInput
from ..schemas.alert_schema import AlertSeverityEnum

# Lista de labels obrigatórias e os tipos de ativos aos quais se aplicam.
# Pode ser expandido e tornado configurável.
REQUIRED_LABELS_BY_ASSET_TYPE: Dict[str, List[str]] = {
    "compute.googleapis.com/Instance": ["owner", "environment", "cost-center"],
    "storage.googleapis.com/Bucket": ["owner", "data-classification", "cost-center"],
    # Adicionar outros tipos de ativos e seus labels obrigatórios
}

def evaluate_gcp_cai_policies(
    asset_collection: Optional[GCPAssetCollectionInput],
    account_id: Optional[str] # project_id, folder_id, ou organization_id do escopo da consulta CAI
) -> List[Dict[str, Any]]:
    """
    Avalia os ativos do GCP Cloud Asset Inventory em relação às políticas definidas.
    """
    alerts_data: List[Dict[str, Any]] = []

    if not asset_collection or not asset_collection.assets:
        if asset_collection and asset_collection.error_message:
            alerts_data.append({
                "resource_id": account_id or "GCPResourceScope", # O escopo da consulta
                "resource_type": "GCP::CloudAssetInventory::Collection",
                "provider": "gcp",
                "severity": AlertSeverityEnum.MEDIUM,
                "title": "GCP Cloud Asset Inventory Collection Failed",
                "description": f"Failed to collect Cloud Asset Inventory for scope '{asset_collection.scope_queried or account_id}': {asset_collection.error_message}",
                "policy_id": "GCP_CAI_GlobalCollection_Error",
                "account_id": account_id, # O escopo principal da consulta
                "details": {
                    "scope_queried": asset_collection.scope_queried,
                    "asset_types_queried": asset_collection.asset_types_queried,
                    "content_type_queried": asset_collection.content_type_queried,
                    "error": asset_collection.error_message
                }
            })
        return alerts_data

    for asset in asset_collection.assets:
        if asset.collection_error_details:
            alerts_data.append({
                "resource_id": asset.name,
                "resource_type": asset.asset_type or "GCP::Asset",
                "provider": "gcp",
                "severity": AlertSeverityEnum.INFORMATIONAL,
                "title": "GCP Asset Data Parsing Issue",
                "description": f"Could not fully parse asset '{asset.name}': {asset.collection_error_details}",
                "policy_id": "GCP_CAI_AssetParsing_Error",
                "account_id": asset.project_id or account_id,
                "details": {"asset_name": asset.name, "asset_type": asset.asset_type, "error": asset.collection_error_details}
            })
            continue

        # Política: GCP_Resource_Missing_Required_Labels
        if asset.asset_type in REQUIRED_LABELS_BY_ASSET_TYPE:
            required_labels_for_type = REQUIRED_LABELS_BY_ASSET_TYPE[asset.asset_type]
            asset_labels: Dict[str, str] = {}
            if asset.resource and isinstance(asset.resource.get("labels"), dict): # GCP usa 'labels', não 'tags'
                asset_labels = asset.resource.get("labels")

            missing_labels = [req_label for req_label in required_labels_for_type if req_label not in asset_labels]

            if missing_labels:
                description = (
                    f"GCP resource '{asset.name}' of type '{asset.asset_type}' "
                    f"in project '{asset.project_id or 'UnknownProject'}' is missing required labels: {', '.join(missing_labels)}."
                )
                alerts_data.append({
                    "resource_id": asset.name, # Nome completo do recurso
                    "resource_type": f"GCP::{asset.asset_type}",
                    "provider": "gcp",
                    "severity": AlertSeverityEnum.LOW, # Ou Medium
                    "title": f"GCP Resource Missing Required Labels ({asset.asset_type})",
                    "description": description,
                    "policy_id": "GCP_Resource_Missing_Required_Labels",
                    "account_id": asset.project_id or account_id, # Usar project_id do ativo se disponível
                    "region": asset.location,
                    "details": {
                        "asset_name": asset.name,
                        "asset_type": asset.asset_type,
                        "project_id": asset.project_id,
                        "location": asset.location,
                        "current_labels": asset_labels,
                        "required_labels_for_type": required_labels_for_type,
                        "missing_labels": missing_labels
                    },
                    "recommendation": f"Ensure the resource has all required labels for proper governance and cost tracking: {', '.join(required_labels_for_type)}."
                })

        # Adicionar mais políticas baseadas em CAI aqui

    return alerts_data
