import os
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcore.http.http_config import HttpConfig
from huaweicloudsdkiam.v3 import IamClient as IamClientV3
# Adicionar imports para outros clientes de serviço conforme necessário
from huaweicloudsdkobs.v1 import ObsClient
from huaweicloudsdkecs.v2 import EcsClient as EcsClientV2
from huaweicloudsdkvpc.v2 import VpcClient as VpcClientV2 # Para Security Groups e VPCs
# Para VPC v3 (se usado para subnets ou funcionalidades mais recentes)
# from huaweicloudsdkvpc.v3 import VpcClient as VpcClientV3


from app.core.config import settings # Para obter configurações globais se necessário
import logging

logger = logging.getLogger(__name__)

# Cache para os clientes
_clients_cache = {}

# --- Configuração de Credenciais e Região ---
# Estas podem vir de variáveis de ambiente ou de um arquivo de configuração seguro.
# Para o MVP, vamos priorizar variáveis de ambiente.

def get_huawei_credentials():
    """
    Obtém as credenciais AK/SK e Project ID da Huawei Cloud a partir de variáveis de ambiente.
    Retorna um objeto BasicCredentials e o project_id.
    """
    ak = os.getenv("HUAWEICLOUD_SDK_AK")
    sk = os.getenv("HUAWEICLOUD_SDK_SK")
    project_id = os.getenv("HUAWEICLOUD_SDK_PROJECT_ID")
    # Domain ID pode ser necessário para algumas APIs ou autenticação a nível de conta/domínio
    # domain_id = os.getenv("HUAWEICLOUD_SDK_DOMAIN_ID")

    if not all([ak, sk, project_id]):
        msg = "Credenciais Huawei Cloud (HUAWEICLOUD_SDK_AK, HUAWEICLOUD_SDK_SK, HUAWEICLOUD_SDK_PROJECT_ID) não estão configuradas."
        logger.error(msg)
        raise ValueError(msg)

    # O SDK pode requerer o project_id nas credenciais ou separadamente ao criar o cliente.
    # BasicCredentials geralmente toma ak, sk, e opcionalmente iam_endpoint ou domain_id/project_id.
    # Se o project_id for usado para escopo de recursos, ele é passado ao cliente do serviço.
    # O SDK da Huawei geralmente usa o project_id no construtor do cliente ou nas requisições.
    # Para BasicCredentials, o project_id pode não ser um parâmetro direto, mas sim domain_id.
    # No entanto, a maioria dos clientes de serviço (ECS, OBS, VPC) aceitam project_id.

    # Para autenticação global (ex: IAM a nível de domínio/conta), pode ser necessário domain_id.
    # Para serviços regionais escopados por projeto, project_id é crucial.
    # Vamos assumir que o project_id é o principal identificador de escopo para os serviços que coletaremos.

    credentials = BasicCredentials(ak, sk, project_id) # project_id aqui pode ser usado pelo SDK para alguns cenários
                                                       # ou pode precisar ser passado explicitamente para cada cliente.
                                                       # A documentação do SDK detalha isso.
                                                       # Algumas versões do SDK podem usar domain_id em vez de project_id aqui.
                                                       # Vamos focar em project_id para consistência com outros provedores.

    return credentials, project_id


def get_http_config() -> HttpConfig:
    """Retorna uma configuração HTTP padrão para os clientes SDK."""
    config = HttpConfig.get_default_config()
    # config.timeout = (10, 30) # connect_timeout, read_timeout
    # config.ignore_ssl_verification = False # Manter True apenas para debug extremo
    return config

# --- Getters de Cliente ---

