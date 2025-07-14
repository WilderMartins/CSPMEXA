import pytest
from datetime import datetime, timezone
import uuid

from policy_engine_service.app.engine.google_workspace_drive_policies import (
    GWSFilePubliclySharedPolicy,
    GWSFileSharedViaLinkPolicy,
    GWSSharedDriveAllowsExternalMembersPolicy,
    GWSSharedDriveAllowsNonMembersAccessToFilesPolicy,
    evaluate_google_workspace_drive_policies
)
from policy_engine_service.app.schemas.input_data_schema import (
    GoogleWorkspaceSharedDriveDataInput,
    GoogleWorkspaceDriveFileDataInput,
    GoogleDriveRestrictionsInput
)
from policy_engine_service.app.schemas.alert_schema import Alert

CUSTOMER_ID = "gws_customer_123"

# --- Fixtures para Dados do Drive ---

@pytest.fixture
def drive_file_public() -> GoogleWorkspaceDriveFileDataInput:
    return GoogleWorkspaceDriveFileDataInput(
        id="file-pub-id", name="Public Document.docx", mime_type="application/vnd.google-apps.document",
        owners=[], # Simplificado
        is_public_on_web=True, # Campo chave para a política
        sharing_summary=["Public on the web (reader)"]
    )

@pytest.fixture
def drive_file_link_shared() -> GoogleWorkspaceDriveFileDataInput:
    return GoogleWorkspaceDriveFileDataInput(
        id="file-link-id", name="Link Shared Doc.pdf", mime_type="application/pdf",
        owners=[],
        is_shared_with_link=True, # Campo chave
        sharing_summary=["Anyone with the link (reader)"]
    )

@pytest.fixture
def drive_file_private() -> GoogleWorkspaceDriveFileDataInput:
    return GoogleWorkspaceDriveFileDataInput(
        id="file-priv-id", name="Private Notes.txt", mime_type="text/plain",
        owners=[],
        is_public_on_web=False,
        is_shared_with_link=False,
        shared=True, # Compartilhado, mas não publicamente/link
        sharing_summary=["Shared with specific_user@example.com"]
    )

@pytest.fixture
def shared_drive_external_members_allowed() -> GoogleWorkspaceSharedDriveDataInput:
    return GoogleWorkspaceSharedDriveDataInput(
        id="sd-ext-id", name="Project X (Externals Allowed)",
        restrictions=GoogleDriveRestrictionsInput(domainUsersOnly=False), # Violação
        files_with_problematic_sharing=[]
    )

@pytest.fixture
def shared_drive_domain_only_members() -> GoogleWorkspaceSharedDriveDataInput:
    return GoogleWorkspaceSharedDriveDataInput(
        id="sd-dom-id", name="Internal Projects",
        restrictions=GoogleDriveRestrictionsInput(domainUsersOnly=True), # OK
        files_with_problematic_sharing=[]
    )

@pytest.fixture
def shared_drive_non_members_can_access_files() -> GoogleWorkspaceSharedDriveDataInput:
    return GoogleWorkspaceSharedDriveDataInput(
        id="sd-nonmemb-id", name="Team Collaboration Drive",
        restrictions=GoogleDriveRestrictionsInput(driveMembersOnly=False), # Violação
        files_with_problematic_sharing=[]
    )

@pytest.fixture
def shared_drive_members_only_access_files() -> GoogleWorkspaceSharedDriveDataInput:
    return GoogleWorkspaceSharedDriveDataInput(
        id="sd-membersonly-id", name="Secure Team Drive",
        restrictions=GoogleDriveRestrictionsInput(driveMembersOnly=True), # OK
        files_with_problematic_sharing=[]
    )

@pytest.fixture
def shared_drive_with_public_file(drive_file_public) -> GoogleWorkspaceSharedDriveDataInput:
    return GoogleWorkspaceSharedDriveDataInput(
        id="sd-withpubfile-id", name="Drive With Public File",
        restrictions=GoogleDriveRestrictionsInput(domainUsersOnly=True, driveMembersOnly=True), # Config do Drive está OK
        files_with_problematic_sharing=[drive_file_public] # Mas contém um arquivo público
    )

@pytest.fixture
def shared_drive_with_error() -> GoogleWorkspaceSharedDriveDataInput:
    return GoogleWorkspaceSharedDriveDataInput(
        id="sd-error-id", name="Errored Drive",
        error_details="Failed to collect this shared drive."
    )

# --- Testes para Políticas de Arquivo ---

def test_gws_file_publicly_shared_policy_alert(drive_file_public):
    policy = GWSFilePubliclySharedPolicy()
    alert = policy.check(drive_file_public, CUSTOMER_ID)
    assert alert is not None
    assert alert.severity == "Critical"
    assert "publicamente na web" in alert.description

def test_gws_file_publicly_shared_policy_no_alert(drive_file_private):
    policy = GWSFilePubliclySharedPolicy()
    alert = policy.check(drive_file_private, CUSTOMER_ID)
    assert alert is None

def test_gws_file_shared_via_link_policy_alert(drive_file_link_shared):
    policy = GWSFileSharedViaLinkPolicy()
    alert = policy.check(drive_file_link_shared, CUSTOMER_ID)
    assert alert is not None
    assert alert.severity == "High"
    assert "qualquer pessoa com o link" in alert.description

def test_gws_file_shared_via_link_policy_no_alert(drive_file_private):
    policy = GWSFileSharedViaLinkPolicy()
    alert = policy.check(drive_file_private, CUSTOMER_ID)
    assert alert is None

# --- Testes para Políticas de Drive Compartilhado ---

