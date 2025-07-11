import google.auth
from google.cloud import container_v1
from google.auth.exceptions import DefaultCredentialsError
from typing import List, Optional, Dict, Any
from app.schemas.gcp_gke_schemas import GKEClusterData, GKENodePool, GKENodeConfig, GKENodePoolAutoscaling, GKEMasterAuth, GKENetworkPolicy, GKEIPAllocationPolicy, GKELoggingConfig, GKEMonitoringConfig, GKEAddonsConfig, GKEPrivateClusterConfig, GKEMaintenancePolicy, GKEAutopilot, GKENodePoolManagement
from app.gcp.gcp_utils import get_gcp_project_id, get_regional_client_options, get_zonal_client_options
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def get_gke_clusters(project_id: Optional[str] = None, location: str = "-") -> List[GKEClusterData]:
    """
    Collects data for all GKE clusters in a specific project and location (region or zone).
    If location is "-", it will list clusters in all locations (regions/zones).
    """
    resolved_project_id = get_gcp_project_id(project_id)
    if not resolved_project_id:
        logger.error("GCP Project ID is not specified and could not be determined from the environment.")
        return [GKEClusterData(name="ERROR_NO_PROJECT_ID", project_id="UNKNOWN", error_details="GCP Project ID not found.")]

    try:
        credentials, _ = google.auth.default()
        # The parent for list_clusters is "projects/{project_id}/locations/{location}"
        # If location is "-", it means all locations.
        parent = f"projects/{resolved_project_id}/locations/{location}"

        client = container_v1.ClusterManagerClient(credentials=credentials)

        request = container_v1.ListClustersRequest(parent=parent)
        response = client.list_clusters(request=request)

        gke_clusters_data: List[GKEClusterData] = []

        if not response.clusters and response.missing_zones:
            logger.warning(f"No GKE clusters found for project {resolved_project_id} in location '{location}'. Missing zones: {response.missing_zones}")
            # It's possible no clusters exist, or the API key/SA doesn't have GKE viewer permissions for these zones.
            # Or the GKE API is not enabled for the project.
            return []

        if not response.clusters:
            logger.info(f"No GKE clusters found for project {resolved_project_id} in location '{location}'.")
            return []

        for cluster_raw in response.clusters:
            try:
                # Helper to convert protobuf Timestamp to datetime
                def _ts_to_datetime(timestamp) -> Optional[datetime]:
                    if timestamp and timestamp.seconds:
                        return datetime.fromtimestamp(timestamp.seconds + timestamp.nanos / 1e9, tz=datetime.timezone.utc)
                    return None

                node_pools_data = []
                for np_raw in cluster_raw.node_pools:
                    node_pools_data.append(GKENodePool(
                        name=np_raw.name,
                        version=np_raw.version,
                        initial_node_count=np_raw.initial_node_count,
                        autoscaling=GKENodePoolAutoscaling(
                            enabled=np_raw.autoscaling.enabled,
                            min_node_count=np_raw.autoscaling.min_node_count,
                            max_node_count=np_raw.autoscaling.max_node_count
                        ) if np_raw.autoscaling else None,
                        status=container_v1.NodePool.Status(np_raw.status).name if np_raw.status else None,
                        config=GKENodeConfig(
                            machine_type=np_raw.config.machine_type,
                            disk_size_gb=np_raw.config.disk_size_gb,
                            oauth_scopes=list(np_raw.config.oauth_scopes),
                            service_account=np_raw.config.service_account
                        ) if np_raw.config else None,
                        management=GKENodePoolManagement(
                            auto_upgrade=np_raw.management.auto_upgrade,
                            auto_repair=np_raw.management.auto_repair
                        ) if np_raw.management else None,
                    ))

                private_cluster_cfg = None
                if cluster_raw.private_cluster_config:
                    private_cluster_cfg = GKEPrivateClusterConfig(
                        enable_private_nodes=cluster_raw.private_cluster_config.enable_private_nodes,
                        enable_private_endpoint=cluster_raw.private_cluster_config.enable_private_endpoint,
                        master_ipv4_cidr_block=cluster_raw.private_cluster_config.master_ipv4_cidr_block,
                        private_endpoint=cluster_raw.private_cluster_config.private_endpoint,
                        public_endpoint=cluster_raw.private_cluster_config.public_endpoint
                    )

                cluster_data = GKEClusterData(
                    name=cluster_raw.name,
                    description=cluster_raw.description,
                    initial_node_count=cluster_raw.initial_node_count,
                    node_pools=node_pools_data,
                    locations=list(cluster_raw.locations) if cluster_raw.locations else None,
                    location=cluster_raw.location, # This is the primary location (zone or region)
                    endpoint=cluster_raw.endpoint,
                    initial_cluster_version=cluster_raw.initial_cluster_version,
                    current_master_version=cluster_raw.current_master_version,
                    current_node_version=cluster_raw.current_node_version,
                    create_time=_ts_to_datetime(cluster_raw.create_time),
                    status=container_v1.Cluster.Status(cluster_raw.status).name if cluster_raw.status else None,
                    status_message=cluster_raw.status_message,
                    node_ipv4_cidr_size=cluster_raw.node_ipv4_cidr_size,
                    services_ipv4_cidr=cluster_raw.services_ipv4_cidr,
                    instance_group_urls=list(cluster_raw.instance_group_urls),
                    self_link=cluster_raw.self_link,
                    zone=cluster_raw.zone, # Deprecated, use location
                    network=cluster_raw.network.split('/')[-1] if cluster_raw.network else None, # Extract name
                    subnetwork=cluster_raw.subnetwork.split('/')[-1] if cluster_raw.subnetwork else None, # Extract name
                    private_cluster_config=private_cluster_cfg,
                    master_authorized_networks_config=dict(cluster_raw.master_authorized_networks_config) if cluster_raw.master_authorized_networks_config else None, # simplify
                    ip_allocation_policy=GKEIPAllocationPolicy(use_ip_aliases=cluster_raw.ip_allocation_policy.use_ip_aliases) if cluster_raw.ip_allocation_policy else None,
                    network_policy=GKENetworkPolicy(
                        provider=container_v1.NetworkPolicy.Provider(cluster_raw.network_policy.provider).name if cluster_raw.network_policy.provider else None,
                        enabled=cluster_raw.network_policy.enabled
                    ) if cluster_raw.network_policy else None,
                    addons_config=GKEAddonsConfig(
                        http_load_balancing={"disabled": cluster_raw.addons_config.http_load_balancing.disabled} if cluster_raw.addons_config.http_load_balancing else None,
                        horizontal_pod_autoscaling={"disabled": cluster_raw.addons_config.horizontal_pod_autoscaling.disabled} if cluster_raw.addons_config.horizontal_pod_autoscaling else None,
                        network_policy_config={"disabled": cluster_raw.addons_config.network_policy_config.disabled} if cluster_raw.addons_config.network_policy_config else None
                    ) if cluster_raw.addons_config else None,
                    logging_service=cluster_raw.logging_service,
                    monitoring_service=cluster_raw.monitoring_service,
                    logging_config=GKELoggingConfig(enable_components=list(cluster_raw.logging_config.component_config.enable_components)) if cluster_raw.logging_config and cluster_raw.logging_config.component_config else None,
                    monitoring_config=GKEMonitoringConfig(enable_components=list(cluster_raw.monitoring_config.component_config.enable_components)) if cluster_raw.monitoring_config and cluster_raw.monitoring_config.component_config else None,
                    maintenance_policy=GKEMaintenancePolicy(window=str(cluster_raw.maintenance_policy.window)) if cluster_raw.maintenance_policy else None, # Simplified
                    autopilot=GKEAutopilot(enabled=cluster_raw.autopilot.enabled) if cluster_raw.autopilot else None,
                    project_id=resolved_project_id,
                    # Extracted fields
                    is_autopilot=cluster_raw.autopilot.enabled if cluster_raw.autopilot else False,
                    has_public_endpoint=bool(private_cluster_cfg.public_endpoint) if private_cluster_cfg else (cluster_raw.endpoint is not None), # Approximation
                    network_policy_enabled=(cluster_raw.network_policy.enabled if cluster_raw.network_policy else False) or \
                                           (not cluster_raw.addons_config.network_policy_config.disabled if cluster_raw.addons_config and cluster_raw.addons_config.network_policy_config else False),
                    node_auto_upgrade_enabled_default=cluster_raw.node_pools[0].management.auto_upgrade if cluster_raw.node_pools and cluster_raw.node_pools[0].management else None,
                )
                gke_clusters_data.append(cluster_data)
            except Exception as e:
                logger.error(f"Error processing GKE cluster {cluster_raw.name}: {e}", exc_info=True)
                gke_clusters_data.append(GKEClusterData(
                    name=cluster_raw.name,
                    project_id=resolved_project_id,
                    location=cluster_raw.location,
                    error_details=str(e)
                ))

        return gke_clusters_data

    except DefaultCredentialsError:
        logger.error(f"GCP default credentials not found for GKE collector (project: {resolved_project_id}).")
        return [GKEClusterData(name="ERROR_NO_CREDENTIALS", project_id=resolved_project_id or "UNKNOWN", error_details="GCP credentials not found.")]
    except Exception as e:
        logger.exception(f"Unexpected error collecting GKE data for project {resolved_project_id} in location '{location}': {e}")
        return [GKEClusterData(name=f"ERROR_COLLECTING_GKE_LOCATION_{location.replace('/','_')}", project_id=resolved_project_id or "UNKNOWN", error_details=str(e))]

