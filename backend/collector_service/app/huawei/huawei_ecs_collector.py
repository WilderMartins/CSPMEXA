from huaweicloudsdkcore.exceptions import exceptions as sdk_exceptions
from huaweicloudsdkecs.v2.model import ListServersDetailsRequest, ShowServerRequest # Para VMs
from huaweicloudsdkvpc.v2.model import ListSecurityGroupsRequest, ListSecurityGroupRulesRequest # Para SGs

from typing import List, Optional, Dict, Any
from app.schemas.huawei_ecs import (
    HuaweiECSServerData, HuaweiECSAddress, HuaweiECSImage, HuaweiECSFlavor,
    HuaweiECSServerMetadata, HuaweiVPCSecurityGroup, HuaweiVPCSecurityGroupRule
)
from app.huawei.huawei_client_manager import get_ecs_client, get_vpc_client, get_huawei_credentials
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

def _parse_huawei_timestamp(timestamp_str: Optional[str]) -> Optional[datetime]:
    if not timestamp_str:
        return None
    try:
        # Formato comum: "2023-10-27T10:30:00Z" ou "2023-10-27T10:30:00.000000"
        # O SDK pode retornar objetos datetime já, mas se for string:
        if isinstance(timestamp_str, datetime):
            if timestamp_str.tzinfo is None:
                return timestamp_str.replace(tzinfo=timezone.utc)
            return timestamp_str.astimezone(timezone.utc)

        if timestamp_str.endswith('Z'):
            dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ")
        elif '.' in timestamp_str: # Com microssegundos
             # Verificar se tem timezone info no final
            if '+' in timestamp_str or '-' == timestamp_str[-6] or '-' == timestamp_str[-3] : # ex: ...+00:00 or ...-07:00
                 dt = datetime.fromisoformat(timestamp_str)
            else: # Sem timezone explícito, assumir UTC
                 dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S.%f")

        else: # Sem microssegundos e sem Z
            dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S")

        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError as e:
        logger.warning(f"Could not parse Huawei timestamp string '{timestamp_str}': {e}")
        return None


