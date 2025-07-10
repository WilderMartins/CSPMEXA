from google.cloud import compute_v1
from google.cloud.exceptions import GoogleCloudError, NotFound, Forbidden
from typing import List, Optional, Dict, Any
from app.schemas.gcp_compute import GCPComputeInstanceData, GCPFirewallData
from app.gcp.gcp_client_manager import get_compute_client, get_compute_firewalls_client, get_gcp_project_id
import logging
from datetime import datetime, timezone # Para parsear timestamps

logger = logging.getLogger(__name__)

def _extract_name_from_url(url: Optional[str]) -> str:
    """Extrai o último componente de uma URL do GCP (ex: nome da zona, tipo de máquina)."""
    if not url:
        return "N/A"
    return url.split('/')[-1]

def _parse_gcp_timestamp(timestamp_str: Optional[str]) -> Optional[datetime]:
    """Converte timestamp string do GCP para objeto datetime UTC."""
    if not timestamp_str:
        return None
    try:
        # Formato comum: "2023-10-27T10:30:00.123-07:00" ou com 'Z'
        # O Python datetime.fromisoformat lida bem com isso se o timezone for simples (+HH:MM ou Z)
        # No entanto, às vezes o GCP retorna formatos que podem precisar de parse mais robusto.
        # Se o timestamp já tiver 'Z', fromisoformat funciona.
        # Se tiver +HH:MM, fromisoformat também funciona.
        # O problema pode ser se não tiver timezone info, aí assumimos UTC ou local.
        # A API do Compute Engine geralmente retorna RFC3339.

        # Remover o 'Z' se existir, pois o Python < 3.11 pode não gostar dele com fromisoformat diretamente
        # dependendo da precisão dos microssegundos.
        # if timestamp_str.endswith('Z'):
        #     timestamp_str = timestamp_str[:-1] + "+00:00"

        dt_obj = datetime.fromisoformat(timestamp_str)
        # Se o objeto for naive, assumir UTC (embora a API deva retornar com offset)
        if dt_obj.tzinfo is None:
            return dt_obj.replace(tzinfo=timezone.utc)
        return dt_obj.astimezone(timezone.utc) # Normalizar para UTC
    except ValueError as e:
        logger.warning(f"Could not parse GCP timestamp string '{timestamp_str}': {e}")
        # Tentar com formatos alternativos se necessário, ou retornar None
        try: # Tentar um formato comum sem sub-segundos e com Z
            return datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            pass
        return None


async def get_gcp_compute_instances(project_id: Optional[str] = None) -> List[GCPComputeInstanceData]:
    """Coleta dados de instâncias de VM do Compute Engine para um projeto, agregando de todas as zonas."""
    actual_project_id = project_id or get_gcp_project_id()
    if not actual_project_id:
        logger.error("GCP Project ID is required for collecting Compute Instances.")
        return [GCPComputeInstanceData(
            id="ERROR_PROJECT_ID_MISSING", name="ERROR_PROJECT_ID_MISSING", zone="global", machine_type="N/A",
            status="ERROR", creation_timestamp=datetime.now(timezone.utc), project_id="N/A",
            extracted_zone="N/A", extracted_machine_type="N/A",
            error_details="GCP Project ID is required but was not provided or found."
        )]

    instances_data: List[GCPComputeInstanceData] = []
    try:
        instances_client = get_compute_client()
        # aggregated_list retorna um iterador de tuplas (scope, instances_scoped_list_object)
        # scope é geralmente 'zones/zone-name'
        aggregated_result = instances_client.aggregated_list(project=actual_project_id)

        for scope_name, instances_in_scope in aggregated_result:
            if instances_in_scope.instances: # Verifica se há instâncias nesta zona/scope
                for instance_native in instances_in_scope.instances:
                    error_msg_instance = []
                    public_ips = []
                    private_ips = []

                    if instance_native.network_interfaces:
                        for ni in instance_native.network_interfaces:
                            if ni.network_ip: # IP Privado principal da interface
                                private_ips.append(ni.network_ip)
                            if ni.access_configs:
                                for ac in ni.access_configs:
                                    if ac.nat_ip: # IP Público
                                        public_ips.append(ac.nat_ip)

                    tags_items = []
                    if hasattr(instance_native, 'tags') and instance_native.tags and hasattr(instance_native.tags, 'items'):
                        tags_items = list(instance_native.tags.items)


                    instance_obj = GCPComputeInstanceData(
                        id=str(instance_native.id) if instance_native.id else "N/A",
                        name=instance_native.name or "N/A",
                        description=instance_native.description,
                        zone=instance_native.zone, # URL completa da zona
                        machine_type=instance_native.machine_type, # URL completa
                        status=instance_native.status,
                        creation_timestamp=_parse_gcp_timestamp(instance_native.creation_timestamp) or datetime.now(timezone.utc),
                        can_ip_forward=instance_native.can_ip_forward,
                        deletion_protection=instance_native.deletion_protection,
                        network_interfaces=instance_native.network_interfaces, # Passar o objeto diretamente, Pydantic fará o parse
                        disks=instance_native.disks,
                        service_accounts=instance_native.service_accounts,
                        scheduling=instance_native.scheduling,
                        tags_fingerprint=instance_native.tags.fingerprint if hasattr(instance_native, 'tags') and instance_native.tags else None,
                        tags_items=tags_items,
                        labels=dict(instance_native.labels) if instance_native.labels else None,
                        label_fingerprint=instance_native.label_fingerprint,
                        project_id=actual_project_id,
                        extracted_zone=_extract_name_from_url(instance_native.zone),
                        extracted_machine_type=_extract_name_from_url(instance_native.machine_type),
                        public_ip_addresses=public_ips,
                        private_ip_addresses=private_ips,
                        error_details="; ".join(error_msg_instance) if error_msg_instance else None
                    )
                    instances_data.append(instance_obj)

    except GoogleCloudError as e:
        logger.error(f"Failed to list GCP Compute Instances for project {actual_project_id}: {e}")
        return [GCPComputeInstanceData(
            id=f"ERROR_LIST_INSTANCES_{actual_project_id}", name=f"ERROR_LIST_INSTANCES_{actual_project_id}",
            zone="global", machine_type="N/A", status="ERROR", creation_timestamp=datetime.now(timezone.utc), project_id=actual_project_id,
            extracted_zone="N/A", extracted_machine_type="N/A",
            error_details=f"Failed to list GCP Compute Instances: {str(e)}"
        )]
    except Exception as e:
        logger.error(f"Unexpected error collecting Compute Instances for project {actual_project_id}: {e}", exc_info=True)
        return [GCPComputeInstanceData(
             id=f"ERROR_UNEXPECTED_INSTANCES_{actual_project_id}", name=f"ERROR_UNEXPECTED_INSTANCES_{actual_project_id}",
            zone="global", machine_type="N/A", status="ERROR", creation_timestamp=datetime.now(timezone.utc), project_id=actual_project_id,
            extracted_zone="N/A", extracted_machine_type="N/A",
            error_details=f"Unexpected error collecting GCP Compute Instances: {str(e)}"
        )]

    logger.info(f"Collected {len(instances_data)} GCP Compute Instances for project {actual_project_id}.")
    return instances_data


