from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from .google_drive_file import DriveFileData # Para listar arquivos problemáticos

class DriveRestrictions(BaseModel):
    admin_managed_restrictions: Optional[bool] = Field(None, alias="adminManagedRestrictions")
    copy_requires_writer_permission: Optional[bool] = Field(None, alias="copyRequiresWriterPermission")
    domain_users_only: Optional[bool] = Field(None, alias="domainUsersOnly")
    drive_members_only: Optional[bool] = Field(None, alias="driveMembersOnly")

    # Novos campos de restrição da API (verificar documentação para nomes exatos)
    # Exemplo: sharing_requesters_can_approve: Optional[bool] = Field(None, alias="sharingRequestersCanApprove")
    #          team_members_only: Optional[bool] = Field(None, alias="teamMembersOnly") # Similar a driveMembersOnly?

    class Config:
        populate_by_name = True
        extra = 'ignore'

class SharedDriveCapabilities(BaseModel):
    can_add_children: Optional[bool] = Field(None, alias="canAddChildren")
    can_change_drive_background: Optional[bool] = Field(None, alias="canChangeDriveBackground")
    can_change_copy_requires_writer_permission_restriction: Optional[bool] = Field(None, alias="canChangeCopyRequiresWriterPermissionRestriction")
    can_change_domain_users_only_restriction: Optional[bool] = Field(None, alias="canChangeDomainUsersOnlyRestriction")
    can_change_drive_members_only_restriction: Optional[bool] = Field(None, alias="canChangeDriveMembersOnlyRestriction")
    can_change_sharing_folders_requires_organizer_permission_restriction: Optional[bool] = Field(None, alias="canChangeSharingFoldersRequiresOrganizerPermissionRestriction") # Nome longo, verificar API
    can_comment: Optional[bool] = Field(None, alias="canComment")
    can_copy: Optional[bool] = Field(None, alias="canCopy")
    can_delete_children: Optional[bool] = Field(None, alias="canDeleteChildren")
    can_delete_drive: Optional[bool] = Field(None, alias="canDeleteDrive")
    can_download: Optional[bool] = Field(None, alias="canDownload")
    can_edit: Optional[bool] = Field(None, alias="canEdit")
    can_list_children: Optional[bool] = Field(None, alias="canListChildren")
    can_manage_members: Optional[bool] = Field(None, alias="canManageMembers")
    can_read_revisions: Optional[bool] = Field(None, alias="canReadRevisions")
    can_rename: Optional[bool] = Field(None, alias="canRename")
    can_rename_drive: Optional[bool] = Field(None, alias="canRenameDrive")
    can_share: Optional[bool] = Field(None, alias="canShare") # Importante: se membros podem compartilhar arquivos/pastas
    can_trash_children: Optional[bool] = Field(None, alias="canTrashChildren")

    class Config:
        populate_by_name = True
        extra = 'ignore'


class SharedDriveData(BaseModel):
    id: str
    name: str
    created_time: Optional[datetime] = Field(None, alias="createdTime")
    # theme_id: Optional[str] = Field(None, alias="themeId")
    # background_image_link: Optional[str] = Field(None, alias="backgroundImageLink")
    # color_rgb: Optional[str] = Field(None, alias="colorRgb")

    restrictions: Optional[DriveRestrictions] = None
    capabilities: Optional[SharedDriveCapabilities] = None

    # Para análise de segurança, podemos querer adicionar:
    # - Lista de membros (com seus papéis) - requer chamada permissions.list para o driveId
    # - Configurações de compartilhamento padrão do Drive Compartilhado (se a API expõe)

    # Lista de arquivos dentro deste Drive Compartilhado que têm compartilhamento problemático
    files_with_problematic_sharing: List[DriveFileData] = Field(default_factory=list)

    error_details: Optional[str] = None # Para erros ao coletar este Drive Compartilhado

    class Config:
        populate_by_name = True
        extra = 'ignore'

# Para respostas de listagem de Drives Compartilhados
class SharedDriveListResponse(BaseModel):
    kind: str = "drive#driveList"
    next_page_token: Optional[str] = Field(None, alias="nextPageToken")
    drives: List[SharedDriveData] = Field(default_factory=list)

    class Config:
        populate_by_name = True
        extra = 'ignore'

# Exemplo de campos para `drives.list` para obter informações relevantes:
# `fields="nextPageToken, drives(id, name, createdTime, restrictions, capabilities)"`
#
# Para obter membros de um Drive Compartilhado, seria necessário chamar `permissions.list(fileId=driveId, supportsAllDrives=True)`.
# As permissões em um Drive Compartilhado definem os membros e seus papéis (organizer, fileOrganizer, writer, commenter, reader).
#
# `restrictions.domainUsersOnly`: Se true, apenas usuários no domínio do Drive Compartilhado podem ser adicionados como membros.
# `restrictions.driveMembersOnly`: Se true, apenas membros do Drive Compartilhado podem acessar arquivos.
# `capabilities.canShare`: Se membros (não organizadores) podem compartilhar arquivos.
#
# Fim do arquivo.
