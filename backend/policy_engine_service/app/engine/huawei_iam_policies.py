from typing import List, Optional, Dict, Any
from app.schemas.input_data_schema import HuaweiIAMUserDataInput, HuaweiIAMUserAccessKeyInput # Alterado para Input
from app.schemas.alert_schema import Alert
import logging
import uuid
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# --- Estrutura Base para Políticas Huawei IAM ---
class HuaweiIAMPolicyDefinition:
    def __init__(self, policy_id: str, title: str, description: str, severity: str, recommendation: str):
        self.policy_id = policy_id
        self.title = title
        self.description = description
        self.severity = severity
        self.recommendation = recommendation

    def check(self, user: HuaweiIAMUserDataInput, account_id: Optional[str]) -> Optional[Alert]: # account_id aqui é domain_id
        raise NotImplementedError

# --- Definições de Políticas para Huawei IAM Users ---

class HuaweiIAMUserMFADisabledPolicy(HuaweiIAMPolicyDefinition):
    def __init__(self):
        super().__init__(
            policy_id="HUAWEI_IAM_User_MFA_Disabled",
            title="Usuário IAM da Huawei Cloud sem MFA Habilitado para Console",
            description="O usuário IAM não possui MFA (Autenticação Multi-Fator) habilitado para login no console. MFA adiciona uma camada crucial de segurança.",
            severity="High", # Considerar Critical para o usuário root/admin da conta
            recommendation="Habilite um dispositivo MFA para o usuário IAM para login no console. Para o usuário administrador da conta, isso é especialmente crítico."
        )

    def check(self, user: HuaweiIAMUserDataInput, account_id: Optional[str]) -> Optional[Alert]:
        # A informação de MFA para console está em user.login_protect.enabled
        if user.login_protect is None or not user.login_protect.enabled:
            # Identificar se é o usuário root/admin da conta pode ser complexo sem um campo explícito.
            # O nome 'root' não é padrão. A criticidade pode ser ajustada se o usuário tiver papéis administrativos.
            current_severity = self.severity
            # if user_is_admin_equivalent: current_severity = "Critical"

            details = {
                "user_name": user.name,
                "user_id": user.id,
                "domain_id": account_id or user.domain_id or "N/A",
                "mfa_console_status": "Disabled or Not Configured"
            }
            return Alert(
                id=str(uuid.uuid4()),
                resource_id=user.id,
                resource_type="HuaweiIAMUser",
                account_id=details["domain_id"],
                region="global", # IAM é global
                provider="huawei",
                severity=current_severity,
                title=self.title,
                description=self.description,
                policy_id=self.policy_id,
                details=details,
                recommendation=self.recommendation
            )
        return None

