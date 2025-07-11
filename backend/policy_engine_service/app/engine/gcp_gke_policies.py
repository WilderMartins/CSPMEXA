from typing import List, Dict, Any, Optional
from app.schemas.gcp.gke_input_schema import GKEClusterDataInput # Schema de input do GKE
from app.schemas.alert_schema import AlertSeverityEnum # Enum de severidade

def evaluate_gke_policies(
    gke_clusters_data: List[GKEClusterDataInput],
    project_id: Optional[str] # project_id é o account_id para GCP
) -> List[Dict[str, Any]]:
    """
    Avalia todas as políticas GKE para uma lista de clusters.
    Retorna uma lista de dicionários, cada um representando dados para AlertCreate.
    """
    alerts_data: List[Dict[str, Any]] = []

    for cluster in gke_clusters_data:
        if cluster.error_details: # Pular clusters com erro de coleta
            alerts_data.append({
                "resource_id": cluster.name or "UNKNOWN_GKE_CLUSTER",
                "resource_type": "GCP::KubernetesEngine::Cluster",
                "provider": "gcp",
                "severity": AlertSeverityEnum.INFORMATIONAL, # Ou WARNING, dependendo da política
                "title": "GKE Cluster Data Collection Error",
                "description": f"Could not fully assess GKE cluster '{cluster.name}' in project '{project_id}' due to a collection error: {cluster.error_details}",
                "policy_id": "GKE_Collection_Error",
                "account_id": project_id,
                "region": cluster.location or "N/A",
                "details": {"cluster_name": cluster.name, "error": cluster.error_details}
            })
            continue

        alerts_data.extend(check_gke_cluster_public_endpoint(cluster, project_id))
        alerts_data.extend(check_gke_cluster_network_policy_disabled(cluster, project_id))
        alerts_data.extend(check_gke_cluster_node_auto_upgrade_disabled(cluster, project_id))
        alerts_data.extend(check_gke_cluster_logging_monitoring_disabled(cluster, project_id))
        # Adicionar chamadas para outras políticas GKE aqui

    return alerts_data

def check_gke_cluster_public_endpoint(
    cluster: GKEClusterDataInput,
    project_id: Optional[str]
) -> List[Dict[str, Any]]:
    """
    Verifica se o endpoint do master do cluster GKE é público.
    Policy ID: GKE_Cluster_Public_Endpoint
    """
    alerts_data: List[Dict[str, Any]] = []
    # `has_public_endpoint` é um campo extraído pelo collector.
    # Se PrivateClusterConfig está habilitado e publicEndpoint está vazio, é privado.
    # Se PrivateClusterConfig não está habilitado, ou se publicEndpoint tem valor, é público.

    is_public = True # Assumir público por padrão se a informação não for clara
    if cluster.private_cluster_config:
        if cluster.private_cluster_config.enable_private_endpoint and not cluster.private_cluster_config.public_endpoint:
            is_public = False
        elif cluster.private_cluster_config.public_endpoint: # Mesmo que private_endpoint esteja habilitado, se public_endpoint existir, ele é acessível publicamente.
            is_public = True
    elif cluster.endpoint: # Se não há private_cluster_config mas há um endpoint, ele é público.
        is_public = True

    # O campo `has_public_endpoint` no schema GKEClusterDataInput (que vem do collector) já deve ter essa lógica.
    if cluster.has_public_endpoint is True or (cluster.has_public_endpoint is None and is_public): # Confia no campo do collector ou recalcula
        alerts_data.append({
            "resource_id": cluster.name,
            "resource_type": "GCP::KubernetesEngine::Cluster",
            "provider": "gcp",
            "severity": AlertSeverityEnum.HIGH,
            "title": "GKE Cluster Master Endpoint is Publicly Accessible",
            "description": f"The master endpoint for GKE cluster '{cluster.name}' in project '{project_id}' (location: {cluster.location or 'N/A'}) is publicly accessible. This increases the attack surface.",
            "policy_id": "GKE_Cluster_Public_Endpoint",
            "account_id": project_id,
            "region": cluster.location or "N/A",
            "details": {
                "cluster_name": cluster.name,
                "endpoint": cluster.endpoint,
                "private_cluster_enabled": cluster.private_cluster_config.enable_private_nodes if cluster.private_cluster_config else False,
                "public_endpoint_address": cluster.private_cluster_config.public_endpoint if cluster.private_cluster_config else cluster.endpoint,
            },
            "recommendation": "Enable private endpoint and disable public endpoint access for GKE clusters. If public access is required, restrict it using Master Authorized Networks."
        })
    return alerts_data