if __name__ == '__main__':
    # For local testing:
    # Ensure GOOGLE_APPLICATION_CREDENTIALS is set or you are logged in via gcloud CLI
    # And that the GKE API (container.googleapis.com) is enabled for your project.

    # Test with a specific project ID (replace with your project ID)
    # test_project_id = "your-gcp-project-id"
    # print(f"Attempting to fetch GKE clusters for project: {test_project_id} (all locations)")
    # clusters = get_gke_clusters(project_id=test_project_id)

    # Test without specifying project_id (will try to use default from environment)
    print("Attempting to fetch GKE clusters for default project (all locations)")
    clusters = get_gke_clusters()

    if clusters:
        for cluster in clusters:
            if cluster.error_details:
                print(f"Cluster: {cluster.name}, Project: {cluster.project_id}, Location: {cluster.location}, Error: {cluster.error_details}")
            else:
                print(f"Cluster: {cluster.name}, Project: {cluster.project_id}, Location: {cluster.location}, Master Ver: {cluster.current_master_version}, Status: {cluster.status}, Public Endpoint: {cluster.has_public_endpoint}, Autopilot: {cluster.is_autopilot}")
                # print(f"Full data: {cluster.model_dump_json(indent=2)}")
    else:
        print("No GKE clusters found or an error occurred during collection.")

    # Test for a specific location (e.g., a region)
    # test_region = "us-central1"
    # print(f"\nAttempting to fetch GKE clusters for default project in region: {test_region}")
    # regional_clusters = get_gke_clusters(location=test_region)
    # if regional_clusters:
    #     for cluster in regional_clusters:
    #         print(f"  Cluster: {cluster.name}, Status: {cluster.status}")
    # else:
    #     print(f"No GKE clusters found in region {test_region} or error occurred.")
```
