from typing import List, Dict, Any, Optional
from ..schemas.m365.m365_input_schemas import (
    M365UserMFAStatusCollectionInput,
    M365ConditionalAccessPolicyCollectionInput,
    M365ConditionalAccessPolicyDetailInput,
)
from ..schemas.alert_schema import AlertSeverityEnum

def evaluate_m365_policies(
    mfa_data: Optional[M365UserMFAStatusCollectionInput],
    ca_policy_data: Optional[M365ConditionalAccessPolicyCollectionInput],
    tenant_id: Optional[str] # tenant_id é o account_id para M365
) -> List[Dict[str, Any]]:
    """
    Avalia todas as políticas M365 para os dados fornecidos.
    Retorna uma lista de dicionários, cada um representando dados para AlertCreate.
    """
    alerts_data: List[Dict[str, Any]] = []

    if mfa_data and not mfa_data.error_message: # Processar apenas se não houver erro global na coleta de MFA
        for user_mfa_status in mfa_data.users_mfa_status:
            if user_mfa_status.error_details: # Pular usuário com erro de coleta individual
                # Opcional: criar um alerta informativo sobre falha na coleta para este usuário
                alerts_data.append({
                    "resource_id": user_mfa_status.user_principal_name,
                    "resource_type": "Microsoft365::User",
                    "provider": "microsoft365",
                    "severity": AlertSeverityEnum.INFORMATIONAL,
                    "title": "M365 User MFA Status Collection Issue",
                    "description": f"Could not fully assess MFA status for user '{user_mfa_status.user_principal_name}' due to: {user_mfa_status.error_details}",
                    "policy_id": "M365_MFA_Collection_Error",
                    "account_id": tenant_id,
                    "details": {"user_principal_name": user_mfa_status.user_principal_name, "error": user_mfa_status.error_details}
                })
                continue
            alerts_data.extend(check_m365_user_mfa_disabled(user_mfa_status, tenant_id))
    elif mfa_data and mfa_data.error_message:
        alerts_data.append({
            "resource_id": tenant_id or "M365Tenant",
            "resource_type": "Microsoft365::Tenant",
            "provider": "microsoft365",
            "severity": AlertSeverityEnum.MEDIUM,
            "title": "M365 User MFA Status Global Collection Failed",
            "description": f"Failed to collect MFA status for users in tenant '{tenant_id}': {mfa_data.error_message}",
            "policy_id": "M365_MFA_GlobalCollection_Error",
            "account_id": tenant_id,
            "details": {"error": mfa_data.error_message}
        })


    if ca_policy_data and not ca_policy_data.error_message: # Processar apenas se não houver erro global na coleta de CA
        for ca_policy in ca_policy_data.policies:
            if ca_policy.error_details:
                alerts_data.append({
                    "resource_id": ca_policy.id,
                    "resource_type": "Microsoft365::ConditionalAccessPolicy",
                    "provider": "microsoft365",
                    "severity": AlertSeverityEnum.INFORMATIONAL,
                    "title": "M365 CA Policy Data Collection Issue",
                    "description": f"Could not fully assess CA policy '{ca_policy.display_name}' (ID: {ca_policy.id}) due to: {ca_policy.error_details}",
                    "policy_id": "M365_CAPolicy_Collection_Error",
                    "account_id": tenant_id,
                    "details": {"policy_id": ca_policy.id, "policy_name": ca_policy.display_name, "error": ca_policy.error_details}
                })
                continue
            alerts_data.extend(check_m365_ca_policy_disabled(ca_policy, tenant_id))
    elif ca_policy_data and ca_policy_data.error_message:
        alerts_data.append({
            "resource_id": tenant_id or "M365Tenant",
            "resource_type": "Microsoft365::Tenant",
            "provider": "microsoft365",
            "severity": AlertSeverityEnum.MEDIUM,
            "title": "M365 CA Policies Global Collection Failed",
            "description": f"Failed to collect Conditional Access policies for tenant '{tenant_id}': {ca_policy_data.error_message}",
            "policy_id": "M365_CAPolicy_GlobalCollection_Error",
            "account_id": tenant_id,
            "details": {"error": ca_policy_data.error_message}
        })

    return alerts_data

