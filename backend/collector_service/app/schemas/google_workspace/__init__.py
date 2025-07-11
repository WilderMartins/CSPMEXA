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
