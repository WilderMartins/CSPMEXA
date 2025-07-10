from typing import List, Optional, Dict, Any
from app.schemas.input_data_schema import IAMUserDataInput, IAMUserAccessKeyMetadataInput
from app.schemas.alert_schema import Alert
import logging
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# --- Estrutura Base para Políticas IAM ---

class IAMPolicy:
    def __init__(self, policy_id: str, title: str, description: str, severity: str, recommendation: str):
        self.policy_id = policy_id
        self.title = title
        self.description = description
        self.severity = severity
        self.recommendation = recommendation

    def check(self, resource: Any, account_id: Optional[str]) -> Optional[Alert]:
        """
        Verifica o recurso IAM (Usuário, Role, Policy) contra esta política.
        Retorna um Alert se a política for violada, None caso contrário.
        A região para IAM é geralmente 'global', mas pode ser incluída no alerta se relevante.
        """
        raise NotImplementedError

# --- Políticas para Usuários IAM ---

class IAMUserMFADisabledPolicy(IAMPolicy):
    def __init__(self):
        super().__init__(
            policy_id="IAM_User_MFA_Disabled",
            title="Usuário IAM sem Autenticação Multi-Fator (MFA) Habilitada",
            description="O usuário IAM não possui um dispositivo MFA (Autenticação Multi-Fator) habilitado. MFA adiciona uma camada extra de segurança às contas de usuário.",
            severity="High",
            recommendation="Habilite um dispositivo MFA para o usuário IAM para aumentar a segurança da conta. Para o usuário root, o MFA é especialmente crítico."
        )

    def check(self, user: IAMUserDataInput, account_id: Optional[str]) -> Optional[Alert]:
        # A política se aplica a todos os usuários, mas é especialmente crítica para o root.
        # O collector não diferencia o root, mas podemos checar pelo nome 'root' se necessário,
        # ou ter uma política separada para o root MFA.
        # Para este MVP, vamos aplicar a todos.

        if not user.mfa_devices or len(user.mfa_devices) == 0:
            # Verifica se o usuário é o root (uma heurística, pode não ser 100% em todas as contas)
            is_root_user = user.user_name == "<root_account>" or (user.arn and ":root" in user.arn.lower()) # Heurística
            current_severity = self.severity
            if is_root_user:
                current_severity = "Critical"


            details = {
                "user_name": user.user_name,
                "user_arn": user.arn,
                "password_last_used": user.password_last_used.isoformat() if user.password_last_used else "N/A"
            }
            return Alert(
                id=str(uuid.uuid4()),
                resource_id=user.arn, # ARN é um bom ID de recurso para usuários IAM
                resource_type="IAMUser",
                account_id=account_id or "N/A",
                region="global", # IAM é global
                provider="aws",
                severity=current_severity,
                title=f"{self.title}{' (Usuário Root)' if is_root_user else ''}",
                description=self.description,
                policy_id=self.policy_id,
                details=details,
                recommendation=self.recommendation
            )
        return None

class IAMUserUnusedAccessKeysPolicy(IAMPolicy):
    def __init__(self, unused_days_threshold: int = 90):
        self.unused_days_threshold = unused_days_threshold
        super().__init__(
            policy_id="IAM_User_Unused_Access_Keys",
            title=f"Chave de Acesso IAM não utilizada por mais de {unused_days_threshold} dias",
            description=f"Uma ou mais chaves de acesso do usuário IAM não foram utilizadas nos últimos {unused_days_threshold} dias. Chaves não utilizadas representam um risco de segurança se comprometidas.",
            severity="Medium",
            recommendation=f"Revise as chaves de acesso não utilizadas. Se não forem mais necessárias, desative-as ou exclua-as. Rotacione as chaves de acesso regularmente."
        )

    def check(self, user: IAMUserDataInput, account_id: Optional[str]) -> Optional[Alert]:
        if not user.access_keys:
            return None

        now = datetime.now(timezone.utc)
        unused_key_ids = []

        for key in user.access_keys:
            if key.status == "Active": # Apenas chaves ativas
                last_used = key.last_used_date
                if last_used is None: # Nunca usada
                    # Se a chave foi criada há mais tempo que o threshold, considera-se não utilizada.
                    # Se foi criada recentemente e nunca usada, pode ser OK.
                    # Para simplificar, se nunca usada E criada há mais de X dias (ex: 7 dias), alerta.
                    # Ou, uma política separada para "Chave Ativa Nunca Usada".
                    # Por agora: se last_used is None E a chave tem mais de N dias de idade.
                    # A data de criação da chave (key.create_date) é importante aqui.
                    if (now - key.create_date).days > self.unused_days_threshold: # Exemplo: se nunca usada e mais antiga que o threshold
                         unused_key_ids.append(f"{key.access_key_id} (nunca utilizada, criada em {key.create_date.strftime('%Y-%m-%d')})")
                elif (now - last_used).days > self.unused_days_threshold:
                    unused_key_ids.append(f"{key.access_key_id} (último uso em {last_used.strftime('%Y-%m-%d')})")

        if unused_key_ids:
            details = {
                "user_name": user.user_name,
                "user_arn": user.arn,
                "unused_keys": unused_key_ids,
                "threshold_days": self.unused_days_threshold
            }
            return Alert(
                id=str(uuid.uuid4()),
                resource_id=user.arn,
                resource_type="IAMUser",
                account_id=account_id or "N/A",
                region="global",
                provider="aws",
                severity=self.severity,
                title=self.title,
                description=f"{self.description} Chaves afetadas: {'; '.join(unused_key_ids)}.",
                policy_id=self.policy_id,
                details=details,
                recommendation=self.recommendation
            )
        return None

