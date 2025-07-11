import asyncio
from typing import List, Optional, Tuple
from googleapiclient.errors import HttpError
from app.google_workspace.google_workspace_client_manager import get_workspace_service
from app.schemas.google_workspace.google_drive_shared_drive import (
    SharedDriveData, DriveRestrictions, SharedDriveCapabilities, SharedDriveListResponse
)
from app.schemas.google_workspace.google_drive_file import (
    DriveFileData, DriveFileOwner, DriveFileListResponse
)
from app.schemas.google_workspace.google_drive_permission import DrivePermission
from app.core.config import settings
from app.google_workspace.user_collector import _parse_iso_datetime # Reutilizar parser de data
import logging

logger = logging.getLogger(__name__)

# Campos a serem solicitados para Drives Compartilhados
SHARED_DRIVE_FIELDS = "nextPageToken, drives(id, name, createdTime, restrictions, capabilities)"
# Campos para arquivos dentro de Drives Compartilhados (e para arquivos públicos em geral)
# Incluir 'permissions' aqui pode ser pesado; melhor buscar permissões separadamente por arquivo.
# 'shared' e 'ownedByMe' são úteis. 'owners' também.
FILE_FIELDS_BASIC = "id, name, mimeType, owners(displayName,emailAddress), shared, webViewLink, driveId, modifiedTime, createdTime"
# Campos para permissões de um arquivo
PERMISSION_FIELDS = "permissions(id,type,role,emailAddress,domain,allowFileDiscovery,displayName,deleted)"


async def _get_file_permissions(
    drive_service: any, file_id: str
) -> Tuple[List[DrivePermission], Optional[str]]:
    """Busca e parseia as permissões de um arquivo específico."""
    permissions_list: List[DrivePermission] = []
    error_msg: Optional[str] = None
    page_token: Optional[str] = None
    try:
        while True:
            request = drive_service.permissions().list(
                fileId=file_id,
                fields=f"nextPageToken, {PERMISSION_FIELDS}", # PERMISSION_FIELDS já contém 'permissions(...)'
                pageSize=100, # Max para permissions.list
                pageToken=page_token,
                supportsAllDrives=True
            )
            response = await asyncio.to_thread(request.execute)

            native_permissions = response.get('permissions', [])
            for perm_native in native_permissions:
                permissions_list.append(DrivePermission(
                    id=perm_native.get('id'),
                    type=perm_native.get('type'),
                    role=perm_native.get('role'),
                    emailAddress=perm_native.get('emailAddress'),
                    domain=perm_native.get('domain'),
                    allowFileDiscovery=perm_native.get('allowFileDiscovery'),
                    deleted=perm_native.get('deleted', False), # Default False se não presente
                    displayName=perm_native.get('displayName')
                ))
            page_token = response.get('nextPageToken')
            if not page_token:
                break
    except HttpError as e_perm:
        error_msg = f"HTTP error fetching permissions for file {file_id}: {e_perm.resp.status} {e_perm._get_reason()}"
        logger.warning(error_msg)
    except Exception as e_perm_other:
        error_msg = f"Unexpected error fetching permissions for file {file_id}: {str(e_perm_other)}"
        logger.warning(error_msg)
    return permissions_list, error_msg