async def get_huawei_ecs_instances(project_id: str, region_id: str) -> List[HuaweiECSServerData]:
    """Coleta dados de instâncias ECS (VMs) para um projeto e região."""
    collected_instances: List[HuaweiECSServerData] = []
    try:
        ecs_client = get_ecs_client(region_id=region_id)
    except ValueError as ve:
        logger.error(f"Credential error for Huawei ECS in region {region_id}: {ve}")
        return [HuaweiECSServerData(id="ERROR_CREDENTIALS", name="ERROR_CREDENTIALS", status="ERROR", created=_parse_huawei_timestamp(datetime.now(timezone.utc).isoformat()), project_id=project_id, region_id=region_id, error_details=str(ve), flavor={"id":"unknown"})]
    except Exception as e:
        logger.error(f"Failed to initialize ECS client for region {region_id}: {e}")
        return [HuaweiECSServerData(id=f"ERROR_CLIENT_INIT_{region_id}", name=f"ERROR_CLIENT_INIT_{region_id}", status="ERROR", created=_parse_huawei_timestamp(datetime.now(timezone.utc).isoformat()), project_id=project_id, region_id=region_id, error_details=str(e), flavor={"id":"unknown"})]

    try:
        # ListServersDetailsRequest pode ter parâmetros de paginação (marker, limit)
        # e filtros (name, status, etc.)
        request = ListServersDetailsRequest()
        # O SDK da Huawei pode esperar que o project_id seja parte das credenciais/config do cliente,
        # ou precise ser passado em algumas chamadas de API. O EcsClient é regional.
        # ListServersDetailsRequest não parece ter project_id como parâmetro direto.

        response = ecs_client.list_servers_details(request) # Bloqueante

        if not hasattr(response, 'servers') or not response.servers:
            logger.info(f"No ECS instances found for project {project_id} in region {region_id}.")
            return []

        for server_native in response.servers:
            error_msg_instance = []
            public_ips = []
            private_ips = []

            # Extrair IPs
            if server_native.addresses:
                for network_name, ip_list in server_native.addresses.items():
                    for ip_info in ip_list:
                        if hasattr(ip_info, 'addr'):
                            if hasattr(ip_info, 'os_ext_ips_type') and ip_info.os_ext_ips_type == 'floating':
                                public_ips.append(ip_info.addr)
                            else: # 'fixed' or unknown
                                private_ips.append(ip_info.addr)

            # Formatar Security Groups (vem como lista de dicts com 'name')
            sg_list_simple = []
            if hasattr(server_native, 'security_groups') and server_native.security_groups:
                for sg_dict in server_native.security_groups:
                    if isinstance(sg_dict, dict) and 'name' in sg_dict: # 'name' aqui é o ID do SG
                        sg_list_simple.append({"name": sg_dict['name']})

            # Metadata (vem como dict)
            custom_meta = None
            if hasattr(server_native, 'metadata') and server_native.metadata:
                custom_meta = HuaweiECSServerMetadata(custom_metadata=server_native.metadata)

            instance_data = HuaweiECSServerData(
                id=server_native.id,
                name=server_native.name,
                status=server_native.status,
                created=_parse_huawei_timestamp(server_native.created) if hasattr(server_native, 'created') else None,
                updated=_parse_huawei_timestamp(server_native.updated) if hasattr(server_native, 'updated') else None,
                user_id=getattr(server_native,'user_id', None),
                image=HuaweiECSImage(id=server_native.image.id) if hasattr(server_native, 'image') and server_native.image else None,
                flavor=HuaweiECSFlavor(id=server_native.flavor.id, name=getattr(server_native.flavor, 'name', None)) if hasattr(server_native, 'flavor') else {"id":"unknown_flavor"},
                addresses=server_native.addresses, # O schema Pydantic irá parsear
                key_name=getattr(server_native,'key_name', None),
                availability_zone=getattr(server_native,'os_ext_az_availability_zone', None),
                host_id=getattr(server_native,'os_ext_srv_attr_host', None),
                hypervisor_hostname=getattr(server_native,'os_ext_srv_attr_hypervisor_hostname', None),
                security_groups=sg_list_simple,
                volumes_attached=getattr(server_native,'os_extended_volumes_volumes_attached', None), # Lista de dicts {'id': 'uuid'}
                metadata=custom_meta,
                project_id=project_id,
                region_id=region_id,
                public_ips=public_ips,
                private_ips=private_ips,
                error_details="; ".join(error_msg_instance) if error_msg_instance else None
            )
            collected_instances.append(instance_data)

    except sdk_exceptions.SdkException as e:
        logger.error(f"Huawei SDK error listing ECS instances for project {project_id} in region {region_id}: Code: {e.error_code}, Msg: {e.error_message}")
        return [HuaweiECSServerData(id=f"ERROR_LIST_ECS_SDK_{region_id}", name=f"ERROR_LIST_ECS_SDK_{region_id}", status="ERROR", created=_parse_huawei_timestamp(datetime.now(timezone.utc).isoformat()), project_id=project_id, region_id=region_id, error_details=f"{e.error_code}: {e.error_message}", flavor={"id":"unknown"})]
    except Exception as e:
        logger.error(f"Unexpected error listing ECS instances for project {project_id} in region {region_id}: {e}", exc_info=True)
        return [HuaweiECSServerData(id=f"ERROR_LIST_ECS_UNEXPECTED_{region_id}", name=f"ERROR_LIST_ECS_UNEXPECTED_{region_id}", status="ERROR", created=_parse_huawei_timestamp(datetime.now(timezone.utc).isoformat()), project_id=project_id, region_id=region_id, error_details=str(e), flavor={"id":"unknown"})]

    logger.info(f"Collected {len(collected_instances)} Huawei ECS instances for project {project_id} in region {region_id}.")
    return collected_instances


