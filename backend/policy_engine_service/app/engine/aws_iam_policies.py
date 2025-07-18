from typing import List, Optional, Dict, Any
from ..schemas.input_data_schema import IAMUserDataInput, IAMUserAccessKeyMetadataInput
from ..schemas.alert_schema import Alert, AlertSeverityEnum
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

# Nova Política: Usuário IAM com Políticas Inline
class IAMUserHasInlinePolicies(IAMPolicy):
    def __init__(self):
        super().__init__(
            policy_id="IAM_User_Has_Inline_Policies",
            title="Usuário IAM Possui Políticas Inline Anexadas",
            description="O usuário IAM possui uma ou mais políticas inline. Políticas inline podem dificultar o gerenciamento e auditoria de permissões em escala.",
            severity="Medium",
            recommendation="Considere substituir políticas inline por políticas gerenciadas pela AWS ou pelo cliente para facilitar o gerenciamento, o versionamento e a reutilização de políticas."
        )

    def check(self, user: IAMUserDataInput, account_id: Optional[str]) -> Optional[Alert]:
        if user.inline_policies and len(user.inline_policies) > 0: # user.inline_policies já é o nome correto do schema
            policy_names = [p.policy_name for p in user.inline_policies if p.policy_name] # p.policy_name já é o nome correto do schema
            details = {
                "user_name": user.user_name,
                "user_arn": user.arn,
                "inline_policy_names": policy_names,
                "inline_policies_count": len(user.inline_policies)
            }
            return Alert(
                id=str(uuid.uuid4()), resource_id=user.arn, resource_type="IAMUser",
                account_id=account_id or "N/A", region="global", provider="aws",
                severity=self.severity, title=self.title,
                description=f"{self.description} Políticas inline encontradas: {', '.join(policy_names)}.",
                policy_id=self.policy_id, details=details, recommendation=self.recommendation
            )
        return None
iam_user_policies_to_evaluate.append(IAMUserHasInlinePolicies())


# Nova Política: Chave de Acesso do Usuário precisa de rotação (ex: > 90 dias)
ACCESS_KEY_ROTATION_THRESHOLD_DAYS = 90
class IAMUserAccessKeyRotationNeeded(IAMPolicy):
    def __init__(self):
        super().__init__(
            policy_id="IAM_User_AccessKey_Needs_Rotation",
            title=f"Chave de Acesso do Usuário IAM Mais Antiga que {ACCESS_KEY_ROTATION_THRESHOLD_DAYS} Dias",
            description=f"Uma ou mais chaves de acesso ativas para o usuário IAM têm mais de {ACCESS_KEY_ROTATION_THRESHOLD_DAYS} dias. Chaves de acesso de longa duração aumentam o risco se comprometidas.",
            severity="Medium",
            recommendation=f"Rotacione as chaves de acesso IAM regularmente, pelo menos a cada {ACCESS_KEY_ROTATION_THRESHOLD_DAYS} dias. Exclua chaves antigas após a rotação bem-sucedida."
        )

    def check(self, user: IAMUserDataInput, account_id: Optional[str]) -> Optional[Alert]:
        alerts_list: List[Alert] = [] # Um usuário pode ter múltiplas chaves que precisam de rotação
        if not user.access_keys:
            return None

        now = datetime.now(timezone.utc)
        for key in user.access_keys:
            if key.status == "Active":
                age_days = (now - key.create_date).days
                if age_days > ACCESS_KEY_ROTATION_THRESHOLD_DAYS:
                    details = {
                        "user_name": user.user_name,
                        "access_key_id": key.access_key_id,
                        "created_date": key.create_date.isoformat(),
                        "age_days": age_days,
                        "rotation_threshold_days": ACCESS_KEY_ROTATION_THRESHOLD_DAYS
                    }
                    alerts_list.append(Alert(
                        id=str(uuid.uuid4()), resource_id=key.access_key_id, resource_type="AWS::IAM::AccessKey",
                        account_id=account_id or "N/A", region="global", provider="aws",
                        severity=self.severity, title=self.title,
                        description=f"Chave de acesso '{key.access_key_id}' para o usuário '{user.user_name}' tem {age_days} dias.",
                        policy_id=self.policy_id, details=details, recommendation=self.recommendation
                    ))
        return alerts_list if alerts_list else None # Retorna lista de alertas ou None