def check_gke_cluster_network_policy_disabled(
    cluster: GKEClusterDataInput,
    project_id: Optional[str]
) -> List[Dict[str, Any]]:
    """
    Verifica se as políticas de rede (NetworkPolicy) não estão habilitadas no cluster GKE.
    Policy ID: GKE_Cluster_Network_Policy_Disabled
    """
    alerts_data: List[Dict[str, Any]] = []
    # `network_policy_enabled` é um campo extraído pelo collector.
    # Verifica networkPolicy.enabled ou addonsConfig.networkPolicyConfig.disabled

    network_policy_explicitly_enabled = False
    if cluster.network_policy and cluster.network_policy.enabled:
        network_policy_explicitly_enabled = True
    elif cluster.addons_config and cluster.addons_config.network_policy_config and \
         cluster.addons_config.network_policy_config.get("disabled") is False: # Se disabled: false, então está habilitado
        network_policy_explicitly_enabled = True

    if cluster.network_policy_enabled is False or (cluster.network_policy_enabled is None and not network_policy_explicitly_enabled):
        alerts_data.append({
            "resource_id": cluster.name,
            "resource_type": "GCP::KubernetesEngine::Cluster",
            "provider": "gcp",
            "severity": AlertSeverityEnum.MEDIUM,
            "title": "GKE Cluster Network Policy Disabled",
            "description": f"Network Policy enforcement is disabled for GKE cluster '{cluster.name}' in project '{project_id}' (location: {cluster.location or 'N/A'}). This allows all pod-to-pod traffic by default, potentially exposing workloads.",
            "policy_id": "GKE_Cluster_Network_Policy_Disabled",
            "account_id": project_id,
            "region": cluster.location or "N/A",
            "details": {
                "cluster_name": cluster.name,
                "network_policy_provider": cluster.network_policy.provider if cluster.network_policy else "N/A",
                "network_policy_addon_disabled": cluster.addons_config.network_policy_config.get("disabled") if cluster.addons_config and cluster.addons_config.network_policy_config else "N/A",
            },
            "recommendation": "Enable Network Policy for the GKE cluster and define policies to restrict pod communication to only what is necessary. This helps in segmenting workloads and limiting the blast radius of a compromise."
        })
    return alerts_data

def check_gke_cluster_node_auto_upgrade_disabled(
    cluster: GKEClusterDataInput,
    project_id: Optional[str]
) -> List[Dict[str, Any]]:
    """
    Verifica se o auto-upgrade de nós está desabilitado nos node pools do cluster GKE.
    Policy ID: GKE_Cluster_Node_Auto_Upgrade_Disabled
    """
    alerts_data: List[Dict[str, Any]] = []
    # O campo `node_auto_upgrade_enabled_default` é uma conveniência do collector para o primeiro node pool.
    # É melhor iterar por todos os node pools.

    disabled_node_pools = []
    if cluster.node_pools:
        for np in cluster.node_pools:
            if np.management and np.management.auto_upgrade is False:
                disabled_node_pools.append(np.name)

    if disabled_node_pools:
        alerts_data.append({
            "resource_id": cluster.name,
            "resource_type": "GCP::KubernetesEngine::Cluster",
            "provider": "gcp",
            "severity": AlertSeverityEnum.MEDIUM,
            "title": "GKE Node Auto-Upgrade Disabled for Some Node Pools",
            "description": f"Node auto-upgrade is disabled for the following node pool(s) in GKE cluster '{cluster.name}' (project: '{project_id}', location: {cluster.location or 'N/A'}): {', '.join(disabled_node_pools)}. This can lead to nodes running outdated and potentially vulnerable Kubernetes versions.",
            "policy_id": "GKE_Cluster_Node_Auto_Upgrade_Disabled",
            "account_id": project_id,
            "region": cluster.location or "N/A",
            "details": {
                "cluster_name": cluster.name,
                "node_pools_with_auto_upgrade_disabled": disabled_node_pools,
                "node_pools_total": len(cluster.node_pools)
            },
            "recommendation": "Enable node auto-upgrade for all node pools to ensure nodes are kept up-to-date with the latest stable and secure Kubernetes versions compatible with the GKE master."
        })
    return alerts_data

