from typing import List, Optional
from app.schemas.input_data_schema import GoogleWorkspaceUserDataInput
from app.schemas.alert_schema import Alert
import logging
import uuid
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# --- Estrutura Base para Políticas de Usuários do Google Workspace ---
class GoogleWorkspaceUserPolicy:
    def __init__(self, policy_id: str, title: str, description: str, severity: str, recommendation: str):
        self.policy_id = policy_id
        self.title = title
        self.description = description
        self.severity = severity
        self.recommendation = recommendation

    def check(self, user: GoogleWorkspaceUserDataInput, account_id: Optional[str]) -> Optional[Alert]: # account_id aqui é customer_id
        raise NotImplementedError

# --- Definições de Políticas para Usuários do Google Workspace ---

class GWSUserSuspendedPolicy(GoogleWorkspaceUserPolicy):
    def __init__(self):
        super().__init__(
            policy_id="GWS_User_Suspended",
            title="Usuário do Google Workspace Suspenso",
            description="A conta do usuário no Google Workspace está atualmente suspensa. Isso pode ser intencional ou indicar um problema.",
            severity="Informational", # Pode ser Medium dependendo do contexto
            recommendation="Verifique o motivo da suspensão. Se não for intencional ou se o usuário não precisar mais de acesso, considere remover ou arquivar a conta para liberar licenças e reduzir a superfície de ataque."
        )

    def check(self, user: GoogleWorkspaceUserDataInput, account_id: Optional[str]) -> Optional[Alert]:
        if user.suspended:
            details = {
                "user_primary_email": user.primary_email,
                "user_id": user.id,
                "customer_id": account_id or "N/A",
                "status": "Suspended",
                "org_unit_path": user.org_unit_path
            }
            return Alert(
                id=str(uuid.uuid4()),
                resource_id=user.id,
                resource_type="GoogleWorkspaceUser",
                account_id=details["customer_id"],
                region="global", # Google Workspace é global
                provider="google_workspace",
                severity=self.severity,
                title=self.title,
                description=f"O usuário {user.primary_email} está suspenso. Org Unit: {user.org_unit_path or 'N/A'}.",
                policy_id=self.policy_id,
                details=details,
                recommendation=self.recommendation
            )
        return None

class GWSUserNo2SVPolicy(GoogleWorkspaceUserPolicy):
    def __init__(self):
        super().__init__(
            policy_id="GWS_User_2SV_Disabled",
            title="Usuário do Google Workspace sem Verificação em Duas Etapas (2SV/MFA) Habilitada",
            description="O usuário não possui a Verificação em Duas Etapas (2SV/MFA) habilitada em sua conta. Isso aumenta significativamente o risco de comprometimento da conta.",
            severity="High", # Para usuários normais. Para admins, deveria ser Critical.
            recommendation="Exija e ajude o usuário a habilitar a Verificação em Duas Etapas (2SV/MFA) em sua conta Google Workspace. Para administradores, a 2SV deve ser mandatória."
        )

    def check(self, user: GoogleWorkspaceUserDataInput, account_id: Optional[str]) -> Optional[Alert]:
        if not user.is_enrolled_in_2sv:
            current_severity = self.severity
            if user.is_admin: # Se o usuário for um administrador, a severidade é maior
                current_severity = "Critical"

            description_detail = f"O usuário {user.primary_email} (Admin: {user.is_admin}) não tem 2SV habilitada."

            details = {
                "user_primary_email": user.primary_email,
                "user_id": user.id,
                "customer_id": account_id or "N/A",
                "is_admin": user.is_admin,
                "is_enrolled_in_2sv": False,
                "org_unit_path": user.org_unit_path
            }
            return Alert(
                id=str(uuid.uuid4()),
                resource_id=user.id,
                resource_type="GoogleWorkspaceUser",
                account_id=details["customer_id"],
                region="global",
                provider="google_workspace",
                severity=current_severity,
                title=self.title,
                description=description_detail,
                policy_id=self.policy_id,
                details=details,
                recommendation=self.recommendation
            )
        return None

