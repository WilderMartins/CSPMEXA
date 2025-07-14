from typing import List, Dict, Any, Optional
from ..schemas.huawei.huawei_csg_input_schemas import CSGRiskCollectionInput, CSGRiskItemInput
from ..schemas.alert_schema import AlertSeverityEnum

# Mapeamento de severidade do Huawei CSG para AlertSeverityEnum
# Os valores exatos ("Critical", "High", etc.) precisam ser confirmados com a API do CSG.
CSG_SEVERITY_MAP = {
    "CRITICAL": AlertSeverityEnum.CRITICAL,
    "HIGH": AlertSeverityEnum.HIGH,
    "SERIOUS": AlertSeverityEnum.HIGH, # Exemplo, CSG pode usar "Serious"
    "MAJOR": AlertSeverityEnum.HIGH,   # Exemplo
    "MEDIUM": AlertSeverityEnum.MEDIUM,
    "MINOR": AlertSeverityEnum.LOW,    # Exemplo
    "LOW": AlertSeverityEnum.LOW,
    "INFORMATIONAL": AlertSeverityEnum.INFORMATIONAL,
    "INFO": AlertSeverityEnum.INFORMATIONAL,
    "SUGGESTION": AlertSeverityEnum.INFORMATIONAL, # Exemplo
}

def evaluate_huawei_csg_policies(
    csg_risk_collection: Optional[CSGRiskCollectionInput],
    account_id: Optional[str] # project_id ou domain_id da Huawei usado na consulta
) -> List[Dict[str, Any]]:
    """
    Processa os riscos do Huawei Cloud Security Guard (CSG) e os transforma em alertas.
    """
    alerts_data: List[Dict[str, Any]] = []

    if not csg_risk_collection or not csg_risk_collection.risks:
        if csg_risk_collection and csg_risk_collection.error_message:
            alerts_data.append({
                "resource_id": account_id or "HuaweiCSG",
                "resource_type": "HuaweiCloud::CSG::RiskCollection",
                "provider": "huawei",
                "severity": AlertSeverityEnum.MEDIUM,
                "title": "Huawei CSG Risk Collection Failed",
                "description": f"Failed to collect CSG risks for account '{account_id}': {csg_risk_collection.error_message}",
                "policy_id": "CSG_GlobalCollection_Error",
                "account_id": account_id,
                "details": {
                    "project_id_queried": csg_risk_collection.project_id_queried,
                    "region_id_queried": csg_risk_collection.region_id_queried,
                    "error": csg_risk_collection.error_message
                }
            })
        return alerts_data

    for risk in csg_risk_collection.risks:
        if risk.collection_error_details:
            alerts_data.append({
                "resource_id": risk.risk_id,
                "resource_type": "HuaweiCloud::CSG::RiskItem",
                "provider": "huawei",
                "severity": AlertSeverityEnum.INFORMATIONAL,
                "title": "Huawei CSG Risk Item Parsing Issue",
                "description": f"Could not fully parse CSG risk item '{risk.risk_id}': {risk.collection_error_details}",
                "policy_id": "CSG_RiskItemParsing_Error",
                "account_id": risk.resource_info.project_id or account_id,
                "region": risk.resource_info.region_id,
                "details": {"risk_id": risk.risk_id, "check_name": risk.check_name, "error": risk.collection_error_details}
            })
            continue

        # Política: Huawei_CSG_Risk_Detected (transforma descobertas CSG em alertas CSPMEXA)
        # A severidade é mapeada. Filtramos apenas por HIGH e CRITICAL para este exemplo.

        csg_severity_upper = (risk.severity or "INFORMATIONAL").upper()
        mapped_severity = CSG_SEVERITY_MAP.get(csg_severity_upper, AlertSeverityEnum.INFORMATIONAL)

        # Decidir se todos os riscos do CSG viram alertas ou apenas alguns.
        # Por enquanto, vamos criar alertas para todos os riscos reportados pelo CSG,
        # usando a severidade mapeada.
        # Poderíamos ter uma política mais específica: "Huawei_CSG_High_Or_Critical_Risk_Detected"

        # if mapped_severity in [AlertSeverityEnum.HIGH, AlertSeverityEnum.CRITICAL]: # Filtrar só High/Critical
        alerts_data.append({
            "resource_id": risk.resource_info.id or risk.risk_id,
            "resource_type": f"HuaweiCloud::{risk.resource_info.type or 'GenericResource'}",
            "provider": "huawei",
            "severity": mapped_severity,
            "title": f"Huawei CSG Finding: {risk.check_name or risk.risk_id}",
            "description": risk.description or "No description provided by CSG.",
            "policy_id": f"CSG_{risk.check_name.replace(' ', '_').upper()}" if risk.check_name else f"CSG_RISK_{risk.risk_id}",
            "account_id": risk.resource_info.project_id or account_id,
            "region": risk.resource_info.region_id,
            "details": {
                "csg_risk_id": risk.risk_id,
                "csg_check_name": risk.check_name,
                "csg_status": risk.status,
                "csg_severity": risk.severity,
                "csg_resource_name": risk.resource_info.name,
                "csg_first_detected": risk.first_detected_time.isoformat() if risk.first_detected_time else None,
                "csg_last_detected": risk.last_detected_time.isoformat() if risk.last_detected_time else None,
                "csg_additional_properties": risk.additional_properties
            },
            "recommendation": risk.suggestion or "Refer to Huawei Cloud Security Guard console for remediation advice."
        })

    return alerts_data