async def _analyze_file_sharing(
    file_data: DriveFileData, # Passar o objeto já parcialmente populado
    permissions_list: List[DrivePermission]
):
    """Analisa as permissões de um arquivo e atualiza os campos de compartilhamento no DriveFileData."""
    file_data.is_public_on_web = False
    file_data.is_shared_with_link = False
    file_data.is_shared_externally_direct = False
    file_data.is_shared_with_domain = False
    file_data.sharing_summary = []

    for perm in permissions_list:
        if perm.deleted: continue # Ignorar permissões deletadas

        if perm.type == "anyone":
            if perm.role in ["reader", "writer", "commenter"]: # Adicionar outros roles se relevante
                if perm.allow_file_discovery is True: # Ou se allowFileDiscovery não for False (default pode ser True)
                    file_data.is_public_on_web = True
                    file_data.sharing_summary.append(f"Public on the web ({perm.role})")
                else: # allowFileDiscovery é False ou None (default para anyoneWithLink)
                    file_data.is_shared_with_link = True
                    file_data.sharing_summary.append(f"Anyone with the link ({perm.role})")

        elif perm.type == "domain":
            file_data.is_shared_with_domain = True
            detail = f"Shared with domain '{perm.domain}' as {perm.role}"
            if perm.allow_file_discovery: detail += " (discoverable)"
            file_data.sharing_summary.append(detail)
            # Considerar se o domínio é o primário ou externo (requer info do domínio primário)

        elif perm.type == "user" or perm.type == "group":
            # Heurística simples para compartilhamento externo: se tem emailAddress e não é do domínio principal.
            # Isso requer conhecer o(s) domínio(s) principal(is) da organização.
            # Para MVP, podemos pular a detecção precisa de "externo" ou assumir um domínio principal.
            # Por agora, apenas registramos que há compartilhamentos diretos.
            # if perm.email_address and not perm.email_address.endswith(f"@{PRIMARY_DOMAIN}"):
            #     file_data.is_shared_externally_direct = True
            #     file_data.sharing_summary.append(f"Shared directly with {perm.type} {perm.email_address or perm.display_name} ({perm.role})")
            pass # Lógica de compartilhamento externo direto pode ser adicionada aqui

    if not file_data.sharing_summary and file_data.shared: # Se 'shared' é True mas nenhuma permissão "larga" foi encontrada
        file_data.sharing_summary.append("Shared with specific users/groups.")


