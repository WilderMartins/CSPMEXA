from typing import List, Dict, Any

def check_cloudtrail_multi_region(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Verifica se existe pelo menos um trail multi-região.
    CIS-AWS-2.2
    """
    alerts = []
    is_multi_region_trail_found = False
    for item in data:
        trail_info = item.get('trail_info', {})
        if trail_info.get('is_multi_region_trail'):
            is_multi_region_trail_found = True
            break

    if not is_multi_region_trail_found:
        alerts.append({
            "resource_id": "N/A",
            "resource_type": "AWS Account",
            "region": "Global",
            "status": "FAIL",
            "details": "Nenhum trail do CloudTrail multi-região foi encontrado na conta."
        })
    return alerts

def check_cloudtrail_log_file_validation(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Verifica se a validação de arquivos de log está habilitada para todos os trails.
    CIS-AWS-2.3
    """
    alerts = []
    for item in data:
        trail_info = item.get('trail_info', {})
        if not trail_info.get('log_file_validation_enabled'):
            alerts.append({
                "resource_id": trail_info.get('name'),
                "resource_type": "CloudTrail Trail",
                "region": trail_info.get('home_region'),
                "status": "FAIL",
                "details": f"A validação de arquivos de log não está habilitada para o trail '{trail_info.get('name')}'."
            })
    return alerts