iam_user_policies_to_evaluate.append(IAMUserAccessKeyRotationNeeded())


# --- Políticas para Roles IAM ---
iam_role_policies_to_evaluate: List[IAMPolicy] = [] # Lista para políticas de Role

class IAMRoleHasInlinePolicies(IAMPolicy):
    def __init__(self):
        super().__init__(
            policy_id="IAM_Role_Has_Inline_Policies",
            title="Role IAM Possui Políticas Inline Anexadas",
            description="A role IAM possui uma ou mais políticas inline. Políticas inline podem dificultar o gerenciamento e auditoria de permissões.",
            severity="Medium",
            recommendation="Considere substituir políticas inline por políticas gerenciadas pela AWS ou pelo cliente para facilitar o gerenciamento e a reutilização."
        )

    def check(self, role: IAMRoleDataInput, account_id: Optional[str]) -> Optional[Alert]:
        if role.inline_policies and len(role.inline_policies) > 0: # role.inline_policies já é o nome correto do schema
            policy_names = [p.policy_name for p in role.inline_policies if p.policy_name] # p.policy_name já é o nome correto do schema
            details = {
                "role_name": role.role_name, # role.role_name é o correto
                "role_arn": role.arn, # role.arn é o correto
                "inline_policy_names": policy_names,
                "inline_policies_count": len(role.inline_policies)
            }
            return Alert(
                id=str(uuid.uuid4()), resource_id=role.arn, resource_type="IAMRole",
                account_id=account_id or "N/A", region="global", provider="aws",
                severity=self.severity, title=self.title,
                description=f"{self.description} Políticas inline encontradas: {', '.join(policy_names)}.",
                policy_id=self.policy_id, details=details, recommendation=self.recommendation
            )
        return None
iam_role_policies_to_evaluate.append(IAMRoleHasInlinePolicies())


class IAMRootAccountMFAPolicy(IAMPolicy):
    def __init__(self):
        super().__init__(
            policy_id="CIS-AWS-1.1",
            title="MFA para usuário Root",
            description="O MFA (Multi-Factor Authentication) deve estar habilitado para o usuário 'root' da conta AWS para aumentar a segurança.",
            severity="Critical",
            recommendation="Habilite o MFA para o usuário root no console do IAM."
        )

    def check(self, user: IAMUserDataInput, account_id: Optional[str]) -> Optional[Alert]:
        # Esta política só precisa ser executada uma vez por conta.
        # Ela é acionada pelo primeiro usuário na lista que contém o sumário.
        if user.account_summary:
            # O get_account_summary retorna 1 se MFA está habilitado, 0 se não.
            if user.account_summary.get("AccountMFAEnabled", 0) == 0:
                return Alert(
                    id=str(uuid.uuid4()),
                    resource_id=f"arn:aws:iam::{account_id}:root",
                    resource_type="IAMRootAccount",
                    account_id=account_id or "N/A",
                    region="global",
                    provider="aws",
                    severity=self.severity,
                    title=self.title,
                    description=self.description,
                    policy_id=self.policy_id,
                    details={"summary": user.account_summary},
                    recommendation=self.recommendation
                )
        return None

import json
from datetime import datetime, timezone, timedelta

iam_user_policies_to_evaluate.append(IAMRootAccountMFAPolicy())