def get_iam_client(region_id: str) -> IamClientV3:
    """Retorna um cliente para o Huawei Cloud IAM service."""
    client_key = f"iam_v3_{region_id}"
    if client_key not in _clients_cache:
        try:
            credentials, _ = get_huawei_credentials() # Project ID não é usado diretamente na credencial IAM global
            # IAM é um serviço global, mas o SDK pode esperar um endpoint ou uma região para construir o endpoint.
            # O endpoint do IAM pode ser diferente dos endpoints regionais de outros serviços.
            # Ex: iam.myhuaweicloud.com ou iam.region_id.myhuaweicloud.com
            # O SDK geralmente forma o endpoint a partir da região.
            # Se IAM for verdadeiramente global e não regional, a região pode ser um placeholder ou uma região "mestra".
            # Vamos assumir que a região é necessária para o SDK construir o endpoint.
            # É importante verificar na documentação do SDK qual o endpoint base para IAM.
            # Para IAM v3, o endpoint é geralmente global: iam.myhuaweicloud.com
            # O SDK pode lidar com isso se a região não for usada para formar o endpoint IAM.
            # Vamos passar a região, e o SDK core deve saber se a usa ou não para IAM.
            # O IAMClientV3 construtor aceita region_id.
            # O endpoint para IAM é geralmente global, mas o SDK pode usar region_id para selecionar um endpoint de acesso regional
            # ou um endpoint global padrão se a região não for relevante para o serviço IAM em si.
            # Exemplo de endpoint IAM: iam.myhuaweicloud.com (global) ou iam.ap-southeast-1.myhuaweicloud.com
            # O SDK deve lidar com a formação do endpoint correto com base na region_id.
            _clients_cache[client_key] = IamClientV3(credentials=credentials, http_config=get_http_config(), region_id=region_id)
            # O builder new_builder()...with_region_id().build() pode não ser o padrão para todos os clientes.
            # Alguns clientes são instanciados diretamente: Client(credentials, region_id, http_config)
            # Verificando a documentação do SDK para IamClientV3:
            # Geralmente é `IamClient.new_builder().with_credentials(cred).with_region_id(region).build()`
            # Ou `IamClient.new_builder().with_credentials(cred).with_endpoint("https_iam_endpoint").build()`
            # Se `with_region_id` não existe, o endpoint precisa ser construído manualmente ou o SDK tem outro método.
            # Testes anteriores mostraram `AttributeError: 'ClientBuilder' object has no attribute 'with_region_id'`
            # Vamos tentar construir o endpoint e usar with_endpoint, ou verificar se o construtor direto funciona.
            # O construtor direto IamClientV3(credentials, http_config, endpoint=endpoint_url) é uma opção.
            # Ou IamClientV3.new_builder().with_credentials(credentials).with_http_config(config).with_endpoint(endpoint).build()

            # Tentativa com endpoint explícito se with_region_id falhou nos testes anteriores:
            # iam_endpoint = f"https://iam.{region_id}.myhuaweicloud.com" # Ou iam.myhuaweicloud.com se global
            # _clients_cache[client_key] = (IamClientV3.new_builder()
            #     .with_credentials(credentials)
            #     .with_http_config(get_http_config())
            #     .with_endpoint(iam_endpoint)
            #     .build())
            # Vou manter o with_region_id por enquanto, pois o erro anterior era no ECS/VPC, não IAM.
            # Se o erro persistir para IAM, precisará ser ajustado.
            # O erro "'ClientBuilder' object has no attribute 'with_region_id'" foi nos testes,
            # o que sugere que o new_builder() para alguns clientes pode não ter esse método.

            # Revertendo para o padrão do SDK que usa region_id no construtor se o builder não funcionar universalmente
            # Se o construtor direto não funcionar, voltaremos ao builder com with_endpoint.
            # A documentação do SDK mostra que IamClientV3.new_builder() existe.
            # O erro anterior era no ECS, não IAM.
            _clients_cache[client_key] = (IamClientV3.new_builder()
                             .with_credentials(credentials)
                             .with_http_config(get_http_config())
                             .with_region_id(region_id) # Esta é a forma correta para IAMv3 builder
                             .build())
            logger.info(f"Huawei Cloud IAM v3 client initialized for region/endpoint context '{region_id}'.")
        except Exception as e:
            logger.error(f"Failed to initialize Huawei Cloud IAM v3 client for region {region_id}: {e}")
            raise
    return _clients_cache[client_key]


def get_obs_client(region_id: str) -> ObsClient:
    """Retorna um cliente para o Huawei Cloud OBS service."""
    client_key = f"obs_v1_{region_id}"
    if client_key not in _clients_cache:
        try:
            credentials, project_id_from_creds = get_huawei_credentials()
            # OBS endpoints são regionais, ex: obs.us-east-1.myhuaweicloud.com
            # O SDK deve construir isso a partir da region_id.
            # O project_id pode ser necessário para algumas operações OBS se não estiver implícito nas credenciais.
            # No SDK Python do OBS, o endpoint é crucial.
            # A classe ObsClient pode requerer ak, sk, server (endpoint), e opcionalmente project_id.

            # O construtor do ObsClient é: ObsClient(access_key_id, secret_access_key, server, signature='obs', region=None, ...)
            # O 'server' é o endpoint. Ex: "obs.sa-brazil-1.myhuaweicloud.com"
            # Precisamos construir este endpoint.
            obs_endpoint = f"obs.{region_id}.myhuaweicloud.com"

            _clients_cache[client_key] = ObsClient(
                access_key_id=credentials.ak,
                secret_access_key=credentials.sk,
                server=f"https://{obs_endpoint}" # Precisa de https://
                # project_id=project_id_from_creds # project_id pode ser inferido ou não necessário para todas as ops
                # region=region_id # Opcional se o endpoint já for específico da região
            )
            logger.info(f"Huawei Cloud OBS client initialized for region '{region_id}' (endpoint: {obs_endpoint}).")
        except Exception as e:
            logger.error(f"Failed to initialize Huawei Cloud OBS client for region {region_id}: {e}")
            raise
    return _clients_cache[client_key]

