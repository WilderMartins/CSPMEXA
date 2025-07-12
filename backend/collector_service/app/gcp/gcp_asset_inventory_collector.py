import logging
from typing import List, Optional, Dict, Any
import datetime
import re

from google.cloud import asset_v1
from google.auth.exceptions import DefaultCredentialsError
from google.api_core.exceptions import GoogleAPIError, InvalidArgument

from app.schemas.gcp.gcp_cai_schemas import GCPAsset, GCPAssetCollection
from app.gcp.gcp_utils import get_gcp_project_id # Para obter o projeto padrão se o escopo não for um projeto

logger = logging.getLogger(__name__)

def _extract_project_id_from_asset_name(asset_name: str) -> Optional[str]:
    # Ex: "//compute.googleapis.com/projects/my-project-id/zones/us-central1-a/instances/my-instance"
    # Ex: "//cloudresourcemanager.googleapis.com/projects/123456789"
    match = re.search(r"projects/([^/]+)", asset_name)
    if match:
        return match.group(1)
    return None

def _extract_location_from_asset_name(asset_name: str) -> Optional[str]:
    # Tenta extrair localizações comuns como zones, regions
    # Ex: "//compute.googleapis.com/projects/p/zones/us-central1-a/instances/i" -> us-central1-a
    # Ex: "//storage.googleapis.com/projects/p/buckets/b" (buckets têm 'location' no resource.data)
    # Ex: "//sql.googleapis.com/projects/p/instances/i" (instances SQL têm 'region' no resource.data)

    # Para compute instances (zones)
    match_zone = re.search(r"/zones/([^/]+)", asset_name)
    if match_zone:
        return match_zone.group(1)

    # Para compute disks, images etc (pode ser regional ou zonal)
    match_region_compute = re.search(r"/regions/([^/]+)", asset_name)
    if match_region_compute:
        return match_region_compute.group(1)

    # Outros tipos de recursos podem ter 'location' ou 'region' em resource.data
    return None


def _convert_sdk_asset_to_schema(sdk_asset: asset_v1.types.Asset) -> Optional[GCPAsset]:
    if not sdk_asset:
        return None

    try:
        project_id = _extract_project_id_from_asset_name(sdk_asset.name)
        location = _extract_location_from_asset_name(sdk_asset.name)

        resource_data_dict = None
        if sdk_asset.resource and hasattr(sdk_asset.resource, "data") and sdk_asset.resource.data:
            # resource.data é um Struct, converter para dict
            try:
                resource_data_dict = dict(sdk_asset.resource.data)
                if not location and "location" in resource_data_dict: # Ex: Buckets GCS
                    location = resource_data_dict.get("location")
                elif not location and "region" in resource_data_dict: # Ex: Instâncias SQL
                     # O SDK pode retornar a URL completa da região, ex: "projects/p/regions/us-central1"
                    region_url = resource_data_dict.get("region")
                    if region_url and isinstance(region_url, str) and "/regions/" in region_url:
                        location = region_url.split("/regions/")[-1]
                    else:
                        location = region_url

            except Exception as e_struct:
                logger.warning(f"Could not fully parse asset resource.data for {sdk_asset.name}: {e_struct}")
                resource_data_dict = {"error_parsing_resource_data": str(e_struct)}

        iam_policy_dict = None
        if sdk_asset.iam_policy:
            # iam_policy é um google.iam.v1.policy_pb2.Policy, converter para dict
            try:
                # Uma forma simples é criar um dict com bindings. Para uma conversão completa,
                # seria necessário iterar sobre os campos do objeto Policy.
                iam_policy_dict = {"bindings": []}
                for binding in sdk_asset.iam_policy.bindings:
                    iam_policy_dict["bindings"].append({"role": binding.role, "members": list(binding.members)})
                # Adicionar etag e version se necessário
            except Exception as e_iam:
                logger.warning(f"Could not fully parse asset iam_policy for {sdk_asset.name}: {e_iam}")
                iam_policy_dict = {"error_parsing_iam_policy": str(e_iam)}

        display_name_val = None
        if resource_data_dict and isinstance(resource_data_dict, dict):
            display_name_val = resource_data_dict.get("displayName", resource_data_dict.get("name"))


        return GCPAsset(
            name=sdk_asset.name,
            assetType=sdk_asset.asset_type,
            resource=resource_data_dict,
            iamPolicy=iam_policy_dict,
            project_id=project_id,
            location=location,
            display_name=display_name_val,
            # create_time e update_time podem não estar no Asset principal, mas no resource.data para alguns tipos
            createTime=resource_data_dict.get("createTime") if resource_data_dict else None, # Exemplo, pode variar
            updateTime=resource_data_dict.get("updateTime") if resource_data_dict else None, # Exemplo, pode variar
        )
    except Exception as e:
        logger.error(f"Error converting SDK GCP Asset object to schema for asset '{getattr(sdk_asset, 'name', 'UNKNOWN_ASSET')}': {e}", exc_info=True)
        return GCPAsset(
            name=getattr(sdk_asset, 'name', f'CONVERSION_ERROR_NAME_{uuid.uuid4()}'),
            assetType=getattr(sdk_asset, 'asset_type', 'UnknownAssetType'),
            collection_error_details=f"Failed to parse SDK GCP Asset object: {str(e)}"
        )

