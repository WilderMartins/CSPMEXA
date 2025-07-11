from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- Schemas de Usuários (espelham collector_service) ---
class GoogleWorkspaceUserEmail(BaseModel):
    address: Optional[EmailStr] = None
    primary: Optional[bool] = None
    class Config: extra = 'ignore'

class GoogleWorkspaceUserName(BaseModel):
    given_name: Optional[str] = Field(None, alias="givenName")
    family_name: Optional[str] = Field(None, alias="familyName")
    full_name: Optional[str] = Field(None, alias="fullName")
    class Config: populate_by_name = True; extra = 'ignore'

class GoogleWorkspaceUserData(BaseModel):
    id: str
    primary_email: EmailStr = Field(..., alias="primaryEmail")
    name: GoogleWorkspaceUserName
    is_admin: bool = Field(False, alias="isAdmin")
    is_delegated_admin: Optional[bool] = Field(None, alias="isDelegatedAdmin")
    last_login_time: Optional[datetime] = Field(None, alias="lastLoginTime")
    creation_time: Optional[datetime] = Field(None, alias="creationTime")
    suspended: Optional[bool] = False
    archived: Optional[bool] = False
    org_unit_path: Optional[str] = Field(None, alias="orgUnitPath")
    is_enrolled_in_2sv: bool = Field(False, alias="isEnrolledIn2Sv")
    emails: Optional[List[GoogleWorkspaceUserEmail]] = None
    error_details: Optional[str] = None
    class Config: populate_by_name = True; extra = 'ignore'

class GoogleWorkspaceUserCollection(BaseModel):
    users: List[GoogleWorkspaceUserData] = Field(default_factory=list)
    next_page_token: Optional[str] = Field(None, alias="nextPageToken")
    error_message: Optional[str] = None
    class Config: populate_by_name = True; extra = 'ignore'


# --- Schemas do Google Drive (espelham collector_service) ---

class DrivePermission(BaseModel):
    id: str
    type: str
    role: str
    email_address: Optional[EmailStr] = Field(None, alias="emailAddress")
    domain: Optional[str] = None
    allow_file_discovery: Optional[bool] = Field(None, alias="allowFileDiscovery")
    deleted: Optional[bool] = None
    display_name: Optional[str] = Field(None, alias="displayName")
    class Config: populate_by_name = True; extra = 'ignore'

class DriveFileOwner(BaseModel):
    display_name: Optional[str] = Field(None, alias="displayName")
    email_address: Optional[str] = Field(None, alias="emailAddress")
    class Config: populate_by_name = True; extra = 'ignore'

class DriveFileData(BaseModel):
    id: str
    name: str
    mime_type: str = Field(alias="mimeType")
    owners: List[DriveFileOwner] = Field(default_factory=list)
    shared: Optional[bool] = False
    web_view_link: Optional[str] = Field(None, alias="webViewLink")
    drive_id: Optional[str] = Field(None, alias="driveId")
    permissions_list: List[DrivePermission] = Field(default_factory=list, alias="permissions")
    is_public_on_web: bool = False
    is_shared_with_link: bool = False
    is_shared_externally_direct: bool = False
    is_shared_with_domain: bool = False
    sharing_summary: List[str] = Field(default_factory=list)
    last_modifying_user_email: Optional[str] = Field(None, alias="lastModifyingUserEmail")
    modified_time: Optional[datetime] = Field(None, alias="modifiedTime")
    created_time: Optional[datetime] = Field(None, alias="createdTime")
    error_details: Optional[str] = None
    class Config: populate_by_name = True; extra = 'ignore'

class DriveFileListResponse(BaseModel): # Para o caso de listarmos arquivos diretamente no futuro
    kind: str = "drive#fileList"
    next_page_token: Optional[str] = Field(None, alias="nextPageToken")
    incomplete_search: Optional[bool] = Field(None, alias="incompleteSearch")
    files: List[DriveFileData] = Field(default_factory=list)
    class Config: populate_by_name = True; extra = 'ignore'

class DriveRestrictions(BaseModel):
    admin_managed_restrictions: Optional[bool] = Field(None, alias="adminManagedRestrictions")
    copy_requires_writer_permission: Optional[bool] = Field(None, alias="copyRequiresWriterPermission")
    domain_users_only: Optional[bool] = Field(None, alias="domainUsersOnly")
    drive_members_only: Optional[bool] = Field(None, alias="driveMembersOnly")
    class Config: populate_by_name = True; extra = 'ignore'

class SharedDriveCapabilities(BaseModel):
    can_add_children: Optional[bool] = Field(None, alias="canAddChildren")
    # Adicionar outros campos de capabilities conforme necessário para políticas
    can_share: Optional[bool] = Field(None, alias="canShare")
    class Config: populate_by_name = True; extra = 'ignore'

class SharedDriveData(BaseModel):
    id: str
    name: str
    created_time: Optional[datetime] = Field(None, alias="createdTime")
    restrictions: Optional[DriveRestrictions] = None
    capabilities: Optional[SharedDriveCapabilities] = None
    files_with_problematic_sharing: List[DriveFileData] = Field(default_factory=list)
    error_details: Optional[str] = None
    class Config: populate_by_name = True; extra = 'ignore'

class SharedDriveListResponse(BaseModel): # Para o caso de listarmos drives diretamente no futuro
    kind: str = "drive#driveList"
    next_page_token: Optional[str] = Field(None, alias="nextPageToken")
    drives: List[SharedDriveData] = Field(default_factory=list)
    class Config: populate_by_name = True; extra = 'ignore'


__all__ = [
    "GoogleWorkspaceUserEmail",
    "GoogleWorkspaceUserName",
    "GoogleWorkspaceUserData",
    "GoogleWorkspaceUserCollection",
    "DrivePermission",
    "DriveFileData",
    "DriveFileOwner",
    "DriveFileListResponse",
    "SharedDriveData",
    "DriveRestrictions",
    "SharedDriveCapabilities",
    "SharedDriveListResponse"
]