async def get_huawei_vpc_security_groups(project_id: str, region_id: str) -> List[HuaweiVPCSecurityGroup]:
    """Coleta dados de Security Groups VPC para um projeto e região."""
    collected_sgs: List[HuaweiVPCSecurityGroup] = []
    try:
        vpc_client = get_vpc_client(region_id=region_id)
    except ValueError as ve: # Erro de credenciais
        logger.error(f"Credential error for Huawei VPC in region {region_id}: {ve}")
        return [HuaweiVPCSecurityGroup(id="ERROR_CREDENTIALS", name="ERROR_CREDENTIALS", project_id=project_id, region_id=region_id, error_details=str(ve))]
    except Exception as e:
        logger.error(f"Failed to initialize VPC client for region {region_id}: {e}")
        return [HuaweiVPCSecurityGroup(id=f"ERROR_CLIENT_INIT_{region_id}", name=f"ERROR_CLIENT_INIT_{region_id}", project_id=project_id, region_id=region_id, error_details=str(e))]

    try:
        # ListSecurityGroupsRequest pode ter 'project_id' se o cliente não for escopado por projeto.
        # No SDK Huawei, o project_id nas credenciais/cliente geralmente lida com isso.
        list_sg_request = ListSecurityGroupsRequest()
        # Adicionar filtros se necessário, ex: list_sg_request.vpc_id = "some-vpc-id"
        sg_response = vpc_client.list_security_groups(list_sg_request) # Bloqueante

        if not hasattr(sg_response, 'security_groups') or not sg_response.security_groups:
            logger.info(f"No VPC Security Groups found for project {project_id} in region {region_id}.")
            return []

        for sg_native in sg_response.security_groups:
            rules_data = []
            # As regras vêm em sg_native.security_group_rules
            if hasattr(sg_native, 'security_group_rules') and sg_native.security_group_rules:
                for rule_native in sg_native.security_group_rules:
                    rules_data.append(HuaweiVPCSecurityGroupRule(
                        id=rule_native.id,
                        description=getattr(rule_native, 'description', None),
                        security_group_id=rule_native.security_group_id,
                        direction=rule_native.direction,
                        ethertype=getattr(rule_native, 'ethertype', None),
                        protocol=getattr(rule_native, 'protocol', None),
                        port_range_min=getattr(rule_native, 'port_range_min', None),
                        port_range_max=getattr(rule_native, 'port_range_max', None),
                        remote_ip_prefix=getattr(rule_native, 'remote_ip_prefix', None),
                        remote_group_id=getattr(rule_native, 'remote_group_id', None)
                    ))

            sg_data = HuaweiVPCSecurityGroup(
                id=sg_native.id,
                name=sg_native.name,
                description=getattr(sg_native, 'description', None),
                project_id=sg_native.project_id, # O SG da API já tem project_id
                security_group_rules=rules_data,
                region_id=region_id # Adicionar a região da coleta
            )
            collected_sgs.append(sg_data)

    except sdk_exceptions.SdkException as e:
        logger.error(f"Huawei SDK error listing VPC SGs for project {project_id} in region {region_id}: Code: {e.error_code}, Msg: {e.error_message}")
        return [HuaweiVPCSecurityGroup(id=f"ERROR_LIST_SGS_SDK_{region_id}", name=f"ERROR_LIST_SGS_SDK_{region_id}", project_id=project_id, region_id=region_id, error_details=f"{e.error_code}: {e.error_message}")]
    except Exception as e:
        logger.error(f"Unexpected error listing VPC SGs for project {project_id} in region {region_id}: {e}", exc_info=True)
        return [HuaweiVPCSecurityGroup(id=f"ERROR_LIST_SGS_UNEXPECTED_{region_id}", name=f"ERROR_LIST_SGS_UNEXPECTED_{region_id}", project_id=project_id, region_id=region_id, error_details=str(e))]

    logger.info(f"Collected {len(collected_sgs)} Huawei VPC Security Groups for project {project_id} in region {region_id}.")
    return collected_sgs

# Nota: A coleta de regras de SG pode ser feita com ListSecurityGroupRulesRequest se não vierem com ListSecurityGroups.
# A API da Huawei `ListSecurityGroups` já inclui as `security_group_rules`.

# Ajustes e observações durante a implementação:
# *   A função `_parse_huawei_timestamp` foi adicionada para lidar com os formatos de data/hora da Huawei Cloud.
# *   O SDK da Huawei para ECS (`ListServersDetailsRequest`) e VPC (`ListSecurityGroupsRequest`) retorna os dados diretamente,
#     sem necessidade de paginação manual explícita nos exemplos básicos, mas pode ter parâmetros de `marker`/`limit` para grandes conjuntos de dados.
#     Os exemplos atuais não implementam essa paginação avançada.
# *   Os nomes dos campos no SDK da Huawei podem ser um pouco diferentes dos da AWS/GCP (ex: `OS-EXT-AZ:availability_zone`, `os-extended-volumes:volumes_attached`).
#     Os schemas Pydantic usam `alias` ou acesso via `getattr` para lidar com isso.
# *   A estrutura de `addresses` em ECS e `security_groups` em ECS é processada para extrair IPs e nomes de SG de forma simplificada.
# *   As chamadas ao SDK são bloqueantes. Para uso em FastAPI assíncrono, o ideal seria envolvê-las com `asyncio.to_thread`
#     ou similar para não bloquear o event loop. Isso foi omitido para simplicidade no MVP, mas é uma consideração importante para produção.
# *   O `project_id` é crucial. O `huawei_client_manager` obtém um `project_id` das credenciais,
#     e os coletores recebem `project_id` e `region_id` como parâmetros para garantir o escopo correto.
#
# Este arquivo estabelece a base para coletar dados de VMs e SGs da Huawei Cloud.
# Fim do arquivo.