class GWSUserAdminPrivilegesPolicy(GoogleWorkspaceUserPolicy):
    def __init__(self):
        super().__init__(
            policy_id="GWS_User_Has_Admin_Privileges",
            title="Usuário do Google Workspace com Privilégios de Administrador",
            description="O usuário possui privilégios de administrador no Google Workspace. Contas de administrador são alvos de alto valor.",
            severity="Informational", # Apenas informativo, mas importante para visibilidade
            recommendation="Revise regularmente a lista de administradores. Garanta que apenas os usuários necessários tenham privilégios de administrador e que sigam o princípio do menor privilégio. Monitore a atividade de contas de administrador."
        )

    def check(self, user: GoogleWorkspaceUserDataInput, account_id: Optional[str]) -> Optional[Alert]:
        if user.is_admin:
            details = {
                "user_primary_email": user.primary_email,
                "user_id": user.id,
                "customer_id": account_id or "N/A",
                "is_admin": True,
                "is_delegated_admin": user.is_delegated_admin,
                "org_unit_path": user.org_unit_path
            }
            return Alert(
                id=str(uuid.uuid4()),
                resource_id=user.id,
                resource_type="GoogleWorkspaceUser",
                account_id=details["customer_id"],
                region="global",
                provider="google_workspace",
                severity=self.severity,
                title=self.title,
                description=f"O usuário {user.primary_email} possui privilégios de administrador (is_admin: {user.is_admin}, is_delegated_admin: {user.is_delegated_admin}).",
                policy_id=self.policy_id,
                details=details,
                recommendation=self.recommendation
            )
        return None

class GWSUserInactivePolicy(GoogleWorkspaceUserPolicy):
    def __init__(self, inactive_days_threshold: int = 90):
        self.inactive_days_threshold = inactive_days_threshold
        super().__init__(
            policy_id="GWS_User_Inactive",
            title=f"Usuário do Google Workspace Inativo por mais de {inactive_days_threshold} dias",
            description=f"O usuário não fez login no Google Workspace nos últimos {inactive_days_threshold} dias. Contas inativas podem representar um risco de segurança.",
            severity="Medium",
            recommendation=f"Verifique se a conta do usuário ainda é necessária. Se o usuário saiu da organização ou não precisa mais de acesso, suspenda ou exclua a conta. Se o acesso ainda for necessário, confirme com o usuário ou seu gerente."
        )

    def check(self, user: GoogleWorkspaceUserDataInput, account_id: Optional[str]) -> Optional[Alert]:
        if user.suspended or user.archived: # Não aplicar para contas já suspensas ou arquivadas
            return None

        if user.last_login_time:
            now = datetime.now(timezone.utc)
            # last_login_time já deve estar em UTC pelo parser do coletor
            if (now - user.last_login_time).days > self.inactive_days_threshold:
                details = {
                    "user_primary_email": user.primary_email,
                    "user_id": user.id,
                    "customer_id": account_id or "N/A",
                    "last_login_time": user.last_login_time.isoformat(),
                    "days_inactive": (now - user.last_login_time).days,
                    "org_unit_path": user.org_unit_path
                }
                return Alert(
                    id=str(uuid.uuid4()),
                    resource_id=user.id,
                    resource_type="GoogleWorkspaceUser",
                    account_id=details["customer_id"],
                    region="global",
                    provider="google_workspace",
                    severity=self.severity,
                    title=self.title,
                    description=f"O usuário {user.primary_email} não fez login desde {user.last_login_time.strftime('%Y-%m-%d')} ({(now - user.last_login_time).days} dias).",
                    policy_id=self.policy_id,
                    details=details,
                    recommendation=self.recommendation
                )
        else: # last_login_time é None, pode significar que nunca logou ou dados não disponíveis
              # Se creation_time existir e for antigo, pode ser um indicativo
            if user.creation_time:
                now = datetime.now(timezone.utc)
                if (now - user.creation_time).days > self.inactive_days_threshold:
                    details = {
                        "user_primary_email": user.primary_email,
                        "user_id": user.id,
                        "customer_id": account_id or "N/A",
                        "last_login_time": "Never or Unknown",
                        "creation_time": user.creation_time.isoformat(),
                        "days_since_creation_with_no_login": (now - user.creation_time).days,
                        "org_unit_path": user.org_unit_path
                    }
                    return Alert(
                        id=str(uuid.uuid4()),
                        resource_id=user.id,
                        resource_type="GoogleWorkspaceUser",
                        account_id=details["customer_id"],
                        region="global",
                        provider="google_workspace",
                        severity=self.severity, # Severidade pode ser ajustada para este caso
                        title=f"Usuário do Google Workspace sem Login Registrado e Criado há mais de {self.inactive_days_threshold} dias",
                        description=f"O usuário {user.primary_email} foi criado em {user.creation_time.strftime('%Y-%m-%d')} e não possui registro de último login.",
                        policy_id=self.policy_id, # Pode usar um sub-ID de política para este caso
                        details=details,
                        recommendation=self.recommendation
                    )
        return None