def get_ecs_client(region_id: str) -> EcsClientV2:
    """Retorna um cliente para o Huawei Cloud ECS service."""
    client_key = f"ecs_v2_{region_id}"
    if client_key not in _clients_cache:
        try:
            credentials, project_id_from_creds = get_huawei_credentials()
            # ECS é regional. O SDK usa region_id para formar o endpoint.
            # O project_id é passado nas credenciais ou explicitamente.
            # EcsClientV2 também usa o padrão builder
            _clients_cache[client_key] = (EcsClientV2.new_builder()
                .with_credentials(credentials)
                .with_http_config(get_http_config())
                .with_region_id(region_id)
                .build())
            # Note: O SDK pode precisar do project_id explicitamente em algumas chamadas de request,
            # mesmo que esteja nas credenciais, para escopo correto.
            logger.info(f"Huawei Cloud ECS v2 client initialized for region '{region_id}'.")
        except Exception as e:
            logger.error(f"Failed to initialize Huawei Cloud ECS v2 client for region {region_id}: {e}")
            raise
    return _clients_cache[client_key]

def get_vpc_client(region_id: str) -> VpcClientV2:
    """Retorna um cliente para o Huawei Cloud VPC service (v2)."""
    client_key = f"vpc_v2_{region_id}"
    if client_key not in _clients_cache:
        try:
            credentials, project_id_from_creds = get_huawei_credentials()
            # VpcClientV2 também usa o padrão builder
            _clients_cache[client_key] = (VpcClientV2.new_builder()
                .with_credentials(credentials)
                .with_http_config(get_http_config())
                .with_region_id(region_id)
                .build())
            logger.info(f"Huawei Cloud VPC v2 client initialized for region '{region_id}'.")
        except Exception as e:
            logger.error(f"Failed to initialize Huawei Cloud VPC v2 client for region {region_id}: {e}")
            raise
    return _clients_cache[client_key]

# Adicionar mais getters de cliente para outros serviços conforme necessário.

if __name__ == '__main__':
    # Teste rápido de inicialização (requer variáveis de ambiente Huawei Cloud setadas)
    # Ex: HUAWEICLOUD_SDK_AK, HUAWEICLOUD_SDK_SK, HUAWEICLOUD_SDK_PROJECT_ID
    # E uma região válida, ex: "cn-north-4" ou "ap-southeast-1"
    test_region = os.getenv("HUAWEICLOUD_SDK_TEST_REGION", "ap-southeast-3") # Exemplo de região
    print(f"Attempting to initialize Huawei Cloud clients for region: {test_region}")

    try:
        creds, proj_id = get_huawei_credentials()
        print(f"Credentials loaded: AK='{creds.ak[:5]}...', ProjectID='{proj_id}'")

        iam_cli = get_iam_client(region_id=test_region) # IAM pode precisar de um endpoint global ou específico
        print(f"IAM Client: {type(iam_cli)}")

        obs_cli = get_obs_client(region_id=test_region)
        print(f"OBS Client: {type(obs_cli)}")

        ecs_cli = get_ecs_client(region_id=test_region)
        print(f"ECS Client: {type(ecs_cli)}")

        vpc_cli = get_vpc_client(region_id=test_region)
        print(f"VPC Client: {type(vpc_cli)}")

        print("All Huawei Cloud clients seem to initialize (superficially).")

    except ValueError as ve:
        print(f"Configuration Error: {ve}")
    except Exception as e:
        print(f"Error during client initialization test: {e}")

# Exemplo de como obter todas as regiões disponíveis para um serviço (ex: ECS)
# Isto pode ser útil para os coletores iterarem sobre todas as regiões.
# requer um cliente já inicializado para uma região qualquer.
# from huaweicloudsdkecs.v2.model import ListFlavorsRequest # Exemplo, não é para regiões
# from huaweicloudsdkcore.exceptions import exceptions
#
# def get_available_ecs_regions(initial_region: str = "ap-southeast-1"):
#     try:
#         iam_client = get_iam_client(region_id=initial_region) # IAM client para listar regiões
#         # A API para listar regiões pode estar no IAM ou em um serviço de gerenciamento de endpoint.
#         # Exemplo (pode não ser a chamada correta, precisa verificar documentação):
#         # request = ListAvailableZonesRequest() # Ou algo como ListRegionsRequest
#         # response = ecs_client.list_available_zones(request)
#         # regions = [az.region_id for az in response.availability_zone_info]
#         # return list(set(regions)) # Lista única de IDs de região
#         #
#         # Para Huawei, a lista de regiões é geralmente conhecida e pode ser obtida da documentação
#         # ou de um endpoint de metadados, se existir.
#         # O SDK pode ter uma forma de listar endpoints/regiões.
#         # Exemplo: client.get_ регион_endpoints()
#         #
#         # Se não houver uma API programática fácil, pode ser necessário manter uma lista estática
#         # de regiões suportadas pela Huawei Cloud e iterar sobre ela.
#         # https://developer.huaweicloud.com/intl/en-us/endpoint
#
#         # Placeholder:
#         logger.warning("Programmatic discovery of all Huawei Cloud regions not yet implemented in client manager.")
#         logger.warning("Returning a default list. Update with actual regions or programmatic discovery.")
#         return ["ap-southeast-3", "ap-southeast-1", "cn-north-4", "eu-west-0"] # Exemplo
# #     except Exception as e:
# #         logger.error(f"Could not retrieve available ECS regions: {e}")
# #         return []
# Fim do arquivo.