async def get_gcp_firewall_rules(project_id: Optional[str] = None) -> List[GCPFirewallData]:
    """Coleta dados de regras de Firewall VPC para um projeto."""
    actual_project_id = project_id or get_gcp_project_id()
    if not actual_project_id:
        logger.error("GCP Project ID is required for collecting Firewall Rules.")
        return [GCPFirewallData(
            id="ERROR_PROJECT_ID_MISSING", name="ERROR_PROJECT_ID_MISSING", network="N/A", priority=0, direction="N/A",
            disabled=True, creation_timestamp=datetime.now(timezone.utc), project_id="N/A", extracted_network_name="N/A",
            error_details="GCP Project ID is required but was not provided or found."
        )]

    firewalls_data: List[GCPFirewallData] = []
    try:
        firewalls_client = get_compute_firewalls_client()
        firewall_list_native = firewalls_client.list(project=actual_project_id) # Iterador

        for firewall_native in firewall_list_native:
            error_msg_firewall = []

            # LogConfig pode ser None ou um objeto com 'enable' e 'metadata'
            log_config_data = None
            if firewall_native.log_config and hasattr(firewall_native.log_config, 'enable'):
                log_config_data = {"enable": firewall_native.log_config.enable}
                if hasattr(firewall_native.log_config, 'metadata'):
                    log_config_data["metadata"] = firewall_native.log_config.metadata


            firewall_obj = GCPFirewallData(
                id=str(firewall_native.id) if firewall_native.id else "N/A",
                name=firewall_native.name or "N/A",
                description=firewall_native.description,
                network=firewall_native.network, # URL completa da rede
                priority=firewall_native.priority,
                direction=firewall_native.direction,
                allowed=firewall_native.allowed, # Lista de AllowedRule, Pydantic fará o parse
                denied=firewall_native.denied,   # Lista de DeniedRule
                source_ranges=list(firewall_native.source_ranges) if firewall_native.source_ranges else None,
                destination_ranges=list(firewall_native.destination_ranges) if firewall_native.destination_ranges else None,
                source_tags=list(firewall_native.source_tags) if firewall_native.source_tags else None,
                target_tags=list(firewall_native.target_tags) if firewall_native.target_tags else None,
                source_service_accounts=list(firewall_native.source_service_accounts) if firewall_native.source_service_accounts else None,
                target_service_accounts=list(firewall_native.target_service_accounts) if firewall_native.target_service_accounts else None,
                disabled=firewall_native.disabled,
                log_config=log_config_data, # Passar o dict para Pydantic parsear
                creation_timestamp=_parse_gcp_timestamp(firewall_native.creation_timestamp) or datetime.now(timezone.utc),
                project_id=actual_project_id,
                extracted_network_name=_extract_name_from_url(firewall_native.network),
                error_details="; ".join(error_msg_firewall) if error_msg_firewall else None
            )
            firewalls_data.append(firewall_obj)

    except GoogleCloudError as e:
        logger.error(f"Failed to list GCP Firewall Rules for project {actual_project_id}: {e}")
        return [GCPFirewallData(
            id=f"ERROR_LIST_FIREWALLS_{actual_project_id}", name=f"ERROR_LIST_FIREWALLS_{actual_project_id}",
            network="N/A", priority=0, direction="N/A", disabled=True, creation_timestamp=datetime.now(timezone.utc),
            project_id=actual_project_id, extracted_network_name="N/A",
            error_details=f"Failed to list GCP Firewall Rules: {str(e)}"
        )]
    except Exception as e:
        logger.error(f"Unexpected error collecting Firewall Rules for project {actual_project_id}: {e}", exc_info=True)
        return [GCPFirewallData(
            id=f"ERROR_UNEXPECTED_FIREWALLS_{actual_project_id}", name=f"ERROR_UNEXPECTED_FIREWALLS_{actual_project_id}",
            network="N/A", priority=0, direction="N/A", disabled=True, creation_timestamp=datetime.now(timezone.utc),
            project_id=actual_project_id, extracted_network_name="N/A",
            error_details=f"Unexpected error collecting GCP Firewall Rules: {str(e)}"
        )]

    logger.info(f"Collected {len(firewalls_data)} GCP Firewall Rules for project {actual_project_id}.")
    return firewalls_data