# --- Lista de Políticas ---
google_workspace_user_policies_to_evaluate: List[GoogleWorkspaceUserPolicy] = [
    GWSUserSuspendedPolicy(),
    GWSUserNo2SVPolicy(),
    GWSUserAdminPrivilegesPolicy(),
    GWSUserInactivePolicy(inactive_days_threshold=90),
]

# --- Funções de Avaliação ---
def evaluate_google_workspace_user_policies(
    users_data: List[GoogleWorkspaceUserDataInput],
    account_id: Optional[str] # customer_id da requisição de análise
) -> List[Alert]:
    all_alerts: List[Alert] = []
    logger.info(f"Avaliando {len(users_data)} usuários do Google Workspace para o cliente {account_id or 'N/A'}.")

    for user in users_data:
        if user.error_details: # Se o coletor teve um erro para este usuário específico
            logger.warning(f"Skipping Google Workspace user {user.primary_email} due to collection error: {user.error_details}")
            # Opcional: criar um alerta sobre falha na coleta do usuário
            continue

        effective_customer_id = account_id or "N/A" # Usar o da requisição se disponível

        for policy_def in google_workspace_user_policies_to_evaluate:
            try:
                alert = policy_def.check(user, effective_customer_id)
                if alert:
                    all_alerts.append(alert)
            except Exception as e:
                logger.error(f"Error evaluating policy {policy_def.policy_id} for GWS user {user.primary_email}: {e}", exc_info=True)
                all_alerts.append(Alert(
                    id=str(uuid.uuid4()), resource_id=user.id, resource_type="GoogleWorkspaceUser",
                    account_id=effective_customer_id, region="global", provider="google_workspace",
                    severity="Medium", title=f"Erro ao Avaliar Política GWS User {policy_def.policy_id}",
                    description=f"Ocorreu um erro interno ao avaliar a política '{policy_def.title}' para o usuário {user.primary_email}. Detalhe: {str(e)}",
                    policy_id="POLICY_ENGINE_ERROR_GWS_USER",
                    details={"failed_policy_id": policy_def.policy_id, "user_email": user.primary_email, "error": str(e)},
                    recommendation="Verifique os logs do Policy Engine."
                ))

    logger.info(f"Avaliação de Usuários Google Workspace concluída para {account_id or 'N/A'}. {len(all_alerts)} alertas gerados.")
    return all_alerts

# Observações:
# - As políticas implementadas são:
#   - GWSUserSuspendedPolicy: Informa sobre usuários suspensos.
#   - GWSUserNo2SVPolicy: Verifica se a 2SV (MFA) está desabilitada, com severidade maior para admins.
#   - GWSUserAdminPrivilegesPolicy: Informa sobre usuários com privilégios de admin (informativo).
#   - GWSUserInactivePolicy: Verifica usuários inativos por mais de X dias (baseado em last_login_time ou creation_time se login for desconhecido).
# - O `account_id` passado para as funções de `check` é o `customer_id` do Google Workspace.
# - As políticas podem ser expandidas para cobrir mais aspectos (ex: senhas fracas se a API fornecer, delegação de admin excessiva, etc.).
# - A identificação de "usuário root" não é direta no Workspace; `is_admin` é usado para identificar administradores.
# - Este arquivo forma a base para políticas de usuários do Google Workspace.
#
# Fim do arquivo.