async def get_google_drive_shared_drives_data(
    customer_id: Optional[str] = None,
    delegated_admin_email: Optional[str] = None,
    max_results_drives: int = 100,
    max_results_files_per_drive: int = 100 # Limite para arquivos por Drive Compartilhado
) -> List[SharedDriveData]:
    """Coleta dados de Drives Compartilhados e arquivos problematicamente compartilhados dentro deles."""
    shared_drives_list: List[SharedDriveData] = []
    error_msg_global: Optional[str] = None

    try:
        drive_service = get_workspace_service(
            service_name='drive', service_version='v3',
            delegated_admin_email=delegated_admin_email,
            scopes=["https://www.googleapis.com/auth/drive.readonly"] # Escopo específico
        )
        if not drive_service:
            logger.error("Falha ao inicializar o serviço Google Drive.")
            # Retornar uma lista com um item de erro pode ser uma opção
            return [SharedDriveData(id="ERROR_SERVICE_INIT", name="Service Init Error", error_details="Failed to init Drive service")]

        page_token_drives: Optional[str] = None
        while True:
            request_drives = drive_service.drives().list(
                useDomainAdminAccess=True, # Essencial para ver todos os drives como admin
                fields=SHARED_DRIVE_FIELDS,
                pageSize=max_results_drives,
                pageToken=page_token_drives
            )
            response_drives = await asyncio.to_thread(request_drives.execute)

            for drive_native in response_drives.get('drives', []):
                drive_id = drive_native.get('id')
                drive_name = drive_native.get('name')
                logger.info(f"Processando Drive Compartilhado: {drive_name} ({drive_id})")

                restrictions_data = None
                if drive_native.get('restrictions'):
                    restrictions_data = DriveRestrictions.model_validate(drive_native.get('restrictions'))

                capabilities_data = None
                if drive_native.get('capabilities'):
                    capabilities_data = SharedDriveCapabilities.model_validate(drive_native.get('capabilities'))

                shared_drive_obj = SharedDriveData(
                    id=drive_id,
                    name=drive_name,
                    created_time=_parse_iso_datetime(drive_native.get('createdTime')),
                    restrictions=restrictions_data,
                    capabilities=capabilities_data,
                    files_with_problematic_sharing=[] # Será preenchido abaixo
                )

                # Listar arquivos dentro deste Drive Compartilhado
                page_token_files: Optional[str] = None
                files_in_drive_count = 0
                try:
                    while True:
                        request_files = drive_service.files().list(
                            driveId=drive_id,
                            corpora="drive", # Buscar apenas neste Drive Compartilhado
                            supportsAllDrives=True,
                            includeItemsFromAllDrives=True, # Necessário para `driveId`
                            fields=f"nextPageToken, files({FILE_FIELDS_BASIC})", # Pedir campos básicos
                            pageSize=max_results_files_per_drive,
                            pageToken=page_token_files
                        )
                        response_files = await asyncio.to_thread(request_files.execute)

                        for file_native in response_files.get('files', []):
                            files_in_drive_count += 1
                            file_id = file_native.get('id')

                            owners_data = [DriveFileOwner.model_validate(owner) for owner in file_native.get('owners', [])]

                            file_data_obj = DriveFileData(
                                id=file_id,
                                name=file_native.get('name'),
                                mimeType=file_native.get('mimeType'),
                                owners=owners_data,
                                shared=file_native.get('shared', False),
                                webViewLink=file_native.get('webViewLink'),
                                drive_id=file_native.get('driveId'), # Deve ser o mesmo que drive_id
                                modified_time=_parse_iso_datetime(file_native.get('modifiedTime')),
                                created_time=_parse_iso_datetime(file_native.get('createdTime')),
                                # permissions_list será preenchido abaixo
                            )

                            # Obter e analisar permissões para este arquivo
                            perms, perm_error = await _get_file_permissions(drive_service, file_id)
                            if perm_error:
                                file_data_obj.error_details = (file_data_obj.error_details + "; " if file_data_obj.error_details else "") + perm_error

                            file_data_obj.permissions_list = perms
                            await _analyze_file_sharing(file_data_obj, perms)

                            if file_data_obj.is_public_on_web or file_data_obj.is_shared_with_link:
                                shared_drive_obj.files_with_problematic_sharing.append(file_data_obj)

                        page_token_files = response_files.get('nextPageToken')
                        if not page_token_files:
                            break
                    logger.info(f"Analisados {files_in_drive_count} arquivos em {drive_name}.")
                except Exception as e_files:
                    err_msg_drive = f"Erro ao listar/processar arquivos no Drive Compartilhado {drive_name}: {str(e_files)}"
                    logger.error(err_msg_drive, exc_info=True)
                    shared_drive_obj.error_details = (shared_drive_obj.error_details + "; " if shared_drive_obj.error_details else "") + err_msg_drive

                shared_drives_list.append(shared_drive_obj)

            page_token_drives = response_drives.get('nextPageToken')
            if not page_token_drives:
                break

    except HttpError as e:
        error_msg_global = f"Erro HTTP da API Google Drive ao listar Drives Compartilhados: {e.resp.status} {e._get_reason()}"
        logger.error(error_msg_global, exc_info=True)
        if not shared_drives_list: # Se nenhum drive foi processado antes do erro
            return [SharedDriveData(id="ERROR_HTTP", name="HTTP Error", error_details=error_msg_global)]
    except Exception as e:
        error_msg_global = f"Erro inesperado ao coletar Drives Compartilhados: {str(e)}"
        logger.error(error_msg_global, exc_info=True)
        if not shared_drives_list:
            return [SharedDriveData(id="ERROR_UNEXPECTED", name="Unexpected Error", error_details=error_msg_global)]

    if error_msg_global and shared_drives_list: # Se houve erro mas alguns drives foram processados
        # Adicionar um item de erro no final pode ser uma opção, ou logar é suficiente.
        logger.warning(f"Coleta de Drives Compartilhados concluída com erro global: {error_msg_global}")

    logger.info(f"Coletados {len(shared_drives_list)} Drives Compartilhados.")
    return shared_drives_list


