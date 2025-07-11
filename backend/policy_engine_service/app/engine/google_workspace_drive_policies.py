from typing import List, Optional, Union
from app.schemas.input_data_schema import (
    GoogleWorkspaceSharedDriveDataInput,
    GoogleWorkspaceDriveFileDataInput,
    # GoogleDrivePermissionInput # Não usado diretamente aqui, mas faz parte do FileDataInput
)
from app.schemas.alert_schema import Alert
import logging
import uuid

logger = logging.getLogger(__name__)

# --- Estrutura Base para Políticas do Google Drive ---
class GoogleWorkspaceDrivePolicy:
    def __init__(self, policy_id: str, title: str, description: str, severity: str, recommendation: str, applies_to: str = "file"):
        self.policy_id = policy_id
        self.title = title
        self.description = description
        self.severity = severity
        self.recommendation = recommendation
        self.applies_to = applies_to # "file" ou "shared_drive"

    def check(self, resource: Union[GoogleWorkspaceDriveFileDataInput, GoogleWorkspaceSharedDriveDataInput], account_id: Optional[str]) -> Optional[Alert]:
        raise NotImplementedError

# --- Políticas para Arquivos do Google Drive ---

class GWSFilePubliclySharedPolicy(GoogleWorkspaceDrivePolicy):
    def __init__(self):
        super().__init__(
            policy_id="GWS_Drive_File_Publicly_Shared",
            title="Arquivo do Google Drive Compartilhado Publicamente na Web",
            description="Este arquivo está configurado para ser acessível e encontrável por qualquer pessoa na internet. Isso representa um alto risco de exposição de dados.",
            severity="Critical",
            recommendation="Revise a necessidade de compartilhamento público. Se não for essencial, remova a permissão 'qualquer pessoa na web' ou 'público'. Use compartilhamento direcionado para usuários ou grupos específicos.",
            applies_to="file"
        )

    def check(self, file_data: GoogleWorkspaceDriveFileDataInput, account_id: Optional[str]) -> Optional[Alert]:
        if file_data.is_public_on_web: # Campo derivado pelo coletor
            details = {
                "file_id": file_data.id,
                "file_name": file_data.name,
                "web_view_link": file_data.web_view_link,
                "owners": [owner.email_address for owner in file_data.owners if owner.email_address],
                "drive_id": file_data.drive_id,
                "sharing_details": file_data.sharing_summary,
                "customer_id": account_id or "N/A"
            }
            return Alert(
                id=str(uuid.uuid4()),
                resource_id=file_data.id,
                resource_type="GoogleDriveFile",
                account_id=details["customer_id"],
                region="global",
                provider="google_workspace",
                severity=self.severity,
                title=self.title,
                description=f"O arquivo '{file_data.name}' ({file_data.id}) está compartilhado publicamente na web. Detalhes: {', '.join(file_data.sharing_summary)}",
                policy_id=self.policy_id,
                details=details,
                recommendation=self.recommendation
            )
        return None

class GWSFileSharedViaLinkPolicy(GoogleWorkspaceDrivePolicy):
    def __init__(self):
        super().__init__(
            policy_id="GWS_Drive_File_Shared_Via_Link",
            title="Arquivo do Google Drive Compartilhado com 'Qualquer Pessoa com o Link'",
            description="Este arquivo pode ser acessado por qualquer pessoa que possua o link, sem necessidade de login. Embora não seja publicamente encontrável, o link pode ser facilmente disseminado.",
            severity="High",
            recommendation="Use o compartilhamento 'qualquer pessoa com o link' com cautela, especialmente para dados sensíveis. Prefira o compartilhamento direcionado. Se o link for necessário, defina uma data de expiração se possível e monitore o acesso.",
            applies_to="file"
        )

    def check(self, file_data: GoogleWorkspaceDriveFileDataInput, account_id: Optional[str]) -> Optional[Alert]:
        if file_data.is_shared_with_link: # Campo derivado pelo coletor
            details = {
                "file_id": file_data.id,
                "file_name": file_data.name,
                "web_view_link": file_data.web_view_link,
                "owners": [owner.email_address for owner in file_data.owners if owner.email_address],
                "drive_id": file_data.drive_id,
                "sharing_details": file_data.sharing_summary,
                "customer_id": account_id or "N/A"
            }
            return Alert(
                id=str(uuid.uuid4()),
                resource_id=file_data.id,
                resource_type="GoogleDriveFile",
                account_id=details["customer_id"],
                region="global",
                provider="google_workspace",
                severity=self.severity,
                title=self.title,
                description=f"O arquivo '{file_data.name}' ({file_data.id}) está compartilhado com 'qualquer pessoa com o link'. Detalhes: {', '.join(file_data.sharing_summary)}",
                policy_id=self.policy_id,
                details=details,
                recommendation=self.recommendation
            )
        return None

