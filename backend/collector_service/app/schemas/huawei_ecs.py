from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- Schemas para Huawei Cloud ECS (Elastic Cloud Server) ---

class HuaweiECSAddress(BaseModel):
    version: Optional[int] = Field(None, description="Versão do IP (4 ou 6).")
    addr: Optional[str] = Field(None, description="Endereço IP.")
    mac_addr: Optional[str] = Field(None, alias="OS-EXT-IPS-MAC:mac_addr", description="Endereço MAC.")
    type: Optional[str] = Field(None, alias="OS-EXT-IPS:type", description="Tipo de IP (fixed, floating).")

    class Config:
        populate_by_name = True

class HuaweiECSImage(BaseModel):
    id: str
    # Links podem ser incluídos se necessário

class HuaweiECSFlavor(BaseModel):
    id: str # ID do flavor/tipo de instância
    name: Optional[str] = None # Nome do flavor
    # Outros detalhes do flavor como vcpus, ram, disk podem ser adicionados se coletados
    # Geralmente, o ID é suficiente para referência.

class HuaweiECSServerSchedulerHint(BaseModel): # OS-SCH-HNT:scheduler_hints
    group: Optional[str] = Field(None, description="ID do grupo de afinidade/anti-afinidade de VMs.")
    # Outros hints podem existir

class HuaweiECSServerMetadata(BaseModel): # Metadados customizados
    # Campos são definidos pelo usuário, então usamos Dict
    custom_metadata: Optional[Dict[str, str]] = Field(None)

class HuaweiECSServerData(BaseModel):
    id: str
    name: str
    status: str # Ex: ACTIVE, SHUTOFF, ERROR, BUILD
    created: datetime # Data de criação
    updated: Optional[datetime] = Field(None) # Data da última atualização

    # tenant_id: str = Field(alias="tenant_id", description="Project ID") # Já temos project_id no contexto da coleta
    user_id: Optional[str] = Field(None, alias="user_id", description="User ID do criador")

    image: Optional[HuaweiECSImage] = Field(None) # Pode ser apenas o ID ou um objeto
    flavor: HuaweiECSFlavor # Detalhes do tipo de instância

    addresses: Optional[Dict[str, List[HuaweiECSAddress]]] = Field(None, description="Dicionário de redes e seus IPs associados.")
    # Ex: "private_network_name": [{"version": 4, "addr": "192.168.1.5", ...}]

    key_name: Optional[str] = Field(None, alias="key_name", description="Nome do par de chaves SSH, se associado.")

    # "OS-EXT-AZ:availability_zone"
    availability_zone: Optional[str] = Field(None, alias="OS-EXT-AZ:availability_zone")

    # "OS-EXT-SRV-ATTR:host"
    host_id: Optional[str] = Field(None, alias="OS-EXT-SRV-ATTR:host", description="ID do host físico (se visível).")
    # "OS-EXT-SRV-ATTR:instance_name" (geralmente server.name)
    # "OS-EXT-SRV-ATTR:hypervisor_hostname"
    hypervisor_hostname: Optional[str] = Field(None, alias="OS-EXT-SRV-ATTR:hypervisor_hostname")

    # "OS-SRV-USG:launched_at"
    # "OS-SRV-USG:terminated_at"

    security_groups: Optional[List[Dict[str, str]]] = Field(None, description="Lista de SGs, ex: [{'name': 'sg-name-uuid'}]") # Vem como lista de dicts com 'name'

    # "os-extended-volumes:volumes_attached"
    volumes_attached: Optional[List[Dict[str, str]]] = Field(None, alias="os-extended-volumes:volumes_attached", description="Lista de volumes, ex: [{'id': 'volume-uuid'}]")

    metadata: Optional[HuaweiECSServerMetadata] = Field(None, description="Metadados customizados.") # Vem como dict

    # "scheduler_hints": Optional[HuaweiECSServerSchedulerHint] = Field(None, alias="OS-SCH-HNT:scheduler_hints") # Pode ser complexo

    # Adicionado pelo collector
    project_id: str
    region_id: str
    public_ips: List[str] = Field([])
    private_ips: List[str] = Field([])

    error_details: Optional[str] = Field(None)

    class Config:
        populate_by_name = True # Para lidar com aliases como "OS-EXT-AZ:availability_zone"
        # Pydantic V1: allow_population_by_field_name = True (se os nomes dos campos da API não baterem)


# --- Schemas para Huawei Cloud VPC Security Groups ---

class HuaweiVPCSecurityGroupRule(BaseModel):
    id: str
    description: Optional[str] = Field(None)
    security_group_id: str
    # project_id: str # Já no SG pai
    direction: str # ingress, egress
    ethertype: Optional[str] = Field(None, description="IPv4 ou IPv6. Default IPv4.")
    protocol: Optional[str] = Field(None, description="tcp, udp, icmp, ou número do protocolo. Null para qualquer.")
    port_range_min: Optional[int] = Field(None, alias="port_range_min")
    port_range_max: Optional[int] = Field(None, alias="port_range_max")
    remote_ip_prefix: Optional[str] = Field(None, alias="remote_ip_prefix", description="CIDR. Ex: 0.0.0.0/0")
    remote_group_id: Optional[str] = Field(None, alias="remote_group_id", description="ID de outro SG como origem/destino.")
    # Outros campos: remote_address_group_id, action (allow/deny - Huawei SGs são 'allow' por padrão), priority

    class Config:
        populate_by_name = True

class HuaweiVPCSecurityGroup(BaseModel):
    id: str
    name: str
    description: Optional[str] = Field(None)
    # project_id: str # Adicionado pelo collector
    # enterprise_project_id: Optional[str] = Field(None) # Se usando Enterprise Projects
    security_group_rules: List[HuaweiVPCSecurityGroupRule] = Field([])

    # Adicionado pelo collector
    project_id_from_collector: str = Field(alias="project_id") # Para evitar conflito se já houver project_id
    region_id: str

    error_details: Optional[str] = Field(None)

    class Config:
        populate_by_name = True # Para project_id_from_collector
        # Se o campo no JSON for `project_id`, e no Pydantic for `project_id_from_collector`,
        # o alias no Pydantic Field deve ser `project_id`.
        # Se o campo no JSON for `projectId`, e no Pydantic for `project_id`,
        # e `populate_by_name = True` (V2) ou `allow_population_by_field_name = True` (V1)
        # não for suficiente para camelCase -> snake_case, então alias é necessário.
        # Geralmente, Pydantic lida bem com snake_case no modelo e camelCase no JSON.
        # O alias é mais para quando os nomes são fundamentalmente diferentes.
        # Aqui, `project_id_from_collector` é o nome do campo Pydantic, e ele espera `project_id` do JSON.
        # Então `Field(alias="project_id")` está correto.
        pass