async def get_google_drive_public_files_data(
    customer_id: Optional[str] = None, # Para escopo de busca, se necessário
    delegated_admin_email: Optional[str] = None,
    max_results_files: int = 1000 # Limite para a busca de arquivos públicos
) -> List[DriveFileData]:
    """
    Coleta dados de arquivos no Google Drive que são compartilhados publicamente ou com "qualquer pessoa com o link".
    Esta função é mais complexa e potencialmente demorada, pois pode envolver a varredura de muitos arquivos.
    MVP: Focar em arquivos em Drives Compartilhados (já coberto acima) ou arquivos pertencentes a usuários específicos.
    Para uma busca em todo o domínio, o `corpora='domain'` com `q` apropriado seria usado.
    """
    publicly_exposed_files: List[DriveFileData] = []
    error_msg_global: Optional[str] = None

    try:
        drive_service = get_workspace_service(
            service_name='drive', service_version='v3',
            delegated_admin_email=delegated_admin_email,
            scopes=["https://www.googleapis.com/auth/drive.readonly"]
        )
        if not drive_service:
            logger.error("Falha ao inicializar o serviço Google Drive para arquivos públicos.")
            return [DriveFileData(id="ERROR_SERVICE_INIT", name="Service Init Error", mime_type="error", error_details="Failed to init Drive service")]

        # Estratégia de busca:
        # 1. Usar `files.list` com `corpora="allDrives"` (ou "domain" se preferir) para buscar em todos os locais.
        # 2. O parâmetro `q` para filtrar por permissões `type='anyone'` é o desafio.
        #    A documentação diz: "You can't yet use the permissions collection to filter search results."
        #    Isso significa que não podemos fazer `q="permissions.type = 'anyone'"`.
        #    Portanto, teremos que listar arquivos (talvez com outros filtros, ex: `not mimeType = 'application/vnd.google-apps.folder'`)
        #    e depois, para cada arquivo, chamar `permissions.list` e analisar.
        #    Isso pode ser muito demorado para um domínio inteiro.
        #
        #    Alternativa: Usar a API Reports (Admin SDK) para eventos de Drive?
        #    `admin.reports().activities().list(userKey='all', applicationName='drive', eventName='change_user_access')`
        #    Isso daria eventos de alteração de permissão, mas não o estado atual de todos os arquivos.
        #
        #    Para MVP, a coleta de arquivos problemáticos já está integrada na função `get_google_drive_shared_drives_data`
        #    para arquivos DENTRO de Drives Compartilhados.
        #    Uma função separada para "todos os arquivos públicos no domínio" é um desafio de escopo/performance.
        #
        #    Vamos simplificar esta função no MVP para retornar uma mensagem de que esta coleta específica
        #    é complexa e coberta parcialmente pela análise de Drives Compartilhados.

        logger.info("A coleta de *todos* os arquivos públicos/link-shared em um domínio é uma operação extensa e não implementada de forma otimizada neste MVP. Arquivos problemáticos dentro de Drives Compartilhados são analisados em `get_google_drive_shared_drives_data`.")
        error_msg_global = "Coleta de todos os arquivos públicos do domínio não implementada otimamente no MVP."
        # Retornar uma lista vazia ou um item de erro informativo.
        return [DriveFileData(id="INFO_DOMAIN_WIDE_PUBLIC_FILES", name="Domain-wide Public File Scan", mime_type="info", error_details=error_msg_global, shared=False)]

    except Exception as e:
        error_msg_global = f"Erro inesperado ao tentar planejar coleta de arquivos públicos: {str(e)}"
        logger.error(error_msg_global, exc_info=True)
        return [DriveFileData(id="ERROR_UNEXPECTED_PUBLIC_FILES", name="Error Public Files", mime_type="error", error_details=error_msg_global, shared=False)]

    # Se fosse implementar a busca real:
    # page_token_files: Optional[str] = None
    # while True:
    #     request_files = drive_service.files().list(
    #         corpora="allDrives", # Ou "domain"
    #         supportsAllDrives=True,
    #         includeItemsFromAllDrives=True,
    #         q="trashed = false and not mimeType = 'application/vnd.google-apps.folder'", # Exemplo de filtro
    #         fields=f"nextPageToken, files({FILE_FIELDS_BASIC})",
    #         pageSize=max_results_files, # Cuidado com o volume
    #         pageToken=page_token_files
    #     )
    #     response_files = await asyncio.to_thread(request_files.execute)
    #     # ... processar arquivos e suas permissões ...
    #     page_token_files = response_files.get('nextPageToken')
    #     if not page_token_files: break

    return publicly_exposed_files

# Fim do arquivo drive_collector.py