def test_gws_shared_drive_allows_external_members_policy_alert(shared_drive_external_members_allowed):
    policy = GWSSharedDriveAllowsExternalMembersPolicy()
    alert = policy.check(shared_drive_external_members_allowed, CUSTOMER_ID)
    assert alert is not None
    assert alert.severity == "Medium"
    assert "permite a adição de membros externos" in alert.description
    assert alert.details["restriction_domain_users_only"] is False

def test_gws_shared_drive_allows_external_members_policy_no_alert(shared_drive_domain_only_members):
    policy = GWSSharedDriveAllowsExternalMembersPolicy()
    alert = policy.check(shared_drive_domain_only_members, CUSTOMER_ID)
    assert alert is None

def test_gws_shared_drive_allows_non_members_file_access_policy_alert(shared_drive_non_members_can_access_files):
    policy = GWSSharedDriveAllowsNonMembersAccessToFilesPolicy()
    alert = policy.check(shared_drive_non_members_can_access_files, CUSTOMER_ID)
    assert alert is not None
    assert alert.severity == "Medium"
    assert "arquivos sejam compartilhados com não-membros" in alert.description
    assert alert.details["restriction_drive_members_only"] is False

def test_gws_shared_drive_allows_non_members_file_access_policy_no_alert(shared_drive_members_only_access_files):
    policy = GWSSharedDriveAllowsNonMembersAccessToFilesPolicy()
    alert = policy.check(shared_drive_members_only_access_files, CUSTOMER_ID)
    assert alert is None

# --- Testes para evaluate_google_workspace_drive_policies ---

def test_evaluate_gws_drive_policies_mixed_data(
    shared_drive_external_members_allowed, # Alerta de Drive
    shared_drive_with_public_file,       # Alerta de Arquivo (aninhado)
    shared_drive_domain_only_members,    # Sem alertas de Drive
    shared_drive_with_error
):
    shared_drives_data = [
        shared_drive_external_members_allowed,
        shared_drive_with_public_file,
        shared_drive_domain_only_members,
        shared_drive_with_error # Deve ser pulado
    ]

    alerts = evaluate_google_workspace_drive_policies(shared_drives_data, CUSTOMER_ID)

    # Esperado:
    # 1 alerta de shared_drive_external_members_allowed (GWS_Shared_Drive_Allows_External_Members)
    # 1 alerta de drive_file_public (GWS_Drive_File_Publicly_Shared) vindo de shared_drive_with_public_file
    # Total = 2 alertas
    assert len(alerts) == 2

    policy_ids_found = {a.policy_id for a in alerts}
    assert GWSSharedDriveAllowsExternalMembersPolicy().policy_id in policy_ids_found
    assert GWSFilePubliclySharedPolicy().policy_id in policy_ids_found

    alert_resource_ids = {a.resource_id for a in alerts}
    assert shared_drive_external_members_allowed.id in alert_resource_ids
    assert shared_drive_with_public_file.files_with_problematic_sharing[0].id in alert_resource_ids
    assert shared_drive_with_error.id not in alert_resource_ids


def test_evaluate_gws_drive_policies_no_drives():
    alerts = evaluate_google_workspace_drive_policies([], CUSTOMER_ID)
    assert len(alerts) == 0

def test_evaluate_gws_drive_policies_drive_policy_error(shared_drive_domain_only_members):
    # Mock uma política de drive para falhar
    class FailingDrivePolicy(GoogleWorkspaceDrivePolicy):
        def __init__(self): super().__init__("FAIL_SDRIVE_POLICY", "Failing SD Policy", "D", "S", "R", "shared_drive")
        def check(self, sd, account_id): raise Exception("Simulated SD policy error")

    original_sd_policies = list(google_workspace_drive_policies.gws_shared_drive_policies)
    google_workspace_drive_policies.gws_shared_drive_policies.append(FailingDrivePolicy())

    alerts = evaluate_google_workspace_drive_policies([shared_drive_domain_only_members], CUSTOMER_ID)

    assert len(alerts) == 1
    assert alerts[0].policy_id == "POLICY_ENGINE_ERROR_GWS_SHARED_DRIVE"
    assert "Simulated SD policy error" in alerts[0].description

    google_workspace_drive_policies.gws_shared_drive_policies = original_sd_policies


def test_evaluate_gws_drive_policies_file_policy_error(shared_drive_with_public_file):
    # Mock uma política de arquivo para falhar
    class FailingFilePolicy(GoogleWorkspaceDrivePolicy):
        def __init__(self): super().__init__("FAIL_DFILE_POLICY", "Failing DFile Policy", "D", "S", "R", "file")
        def check(self, file_data, account_id): raise Exception("Simulated DFile policy error")

    original_file_policies = list(google_workspace_drive_policies.gws_drive_file_policies)
    google_workspace_drive_policies.gws_drive_file_policies.append(FailingFilePolicy())

    alerts = evaluate_google_workspace_drive_policies([shared_drive_with_public_file], CUSTOMER_ID)

    # shared_drive_with_public_file gera 1 alerta de arquivo público + 1 alerta de erro da FailingFilePolicy
    assert len(alerts) == 2
    policy_ids = {a.policy_id for a in alerts}
    assert "POLICY_ENGINE_ERROR_GWS_DRIVE_FILE" in policy_ids
    assert GWSFilePubliclySharedPolicy().policy_id in policy_ids # A política não falha ainda deve rodar

    google_workspace_drive_policies.gws_drive_file_policies = original_file_policies

# Os schemas Input (GoogleWorkspaceSharedDriveDataInput, etc.) em input_data_schema.py
# devem espelhar os schemas de output do coletor (SharedDriveData, etc.).
# Os fixtures aqui usam os schemas Input.
# As políticas usam os campos derivados `is_public_on_web` e `is_shared_with_link`
# que são preenchidos pelo coletor no `DriveFileData`.
#
# Fim do arquivo.