def get_gcp_cloud_assets(
    scope: str, # "projects/{PROJECT_ID}" ou "folders/{FOLDER_ID}" ou "organizations/{ORGANIZATION_ID}"
    asset_types: Optional[List[str]] = None, # Lista de tipos de ativos a serem retornados
    content_type: str = "RESOURCE", # RESOURCE, IAM_POLICY, ORG_POLICY, ACCESS_POLICY
    max_results_per_call: int = 1000, # A API CAI suporta até 1000
    max_total_results: int = 10000,
) -> GCPAssetCollection:
    """
    Coleta ativos do GCP Cloud Asset Inventory para um escopo específico.
    Requer permissão: cloudasset.assets.listResource (ou similar dependendo do content_type)
    """
    all_assets_schemas: List[GCPAsset] = []
    page_token: Optional[str] = None
    collected_count = 0

    try:
        credentials, _ = google.auth.default()
        asset_client = asset_v1.AssetServiceClient(credentials=credentials)

        content_type_enum = asset_v1.types.ContentType.RESOURCE # Default
        if content_type.upper() == "IAM_POLICY":
            content_type_enum = asset_v1.types.ContentType.IAM_POLICY
        elif content_type.upper() == "ORG_POLICY":
            content_type_enum = asset_v1.types.ContentType.ORG_POLICY
        elif content_type.upper() == "ACCESS_POLICY":
            content_type_enum = asset_v1.types.ContentType.ACCESS_POLICY

        logger.info(f"Fetching GCP Cloud Assets for scope: {scope}, asset_types: {asset_types or 'Any'}, content_type: {content_type}")

        while collected_count < max_total_results:
            current_limit = min(max_results_per_call, max_total_results - collected_count)
            if current_limit <= 0: break

            request = asset_v1.types.ListAssetsRequest(
                parent=scope,
                asset_types=asset_types or [], # Lista vazia significa todos os tipos para o content_type
                content_type=content_type_enum,
                page_size=current_limit,
                page_token=page_token
                # read_time pode ser usado para obter dados de um ponto específico no tempo
            )

            # Chamada síncrona ao SDK. O controller usará run_in_threadpool.
            response_pager = asset_client.list_assets(request=request)

            page_assets = []
            for asset in response_pager: # O pager itera sobre os ativos diretamente
                page_assets.append(asset)
                schema_asset = _convert_sdk_asset_to_schema(asset)
                if schema_asset:
                    all_assets_schemas.append(schema_asset)

            collected_count += len(page_assets)
            page_token = response_pager.next_page_token # O pager tem next_page_token

            if not page_token or collected_count >= max_total_results:
                break

        # read_time pode não estar diretamente no pager, mas pode ser pego da primeira resposta se necessário.
        # Por enquanto, não vamos preenchê-lo no schema da coleção.
        logger.info(f"Collected {collected_count} GCP Cloud Assets for scope '{scope}'.")
        return GCPAssetCollection(
            assets=all_assets_schemas,
            next_page_token=page_token,
            scope_queried=scope,
            asset_types_queried=asset_types,
            content_type_queried=content_type
        )

    except DefaultCredentialsError:
        msg = "GCP default credentials not found for Cloud Asset Inventory collector."
        logger.error(msg)
        return GCPAssetCollection(error_message=msg, scope_queried=scope)
    except InvalidArgument as e: # Se o escopo ou asset_types forem inválidos
        logger.error(f"Invalid argument for Cloud Asset Inventory for scope '{scope}': {e}", exc_info=True)
        return GCPAssetCollection(error_message=f"Invalid argument: {str(e)}", scope_queried=scope)
    except GoogleAPIError as e:
        logger.error(f"Google API Error collecting Cloud Assets for scope '{scope}': {e}", exc_info=True)
        return GCPAssetCollection(error_message=f"Google API Error: {str(e)}", scope_queried=scope)
    except Exception as e:
        logger.error(f"Unexpected error collecting Cloud Assets for scope '{scope}': {e}", exc_info=True)
        return GCPAssetCollection(error_message=f"Unexpected error: {str(e)}", scope_queried=scope)

if __name__ == "__main__":
    # Teste local (requer credenciais GCP e Cloud Asset API habilitada)
    # import asyncio # Não necessário pois o coletor é síncrono
    # def run_cai_test():
    #     # Configurar GOOGLE_APPLICATION_CREDENTIALS
    #     test_scope_project = f"projects/{get_gcp_project_id()}" # Usa o projeto default das credenciais
    #     # test_scope_org = "organizations/YOUR_ORG_ID"

    #     if not get_gcp_project_id():
    #          print("Pulando teste local do coletor CAI: GOOGLE_APPLICATION_CREDENTIALS não configurado ou sem projeto default.")
    #          return

    #     print(f"Testando coletor Cloud Asset Inventory para escopo {test_scope_project}...")
    #     asset_collection = get_gcp_cloud_assets(
    #         scope=test_scope_project,
    #         asset_types=["compute.googleapis.com/Instance", "storage.googleapis.com/Bucket"],
    #         content_type="RESOURCE",
    #         max_total_results=10
    #     )

    #     if asset_collection.error_message:
    #         print(f"Erro na coleta: {asset_collection.error_message}")
    #     else:
    #         print(f"Coletados {len(asset_collection.assets)} ativos.")
    #         for asset in asset_collection.assets:
    #             print(f"  Ativo: {asset.name}, Tipo: {asset.asset_type}, Projeto: {asset.project_id}, Local: {asset.location}")
    #             # print(asset.model_dump_json(indent=2, by_alias=True))
    #         if asset_collection.next_page_token:
    #             print(f"  Próximo token de página: {asset_collection.next_page_token}")

    # run_cai_test()
    print("Coletor GCP Cloud Asset Inventory (estrutura) criado. Adapte com chamadas reais ao SDK e documentação.")

```