def check_gke_cluster_logging_monitoring_disabled(
    cluster: GKEClusterDataInput,
    project_id: Optional[str]
) -> List[Dict[str, Any]]:
    """
    Verifica se o logging e monitoring para Cloud Operations (Stackdriver) não estão configurados/habilitados.
    Policy ID: GKE_Cluster_Logging_Monitoring_Disabled
    """
    alerts_data: List[Dict[str, Any]] = []

    logging_disabled = True
    if cluster.logging_service and "googleapis.com" in cluster.logging_service:
        if cluster.logging_config and cluster.logging_config.enable_components:
            if "SYSTEM_COMPONENTS" in cluster.logging_config.enable_components and \
               "WORKLOADS" in cluster.logging_config.enable_components:
                logging_disabled = False
            elif not cluster.logging_config.enable_components: # Empty list might mean default, which is usually enabled.
                logging_disabled = False # Assuming default is fine. API might return empty if default (all) components are enabled.
        elif not cluster.logging_config: # If logging_config is not present but logging_service is, assume default (enabled)
            logging_disabled = False


    monitoring_disabled = True
    if cluster.monitoring_service and "googleapis.com" in cluster.monitoring_service:
        if cluster.monitoring_config and cluster.monitoring_config.enable_components:
            if "SYSTEM_COMPONENTS" in cluster.monitoring_config.enable_components: # WORKLOADS is optional for monitoring
                monitoring_disabled = False
            elif not cluster.monitoring_config.enable_components:
                monitoring_disabled = False
        elif not cluster.monitoring_config:
            monitoring_disabled = False

    if logging_disabled or monitoring_disabled:
        missing_services = []
        if logging_disabled: missing_services.append("Logging (Cloud Operations)")
        if monitoring_disabled: missing_services.append("Monitoring (Cloud Operations)")

        alerts_data.append({
            "resource_id": cluster.name,
            "resource_type": "GCP::KubernetesEngine::Cluster",
            "provider": "gcp",
            "severity": AlertSeverityEnum.MEDIUM,
            "title": f"GKE Cluster Lacks Full Cloud Operations Integration ({', '.join(missing_services)})",
            "description": f"{', '.join(missing_services)} to Google Cloud Operations (formerly Stackdriver) may not be fully enabled or configured for GKE cluster '{cluster.name}' in project '{project_id}' (location: {cluster.location or 'N/A'}). This can hinder visibility and troubleshooting.",
            "policy_id": "GKE_Cluster_Logging_Monitoring_Disabled",
            "account_id": project_id,
            "region": cluster.location or "N/A",
            "details": {
                "cluster_name": cluster.name,
                "logging_service": cluster.logging_service,
                "logging_components": cluster.logging_config.enable_components if cluster.logging_config else "Default/Not Specified",
                "monitoring_service": cluster.monitoring_service,
                "monitoring_components": cluster.monitoring_config.enable_components if cluster.monitoring_config else "Default/Not Specified",
            },
            "recommendation": "Ensure that both system component and workload logging/monitoring are enabled for the GKE cluster and integrated with Google Cloud Operations for comprehensive observability."
        })
    return alerts_data

# Adicionar mais funções de política GKE aqui, por exemplo:
# - check_gke_master_authorized_networks_disabled_or_too_open
# - check_gke_basic_authentication_enabled (se aplicável, é legado)
# - check_gke_legacy_abac_enabled (se aplicável, é legado)
# - check_gke_shielded_nodes_disabled
# - check_gke_binary_authorization_disabled
```