def check_stale_key_s3_write_access(users_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Verifica se um usuário tem uma chave de acesso antiga (>90 dias) e permissão de escrita em S3.
    ATTACK-PATH-IAM-S3-1
    """
    alerts = []
    ninety_days_ago = datetime.now(timezone.utc) - timedelta(days=90)

    for user in users_data:
        if not user.get("access_keys"):
            continue

        stale_keys = []
        for key in user.get("access_keys", []):
            if key.get("Status") == "Active":
                last_used_str = key.get("LastUsedDate")
                create_date_str = key.get("CreateDate")

                last_used = datetime.fromisoformat(last_used_str) if last_used_str else None
                create_date = datetime.fromisoformat(create_date_str) if create_date_str else None

                # Considera a chave antiga se nunca foi usada e foi criada há mais de 90 dias,
                # ou se foi usada pela última vez há mais de 90 dias.
                is_stale = (last_used is None and create_date and create_date < ninety_days_ago) or \
                           (last_used and last_used < ninety_days_ago)

                if is_stale:
                    stale_keys.append(key.get("AccessKeyId"))

        if stale_keys:
            # A chave está antiga. Agora, verifique as permissões de escrita em S3.
            # Esta é uma verificação simplificada. Uma real precisaria de um resolvedor de políticas complexo.
            has_s3_write = False
            for policy in user.get("attached_policies", []) + user.get("inline_policies", []):
                policy_doc_str = policy.get("policy_document", "{}")
                policy_doc = json.loads(policy_doc_str) if isinstance(policy_doc_str, str) else policy_doc_str

                for stmt in policy_doc.get("Statement", []):
                    if stmt.get("Effect") == "Allow":
                        actions = stmt.get("Action", [])
                        if isinstance(actions, str) and ("s3:PutObject" in actions or "s3:*" in actions):
                            has_s3_write = True
                            break
                        elif isinstance(actions, list) and any("s3:PutObject" in a or "s3:*" in a for a in actions):
                            has_s3_write = True
                            break
                if has_s3_write:
                    break

            if has_s3_write:
                alerts.append({
                    "resource_id": user.get("arn"),
                    "resource_type": "IAMUser",
                    "region": "global",
                    "status": "FAIL",
                    "details": f"O usuário '{user.get('user_name')}' tem chaves de acesso antigas ({', '.join(stale_keys)}) e permissões de escrita em S3."
                })

    return alerts

# --- Funções de Avaliação ---

def evaluate_iam_user_policies(users_data: List[IAMUserDataInput], account_id: Optional[str]) -> List[Dict[str, Any]]:
    all_alerts_data: List[Dict[str, Any]] = []
    if not users_data: return all_alerts_data
    logger.info(f"Avaliando {len(users_data)} usuários IAM para a conta {account_id or 'N/A'}.")

    for user in users_data:
        if user.error_details:
            logger.warning(f"Skipping IAM user {user.user_name} due to previous collection error: {user.error_details}")
            # Adicionar alerta informativo sobre falha na coleta do usuário
            all_alerts_data.append({
                "resource_id": user.user_name or user.arn or "UnknownUser",
                "resource_type": "IAMUser", "provider": "aws", "severity": "Informational",
                "title": "Falha na Coleta de Detalhes do Usuário IAM",
                "description": f"Não foi possível coletar todos os detalhes para o usuário IAM '{user.user_name or user.user_id}'. Erro: {user.error_details}",
                "policy_id": "IAM_User_Collection_Error", "account_id": account_id, "region": "global",
                "details": {"user_info": user.user_name or user.user_id, "error": user.error_details}
            })
            continue

        for policy in iam_user_policies_to_evaluate:
            try:
                # O método check pode retornar um único Alert ou uma Lista de Alerts
                result = policy.check(user, account_id)
                if result:
                    if isinstance(result, list):
                        for alert_obj in result:
                            all_alerts_data.append(alert_obj.model_dump()) # Pydantic V2
                            # all_alerts_data.append(alert_obj.dict()) # Pydantic V1
                    else: # Single Alert object
                        all_alerts_data.append(result.model_dump()) # Pydantic V2
                        # all_alerts_data.append(result.dict()) # Pydantic V1
            except Exception as e:
                logger.error(f"Error evaluating policy {policy.policy_id} for IAM user {user.user_name}: {e}", exc_info=True)
                all_alerts_data.append(Alert(
                    id=str(uuid.uuid4()), resource_id=user.arn, resource_type="IAMUser",
                    account_id=account_id or "N/A", region="global", provider="aws",
                    severity="Medium", title=f"Erro ao Avaliar Política {policy.policy_id} para Usuário IAM",
                    description=f"Ocorreu um erro interno ao tentar avaliar a política '{policy.title}' para o usuário {user.user_name}. Detalhe: {str(e)}",
                    policy_id="POLICY_ENGINE_ERROR", details={"failed_policy_id": policy.policy_id, "user_arn": user.arn},
                    recommendation="Verifique os logs do Policy Engine."
                ).model_dump()) # Pydantic V2

    logger.info(f"Avaliação de Usuários IAM concluída. {len(all_alerts_data)} alertas gerados.")
    return all_alerts_data

# Funções para evaluate_iam_role_policies e evaluate_iam_managed_policy_policies serão adicionadas aqui
def evaluate_iam_role_policies(roles_data: List[IAMRoleDataInput], account_id: Optional[str]) -> List[Dict[str, Any]]:
    all_alerts_data: List[Dict[str, Any]] = []
    if not roles_data: return all_alerts_data
    logger.info(f"Avaliando {len(roles_data)} roles IAM para a conta {account_id or 'N/A'}.")

    for role_item in roles_data: # Renomeado para role_item para evitar conflito com o módulo role
        if role_item.error_details:
            logger.warning(f"Skipping IAM role {role_item.role_name} due to collection error: {role_item.error_details}")
            all_alerts_data.append({
                "resource_id": role_item.role_name or role_item.arn or "UnknownRole",
                "resource_type": "IAMRole", "provider": "aws", "severity": "Informational",
                "title": "Falha na Coleta de Detalhes da Role IAM",
                "description": f"Não foi possível coletar todos os detalhes para a role IAM '{role_item.role_name}'. Erro: {role_item.error_details}",
                "policy_id": "IAM_Role_Collection_Error", "account_id": account_id, "region": "global",
                "details": {"role_info": role_item.role_name or role_item.arn, "error": role_item.error_details}
            })
            continue
        for policy in iam_role_policies_to_evaluate:
            try:
                result = policy.check(role_item, account_id)
                if result:
                    if isinstance(result, list):
                         for alert_obj in result: all_alerts_data.append(alert_obj.model_dump())
                    else:
                         all_alerts_data.append(result.model_dump())
            except Exception as e:
                logger.error(f"Error evaluating policy {policy.policy_id} for IAM role {role_item.role_name}: {e}", exc_info=True)
                all_alerts_data.append(Alert(
                    id=str(uuid.uuid4()), resource_id=role_item.arn, resource_type="IAMRole",
                    account_id=account_id or "N/A", region="global", provider="aws",
                    severity="Medium", title=f"Erro ao Avaliar Política {policy.policy_id} para Role IAM",
                    description=f"Ocorreu um erro interno ao tentar avaliar a política '{policy.title}' para a role {role_item.role_name}. Detalhe: {str(e)}",
                    policy_id="POLICY_ENGINE_ERROR", details={"failed_policy_id": policy.policy_id, "role_arn": role_item.arn},
                    recommendation="Verifique os logs do Policy Engine."
                ).model_dump())
    logger.info(f"Avaliação de Roles IAM concluída. {len(all_alerts_data)} alertas gerados.")
    return all_alerts_data

# def evaluate_iam_managed_policy_policies(policies_data: List[IAMPolicyDataInput], account_id: Optional[str]) -> List[Alert]: ...