# --- Políticas para Drives Compartilhados ---

class GWSSharedDriveAllowsExternalMembersPolicy(GoogleWorkspaceDrivePolicy):
    def __init__(self):
        super().__init__(
            policy_id="GWS_Shared_Drive_Allows_External_Members",
            title="Drive Compartilhado Permite Membros Externos ao Domínio",
            description="O Drive Compartilhado está configurado para permitir a adição de membros de fora do seu domínio Google Workspace. Isso pode aumentar o risco de exposição de dados se não gerenciado cuidadosamente.",
            severity="Medium",
            recommendation="Revise a necessidade de permitir membros externos neste Drive Compartilhado. Se não for essencial, desabilite a configuração 'domainUsersOnly' (ou habilite a restrição equivalente) nas configurações do Drive Compartilhado. Monitore regularmente os membros externos.",
            applies_to="shared_drive"
        )

    def check(self, shared_drive: GoogleWorkspaceSharedDriveDataInput, account_id: Optional[str]) -> Optional[Alert]:
        # `domainUsersOnly = False` significa que externos SÃO permitidos.
        if shared_drive.restrictions and shared_drive.restrictions.domain_users_only is False:
            details = {
                "shared_drive_id": shared_drive.id,
                "shared_drive_name": shared_drive.name,
                "customer_id": account_id or "N/A",
                "restriction_domain_users_only": False
            }
            return Alert(
                id=str(uuid.uuid4()),
                resource_id=shared_drive.id,
                resource_type="GoogleSharedDrive",
                account_id=details["customer_id"],
                region="global",
                provider="google_workspace",
                severity=self.severity,
                title=self.title,
                description=f"O Drive Compartilhado '{shared_drive.name}' ({shared_drive.id}) permite a adição de membros externos (domainUsersOnly=false).",
                policy_id=self.policy_id,
                details=details,
                recommendation=self.recommendation
            )
        return None

class GWSSharedDriveAllowsNonMembersAccessToFilesPolicy(GoogleWorkspaceDrivePolicy):
    def __init__(self):
        super().__init__(
            policy_id="GWS_Shared_Drive_Allows_Non_Members_File_Access",
            title="Drive Compartilhado Permite que Arquivos Sejam Compartilhados com Não-Membros",
            description="O Drive Compartilhado está configurado de forma que arquivos contidos nele podem ser compartilhados com usuários que não são membros do próprio Drive Compartilhado. Isso pode levar a uma disseminação mais ampla de dados.",
            severity="Medium",
            recommendation="Revise esta configuração ('driveMembersOnly'). Se o acesso aos arquivos deve ser estritamente limitado aos membros do Drive Compartilhado, habilite esta restrição. Considere também as permissões de compartilhamento dos membros.",
            applies_to="shared_drive"
        )

    def check(self, shared_drive: GoogleWorkspaceSharedDriveDataInput, account_id: Optional[str]) -> Optional[Alert]:
        # `driveMembersOnly = False` significa que arquivos PODEM ser compartilhados com não-membros.
        if shared_drive.restrictions and shared_drive.restrictions.drive_members_only is False:
            details = {
                "shared_drive_id": shared_drive.id,
                "shared_drive_name": shared_drive.name,
                "customer_id": account_id or "N/A",
                "restriction_drive_members_only": False
            }
            return Alert(
                id=str(uuid.uuid4()),
                resource_id=shared_drive.id,
                resource_type="GoogleSharedDrive",
                account_id=details["customer_id"],
                region="global",
                provider="google_workspace",
                severity=self.severity,
                title=self.title,
                description=f"O Drive Compartilhado '{shared_drive.name}' ({shared_drive.id}) permite que arquivos sejam compartilhados com não-membros (driveMembersOnly=false).",
                policy_id=self.policy_id,
                details=details,
                recommendation=self.recommendation
            )
        return None

