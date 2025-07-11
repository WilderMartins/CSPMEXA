# Makes schemas/google_workspace a package
# Import schemas to make them available via from app.schemas.google_workspace import ...
from .google_workspace_user import (
    GoogleWorkspaceUserInput,
    GoogleWorkspaceUserEmail,
    GoogleWorkspaceUserName,
    GoogleWorkspaceUserData,
    GoogleWorkspaceUserCollection
)

__all__ = [
    "GoogleWorkspaceUserInput",
    "GoogleWorkspaceUserEmail",
    "GoogleWorkspaceUserName",
    "GoogleWorkspaceUserData",
    "GoogleWorkspaceUserCollection"
]

from .google_drive_permission import DrivePermission
from .google_drive_file import DriveFileData, DriveFileOwner, DriveFileListResponse
from .google_drive_shared_drive import SharedDriveData, DriveRestrictions, SharedDriveCapabilities, SharedDriveListResponse

__all__.extend([
    "DrivePermission",
    "DriveFileData",
    "DriveFileOwner",
    "DriveFileListResponse",
    "SharedDriveData",
    "DriveRestrictions",
    "SharedDriveCapabilities",
    "SharedDriveListResponse"
])