class HuaweiIAMUserInactiveAccessKeyPolicy(HuaweiIAMPolicyDefinition):
    def __init__(self, inactive_days_threshold: int = 90):
        self.inactive_days_threshold = inactive_days_threshold
        super().__init__(
            policy_id="HUAWEI_IAM_User_Inactive_Access_Key",
            title=f"Chave de Acesso IAM da Huawei Cloud Inativa (ou não usada) por mais de {inactive_days_threshold} dias",
            description=f"Uma ou mais chaves de acesso (AK/SK) do usuário IAM estão ativas mas não foram usadas nos últimos {inactive_days_threshold} dias, ou estão inativas. Chaves não utilizadas ou inativas desnecessariamente aumentam o risco.",
            severity="Medium",
            recommendation=f"Revise as chaves de acesso. Se uma chave ativa não é usada há mais de {inactive_days_threshold} dias, considere desativá-la ou rotacioná-la. Exclua chaves inativas se não forem mais necessárias."
        )

    def check(self, user: HuaweiIAMUserDataInput, account_id: Optional[str]) -> Optional[Alert]:
        if not user.access_keys:
            return None

        now = datetime.now(timezone.utc)
        problematic_keys_details = []

        for key in user.access_keys:
            if key.status.lower() == "inactive":
                problematic_keys_details.append(f"Key ID '{key.access_key}' is Inactive (Created: {key.create_time.strftime('%Y-%m-%d') if key.create_time else 'N/A'}).")
            elif key.status.lower() == "active":
                # O SDK da Huawei para ListPermanentAccessKeys não retorna last_used_time diretamente.
                # Esta informação precisaria vir de uma API de análise de credenciais ou Cloud Trace (CT).
                # Para este MVP, se a política for sobre "não usada por X dias", e não temos 'last_used_date',
                # podemos focar na idade da chave ativa. Se uma chave ativa tem mais de X dias e não temos
                # info de último uso, podemos alertar com uma severidade menor ou uma descrição diferente.
                # Por enquanto, vamos focar em chaves 'Inactive'.
                # Se 'last_used_date' fosse adicionado ao schema HuaweiIAMUserAccessKeyInput e populado pelo collector:
                # if key.last_used_date:
                #     if (now - key.last_used_date).days > self.inactive_days_threshold:
                #         problematic_keys_details.append(f"Active Key ID '{key.access_key}' last used on {key.last_used_date.strftime('%Y-%m-%d')} (>{self.inactive_days_threshold} days ago).")
                # elif key.create_time and (now - key.create_time).days > self.inactive_days_threshold:
                #     problematic_keys_details.append(f"Active Key ID '{key.access_key}' created on {key.create_time.strftime('%Y-%m-%d')} (>{self.inactive_days_threshold} days ago) and never used (or last use unknown).")
                pass # Sem last_used_date, não podemos implementar a parte de "não usada" desta política.

        if problematic_keys_details:
            details = {
                "user_name": user.name,
                "user_id": user.id,
                "domain_id": account_id or user.domain_id or "N/A",
                "inactive_or_old_unused_keys": problematic_keys_details
            }
            # Ajustar título e descrição se apenas chaves inativas forem detectadas.
            current_title = self.title
            current_description = self.description
            if all("Inactive" in s for s in problematic_keys_details):
                current_title = "Usuário IAM da Huawei Cloud com Chaves de Acesso Inativas"
                current_description = "O usuário IAM possui uma ou mais chaves de acesso (AK/SK) que estão no estado 'Inactive'."

            return Alert(
                id=str(uuid.uuid4()),
                resource_id=user.id,
                resource_type="HuaweiIAMUser",
                account_id=details["domain_id"],
                region="global",
                provider="huawei",
                severity=self.severity, # Pode ser ajustado com base no tipo de problema
                title=current_title,
                description=f"{current_description} Detalhes: {'; '.join(problematic_keys_details)}",
                policy_id=self.policy_id,
                details=details,
                recommendation=self.recommendation
            )
        return None

# --- Lista de Políticas ---
huawei_iam_user_policies_to_evaluate: List[HuaweiIAMPolicyDefinition] = [
    HuaweiIAMUserMFADisabledPolicy(),
    HuaweiIAMUserInactiveAccessKeyPolicy(inactive_days_threshold=90), # Focará em chaves inativas devido à falta de last_used_date
]

# --- Funções de Avaliação ---
def evaluate_huawei_iam_user_policies(
    users_data: List[HuaweiIAMUserDataInput],
    account_id: Optional[str] # domain_id da requisição de análise
) -> List[Alert]:
    all_alerts: List[Alert] = []
    logger.info(f"Avaliando {len(users_data)} usuários Huawei IAM para a conta/domínio {account_id or 'N/A'}.")

    for user in users_data:
        if user.error_details:
            logger.warning(f"Skipping Huawei IAM user {user.name} due to collection error: {user.error_details}")
            continue

        # O account_id da requisição é o domain_id.
        # O user.domain_id deve ser o mesmo, mas usamos o da requisição para consistência no alerta.
        effective_domain_id_for_alert = account_id or user.domain_id

        for policy_def in huawei_iam_user_policies_to_evaluate:
            try:
                alert = policy_def.check(user, effective_domain_id_for_alert)
                if alert:
                    all_alerts.append(alert)
            except Exception as e:
                logger.error(f"Error evaluating policy {policy_def.policy_id} for Huawei IAM user {user.name}: {e}", exc_info=True)
                # Criar alerta de erro de engine

    logger.info(f"Avaliação de Usuários Huawei IAM concluída para {account_id or 'N/A'}. {len(all_alerts)} alertas gerados.")
    return all_alerts