class IAMRootUserActiveAccessKeyPolicy(IAMPolicy):
    def __init__(self):
        super().__init__(
            policy_id="IAM_Root_User_Active_Access_Key",
            title="Chave de Acesso Ativa para o Usuário Root da Conta",
            description="O usuário root da conta AWS possui uma ou mais chaves de acesso ativas. O uso de chaves de acesso do root para tarefas diárias é desaconselhado devido às suas permissões irrestritas.",
            severity="Critical",
            recommendation="Exclua todas as chaves de acesso associadas ao usuário root. Utilize roles IAM para acesso programático e administrativo. Guarde as credenciais do root em local seguro e use-as apenas para tarefas que exigem explicitamente o root."
        )

    def check(self, user: IAMUserDataInput, account_id: Optional[str]) -> Optional[Alert]:
        # Identificar o usuário root pode ser feito pelo ARN ou nome.
        # Exemplo ARN root: arn:aws:iam::ACCOUNT_ID:root
        # O nome do usuário root em si não é fixo ('<root_account>' é um placeholder).
        # O collector não marca explicitamente o root user.
        # Vamos assumir que o ARN do root é passado ou podemos identificar pelo ARN.
        is_root_user = ":root" in user.arn.lower() or user.user_name == "<root_account>" # Heurística

        if is_root_user and user.access_keys:
            active_keys = [key.access_key_id for key in user.access_keys if key.status == "Active"]
            if active_keys:
                details = {
                    "user_arn": user.arn, # O ARN do root
                    "active_access_key_ids": active_keys
                }
                return Alert(
                    id=str(uuid.uuid4()),
                    resource_id=user.arn,
                    resource_type="IAMUser", # Ou "IAMRootAccount"
                    account_id=account_id or "N/A",
                    region="global",
                    provider="aws",
                    severity=self.severity,
                    title=self.title,
                    description=f"{self.description} Chaves ativas encontradas: {', '.join(active_keys)}.",
                    policy_id=self.policy_id,
                    details=details,
                    recommendation=self.recommendation
                )
        return None


# --- Lista de Políticas IAM ---
iam_user_policies_to_evaluate: List[IAMPolicy] = [
    IAMUserMFADisabledPolicy(),
    IAMUserUnusedAccessKeysPolicy(unused_days_threshold=90), # Limite de 90 dias como exemplo
    IAMRootUserActiveAccessKeyPolicy(),
]

# Adicionar listas para IAM Roles e IAM Policies (gerenciadas) quando as classes de política forem criadas

# --- Funções de Avaliação ---

def evaluate_iam_user_policies(users_data: List[IAMUserDataInput], account_id: Optional[str]) -> List[Alert]:
    all_alerts: List[Alert] = []
    logger.info(f"Avaliando {len(users_data)} usuários IAM para a conta {account_id or 'N/A'}.")

    for user in users_data:
        if user.error_details:
            logger.warning(f"Skipping IAM user {user.user_name} due to previous collection error: {user.error_details}")
            continue

        for policy in iam_user_policies_to_evaluate:
            try:
                alert = policy.check(user, account_id)
                if alert:
                    all_alerts.append(alert)
            except Exception as e:
                logger.error(f"Error evaluating policy {policy.policy_id} for IAM user {user.user_name}: {e}", exc_info=True)
                all_alerts.append(Alert(
                    id=str(uuid.uuid4()), resource_id=user.arn, resource_type="IAMUser",
                    account_id=account_id or "N/A", region="global", provider="aws",
                    severity="Medium", title=f"Erro ao Avaliar Política {policy.policy_id} para Usuário IAM",
                    description=f"Ocorreu um erro interno ao tentar avaliar a política '{policy.title}' para o usuário {user.user_name}. Detalhe: {str(e)}",
                    policy_id="POLICY_ENGINE_ERROR", details={"failed_policy_id": policy.policy_id, "user_arn": user.arn},
                    recommendation="Verifique os logs do Policy Engine."
                ))

    logger.info(f"Avaliação de Usuários IAM concluída. {len(all_alerts)} alertas gerados.")
    return all_alerts

# Funções para evaluate_iam_role_policies e evaluate_iam_managed_policy_policies serão adicionadas aqui
# quando as respectivas classes de política e listas forem definidas.
# def evaluate_iam_role_policies(roles_data: List[IAMRoleDataInput], account_id: Optional[str]) -> List[Alert]: ...
# def evaluate_iam_managed_policy_policies(policies_data: List[IAMPolicyDataInput], account_id: Optional[str]) -> List[Alert]: ...