from ..schemas.m365.m365_input_schemas import M365UserMFADetailInput
def check_m365_user_mfa_disabled(
    user_mfa: M365UserMFADetailInput,
    tenant_id: Optional[str]
) -> List[Dict[str, Any]]:
    """
    Política: M365_User_MFA_Disabled
    Alerta se o MFA não está registrado ou não está efetivamente imposto para o usuário.
    Para o MVP, consideramos `is_mfa_registered == False` como uma falha.
    `mfa_state` pode ser: "NotRegistered", "Registered", "Enforced", "RegisteredNotEnforcedBySecurityDefaults"
    """
    alerts_data: List[Dict[str, Any]] = []

    # Considerar uma issue se mfa_state for "NotRegistered" ou se is_mfa_registered for explicitamente False.
    # A API credentialUserRegistrationDetails tem `isRegistered` e `isEnabled`.
    # `isEnabled` significa "MFA is capable and will be enforced by Azure AD (such as when security defaults is enabled)"
    # `isRegistered` significa "MFA is registered for the user"
    # Um usuário pode ser registrado mas não ter MFA imposto em cada login se depender de CA policies.
    # Para um CSPM, o ideal é alertar se o usuário não estiver protegido por MFA na prática.
    # Se `is_mfa_registered` for False, é um alerta claro.
    # Se `is_mfa_registered` for True mas `is_mfa_enabled_via_policies` (nosso mapeamento de `isEnabled`) for False,
    # significa que o MFA não é imposto por default, e dependeria de CA. Isso pode ser um alerta de menor severidade.

    issue_found = False
    description = ""
    severity = AlertSeverityEnum.HIGH # Default para MFA não registrado

    if user_mfa.is_mfa_registered is False or user_mfa.mfa_state == "NotRegistered":
        issue_found = True
        description = f"User '{user_mfa.user_principal_name}' in tenant '{tenant_id}' does not have MFA registered. This significantly increases the risk of account compromise."
        severity = AlertSeverityEnum.CRITICAL
    elif user_mfa.is_mfa_registered is True and user_mfa.is_mfa_enabled_via_policies is False:
        # Usuário registrou MFA, mas Security Defaults (que impõe MFA para todos) pode estar desligado.
        # O MFA pode ainda ser imposto por Políticas de Acesso Condicional.
        # Para um CSPM, este é um estado que merece atenção, talvez com severidade Média.
        issue_found = True
        description = f"User '{user_mfa.user_principal_name}' in tenant '{tenant_id}' has MFA registered, but it might not be enforced for all sign-ins (e.g., Security Defaults might be off, relying on Conditional Access policies). Review CA policies to ensure comprehensive MFA coverage."
        severity = AlertSeverityEnum.MEDIUM


    if issue_found:
        alerts_data.append({
            "resource_id": user_mfa.user_id, # ID do objeto do usuário
            "resource_type": "Microsoft365::User",
            "provider": "microsoft365",
            "severity": severity,
            "title": "M365 User MFA Not Effectively Enforced",
            "description": description,
            "policy_id": "M365_User_MFA_Status_Issue", # Policy ID mais genérico
            "account_id": tenant_id,
            "region": None, # M365/Azure AD é global para usuários
            "details": {
                "user_principal_name": user_mfa.user_principal_name,
                "mfa_registered": user_mfa.is_mfa_registered,
                "mfa_enforced_by_security_defaults_or_similar": user_mfa.is_mfa_enabled_via_policies,
                "current_mfa_state_reported": user_mfa.mfa_state,
            },
            "recommendation": "Ensure all users, especially administrative accounts, have strong MFA registered and enforced. Utilize Security Defaults or comprehensive Conditional Access policies to enforce MFA."
        })
    return alerts_data

def check_m365_ca_policy_disabled(
    ca_policy: M365ConditionalAccessPolicyDetailInput,
    tenant_id: Optional[str]
) -> List[Dict[str, Any]]:
    """
    Política: M365_ConditionalAccess_Policy_Disabled
    Alerta se uma Política de Acesso Condicional está desabilitada.
    """
    alerts_data: List[Dict[str, Any]] = []
    # state pode ser "enabled", "disabled", ou "enabledForReportingButNotEnforced"
    if ca_policy.state == "disabled":
        alerts_data.append({
            "resource_id": ca_policy.id,
            "resource_type": "Microsoft365::ConditionalAccessPolicy",
            "provider": "microsoft365",
            "severity": AlertSeverityEnum.MEDIUM, # Desabilitar uma CA policy pode ser intencional, mas merece revisão.
            "title": "M365 Conditional Access Policy Disabled",
            "description": f"The Conditional Access policy '{ca_policy.display_name}' (ID: {ca_policy.id}) in tenant '{tenant_id}' is currently disabled. Review if this is intentional, as disabled policies are not enforced.",
            "policy_id": "M365_ConditionalAccess_Policy_Disabled",
            "account_id": tenant_id,
            "region": None, # CA Policies são globais
            "details": {
                "policy_id": ca_policy.id,
                "policy_name": ca_policy.display_name,
                "current_state": ca_policy.state,
            },
            "recommendation": "Review the purpose of the Conditional Access policy. If it's intended to be active, change its state to 'enabled'. If it's no longer needed, consider deleting it to simplify management."
        })
    elif ca_policy.state == "enabledForReportingButNotEnforced":
        alerts_data.append({
            "resource_id": ca_policy.id,
            "resource_type": "Microsoft365::ConditionalAccessPolicy",
            "provider": "microsoft365",
            "severity": AlertSeverityEnum.INFORMATIONAL, # Modo "Report-only" é para teste.
            "title": "M365 Conditional Access Policy in Report-Only Mode",
            "description": f"The Conditional Access policy '{ca_policy.display_name}' (ID: {ca_policy.id}) in tenant '{tenant_id}' is in 'Report-only' mode. It logs a Ccesso Condicional, mas não impõe restrições.",
            "policy_id": "M365_ConditionalAccess_Policy_ReportOnly",
            "account_id": tenant_id,
            "region": None,
            "details": {
                "policy_id": ca_policy.id,
                "policy_name": ca_policy.display_name,
                "current_state": ca_policy.state,
            },
            "recommendation": "Monitor the impact of the policy in report-only mode. If the behavior is as expected and the policy is intended to be active, change its state to 'enabled' to enforce it."
        })
    return alerts_data