# --- Lista de Políticas ---
# Separar por tipo de recurso para facilitar a avaliação
gws_drive_file_policies: List[GoogleWorkspaceDrivePolicy] = [
    GWSFilePubliclySharedPolicy(),
    GWSFileSharedViaLinkPolicy(),
]

gws_shared_drive_policies: List[GoogleWorkspaceDrivePolicy] = [
    GWSSharedDriveAllowsExternalMembersPolicy(),
    GWSSharedDriveAllowsNonMembersAccessToFilesPolicy(),
]

# --- Funções de Avaliação ---
def evaluate_google_workspace_drive_policies(
    shared_drives_data: List[GoogleWorkspaceSharedDriveDataInput], # O coletor envia uma lista de SharedDriveData
    account_id: Optional[str] # customer_id
) -> List[Alert]:
    all_alerts: List[Alert] = []
    logger.info(f"Avaliando {len(shared_drives_data)} Drives Compartilhados do Google Workspace para o cliente {account_id or 'N/A'}.")

    for shared_drive in shared_drives_data:
        if shared_drive.error_details:
            logger.warning(f"Skipping GWS Shared Drive {shared_drive.name} due to collection error: {shared_drive.error_details}")
            # Opcional: criar alerta sobre falha na coleta do Drive Compartilhado
            continue

        effective_customer_id = account_id or "N/A"

        # Avaliar políticas de nível de Drive Compartilhado
        for policy_def in gws_shared_drive_policies:
            try:
                alert = policy_def.check(shared_drive, effective_customer_id)
                if alert:
                    all_alerts.append(alert)
            except Exception as e:
                logger.error(f"Error evaluating Shared Drive policy {policy_def.policy_id} for {shared_drive.name}: {e}", exc_info=True)
                # Criar alerta de erro de engine para o Drive Compartilhado
                all_alerts.append(Alert(
                    id=str(uuid.uuid4()), resource_id=shared_drive.id, resource_type="GoogleSharedDrive",
                    account_id=effective_customer_id, region="global", provider="google_workspace",
                    severity="Medium", title=f"Erro ao Avaliar Política de Drive Compartilhado {policy_def.policy_id}",
                    description=f"Erro interno: {str(e)}", policy_id="POLICY_ENGINE_ERROR_GWS_SHARED_DRIVE",
                    details={"failed_policy_id": policy_def.policy_id, "shared_drive_name": shared_drive.name},
                    recommendation="Verifique os logs do Policy Engine."
                ))

        # Avaliar políticas para arquivos problemáticos dentro deste Drive Compartilhado
        for file_data in shared_drive.files_with_problematic_sharing:
            if file_data.error_details: # Erro na coleta específica deste arquivo
                logger.warning(f"Skipping file {file_data.name} in Shared Drive {shared_drive.name} due to collection error: {file_data.error_details}")
                continue

            for policy_def in gws_drive_file_policies:
                try:
                    alert = policy_def.check(file_data, effective_customer_id)
                    if alert:
                        all_alerts.append(alert)
                except Exception as e:
                    logger.error(f"Error evaluating Drive File policy {policy_def.policy_id} for file {file_data.name}: {e}", exc_info=True)
                    all_alerts.append(Alert(
                        id=str(uuid.uuid4()), resource_id=file_data.id, resource_type="GoogleDriveFile",
                        account_id=effective_customer_id, region="global", provider="google_workspace",
                        severity="Medium", title=f"Erro ao Avaliar Política de Arquivo do Drive {policy_def.policy_id}",
                        description=f"Erro interno: {str(e)}", policy_id="POLICY_ENGINE_ERROR_GWS_DRIVE_FILE",
                        details={"failed_policy_id": policy_def.policy_id, "file_name": file_data.name, "shared_drive_id": shared_drive.id},
                        recommendation="Verifique os logs do Policy Engine."
                    ))

    logger.info(f"Avaliação de Google Workspace Drive concluída para {account_id or 'N/A'}. {len(all_alerts)} alertas gerados.")
    return all_alerts

# Se, no futuro, o coletor enviar uma lista de DriveFileData avulsos (não apenas aninhados em SharedDrives),
# uma função separada `evaluate_google_workspace_individual_files_policies` poderia ser criada,
# ou a função principal precisaria de um tipo de dados de entrada mais genérico.
# Para o MVP atual, focamos em `SharedDriveData` como a entrada principal.
#
# Fim do arquivo.
