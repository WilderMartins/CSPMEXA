from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from .google_drive_permission import DrivePermission # Import relativo

class DriveFileOwner(BaseModel): # Sub-schema para owners
    display_name: Optional[str] = Field(None, alias="displayName")
    email_address: Optional[str] = Field(None, alias="emailAddress") # Não EmailStr, pode ser SA
    # kind: Optional[str] = None
    # me: Optional[bool] = None
    # permission_id: Optional[str] = Field(None, alias="permissionId")
    # photo_link: Optional[str] = Field(None, alias="photoLink")
    class Config:
        populate_by_name = True
        extra = 'ignore'

class DriveFileData(BaseModel):
    id: str
    name: str
    mime_type: str = Field(alias="mimeType")
    owners: List[DriveFileOwner] = Field(default_factory=list) # Lista de proprietários
    shared: Optional[bool] = False # True se compartilhado com alguém além do proprietário
    web_view_link: Optional[str] = Field(None, alias="webViewLink")
    drive_id: Optional[str] = Field(None, alias="driveId") # ID do Drive Compartilhado, se aplicável

    # Este campo será populado por uma chamada separada a permissions.list para este arquivo
    permissions_list: List[DrivePermission] = Field(default_factory=list, alias="permissions")

    # Campos derivados (a serem preenchidos pelo coletor após analisar permissions_list)
    is_public_on_web: bool = False
    is_shared_with_link: bool = False
    is_shared_externally_direct: bool = False # Compartilhado diretamente com usuários/grupos externos
    is_shared_with_domain: bool = False # Compartilhado com todo o domínio

    # Detalhes resumidos do compartilhamento para fácil visualização/política
    sharing_summary: List[str] = Field(default_factory=list)

    last_modifying_user_email: Optional[str] = Field(None, alias="lastModifyingUserEmail") # Nome do campo pode variar, verificar API
    modified_time: Optional[datetime] = Field(None, alias="modifiedTime")
    created_time: Optional[datetime] = Field(None, alias="createdTime")

    error_details: Optional[str] = None # Para erros específicos deste arquivo

    class Config:
        populate_by_name = True
        extra = 'ignore'

# Para respostas de listagem de arquivos
class DriveFileListResponse(BaseModel):
    kind: str = "drive#fileList"
    next_page_token: Optional[str] = Field(None, alias="nextPageToken")
    incomplete_search: Optional[bool] = Field(None, alias="incompleteSearch")
    files: List[DriveFileData] = Field(default_factory=list)

    class Config:
        populate_by_name = True
        extra = 'ignore'

# Exemplo de campos para `files.list` para obter informações relevantes:
# `fields="nextPageToken, files(id, name, mimeType, owners(displayName,emailAddress), shared, webViewLink, driveId, modifiedTime, createdTime, permissions(id,type,role,emailAddress,domain,allowFileDiscovery,displayName))"`
# Nota: Incluir `permissions` diretamente no `files.list` pode retornar apenas um subconjunto das permissões
# ou pode ser muito custoso/lento. A prática recomendada é geralmente fazer uma chamada `permissions.list(fileId=...)`
# separada para cada arquivo de interesse para obter a lista completa de permissões.
# O campo `permissions_list` no schema `DriveFileData` reflete isso.
# O alias `permissions` é para o caso de a API `files.list` retornar algumas permissões.
# O coletor precisará consolidar isso.
#
# Para `lastModifyingUser`, o objeto File da API Drive tem `lastModifyingUser` (um objeto User).
# Podemos simplificar para `last_modifying_user_email` ou ter um sub-schema.
# `lastModifyingUser(displayName, emailAddress)`
# O schema atual tem `last_modifying_user_email: Optional[str] = Field(None, alias="lastModifyingUserEmail")`
# Isso implica que o coletor extrairá o email do objeto `lastModifyingUser`.
#
# Os campos derivados como `is_public_on_web` serão calculados no coletor.
#
# Fim do arquivo.
