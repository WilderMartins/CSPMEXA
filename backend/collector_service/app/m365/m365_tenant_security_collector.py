import asyncio
import httpx
import logging
from typing import List, Dict, Any, Optional

from app.m365.m365_client_manager import m365_client_manager, GRAPH_API_BASE_URL
from app.schemas.m365.m365_security_schemas import (
    M365UserMFADetail,
    M365UserMFAStatusCollection,
    M365ConditionalAccessPolicyDetail
    # M365UserMFAMethod # Não usado diretamente na coleção, mas parte do schema M365UserMFADetail se fosse mais detalhado
)

logger = logging.getLogger(__name__)

# --- Coletor de Status de MFA de Usuários ---
async def get_m365_users_mfa_status() -> M365UserMFAStatusCollection:
    """
    Coleta o status de MFA para usuários do M365 usando a API /reports/credentialUserRegistrationDetails.
    Requer permissão de API Graph: AuditLog.Read.All ou Reports.Read.All.
    """
    all_users_mfa_details: List[M365UserMFADetail] = []
    total_scanned = 0
    total_with_issues = 0
    error_msg_global: Optional[str] = None

    graph_client = await m365_client_manager.get_graph_client()
    if not graph_client:
        return M365UserMFAStatusCollection(error_message="Failed to get authenticated Graph API client for MFA status.")

    try:
        async with graph_client:
            # Usar a API de relatórios para detalhes de registro de credenciais
            # Esta API fornece informações sobre o status de registro de MFA.
            mfa_report_endpoint = "/reports/credentialUserRegistrationDetails"
            # Campos relevantes: id, userPrincipalName, isRegistered, isEnabled, authMethods (lista de strings)
            # authMethods: ["email", "mobilePhone", "officePhone", "securityQuestion", "appPassword",
            #               "microsoftAuthenticatorPush", "softwareOneTimePasscode", "fido2SecurityKey",
            #               "windowsHelloForBusiness", "microsoftPin", "passwordlessMobilePhone"]
            # "isCompliant" e "isMfaRegistered" também são interessantes.
            # Vamos focar em isRegistered, isEnabled e authMethods.

            select_fields = "id,userPrincipalName,displayName,isRegistered,isEnabled,authMethods" # displayName não está em credentialUserRegistrationDetails, precisaria de outra chamada ou join
            # Para obter displayName, precisaríamos primeiro obter todos os usuários e depois enriquecer.
            # Por simplicidade inicial, vamos focar nos dados do report.
            # O schema M365UserMFADetail tem displayName, então precisaremos ajustá-lo ou fazer a chamada adicional.
            # Por agora, vou remover displayName da query e do preenchimento para simplificar.

            # Ajuste: Primeiro pegar todos os UPNs e IDs, depois o report de MFA.
            # Ou, mais simples, pegar o report e não ter o displayName.
            # Vamos pela simplicidade primeiro, sem displayName do report de MFA.

            select_fields_report = "id,userPrincipalName,isRegistered,isEnabled,authMethods"
            users_report_endpoint = f"{mfa_report_endpoint}?$select={select_fields_report}"

            next_link: Optional[str] = users_report_endpoint
            while next_link:
                url_to_call = next_link
                if not next_link.startswith("https://"):
                    url_to_call = f"{GRAPH_API_BASE_URL}{next_link}"

                logger.info(f"Fetching M365 MFA registration details from: {url_to_call.split('?')[0]}...")
                response = await graph_client.get(url_to_call)

                if response.status_code != 200:
                    error_detail = f"Error fetching MFA registration details: {response.status_code} - {response.text[:200]}"
                    logger.error(error_detail)
                    if not all_users_mfa_details:
                        return M365UserMFAStatusCollection(error_message=error_detail)
                    error_msg_global = (error_msg_global or "") + error_detail + "; "
                    break

                data = response.json()
                report_entries = data.get("value", [])

                for entry in report_entries:
                    total_scanned += 1

                    is_mfa_registered = entry.get("isRegistered", False) # Se MFA está registrado
                    is_mfa_enabled_by_policy = entry.get("isEnabled", False) # Se MFA é imposto (ex: via Security Defaults)

                    # authMethods é uma lista de strings como "microsoftAuthenticatorPush", "sms"
                    registered_methods = entry.get("authMethods", [])

                    mfa_state = "NotRegistered"
                    if is_mfa_registered:
                        mfa_state = "Registered"
                        if is_mfa_enabled_by_policy: # isEnabled aqui significa "MFA is capable and will be enforced by Azure AD"
                            mfa_state = "Enforced"
                        else: # Registrado mas não necessariamente imposto em cada login (pode ser por Acesso Condicional)
                            mfa_state = "RegisteredNotEnforcedBySecurityDefaults"

                    # Definir "issue" se não estiver registrado ou se usa métodos fracos (ex: só SMS)
                    # Para este MVP, consideramos "não registrado" como uma issue.
                    # Uma análise mais profunda de "métodos fracos" pode ser adicionada depois.
                    has_issue = not is_mfa_registered
                    if has_issue:
                        total_with_issues += 1

                    all_users_mfa_details.append(M365UserMFADetail(
                        user_id=entry.get("id"), # Este é o ID do objeto do usuário Azure AD
                        user_principal_name=entry.get("userPrincipalName"),
                        display_name=entry.get("userPrincipalName"), # Usar UPN como fallback para displayName, já que o report não o tem
                        is_mfa_registered=is_mfa_registered,
                        is_mfa_enabled_via_policies=is_mfa_enabled_by_policy, # Mapear isEnabled do report
                        mfa_state=mfa_state
                        # Adicionar registered_auth_methods=registered_methods ao schema se quisermos guardar isso
                    ))

                next_link = data.get("@odata.nextLink")
                if next_link and next_link.startswith(GRAPH_API_BASE_URL):
                    next_link = next_link.replace(GRAPH_API_BASE_URL, "")

    except httpx.HTTPStatusError as e:
        error_msg_global = f"Graph API request for MFA status failed: {e.response.status_code} - {e.response.text[:200]}"
        logger.error(error_msg_global)
    except Exception as e:
        error_msg_global = f"Unexpected error collecting M365 MFA status: {str(e)}"
        logger.exception(error_msg_global)

    return M365UserMFAStatusCollection(
        users_mfa_status=all_users_mfa_details,
        total_users_scanned=total_scanned,
        total_users_with_mfa_issues=total_with_issues,
        error_message=error_msg_global
    )

# --- Coletor de Políticas de Acesso Condicional ---
async def get_m365_conditional_access_policies() -> M365ConditionalAccessPolicyCollection:
    """
    Coleta informações sobre as Políticas de Acesso Condicional do M365/Azure AD.
    Requer permissão de API Graph: Policy.Read.All
    """
    policies_details: List[M365ConditionalAccessPolicyDetail] = []
    error_msg_global: Optional[str] = None

    graph_client = await m365_client_manager.get_graph_client()
    if not graph_client:
        return M365ConditionalAccessPolicyCollection(error_message="Failed to get authenticated Graph API client.")

    try:
        async with graph_client:
            # Endpoint para listar políticas de Acesso Condicional
            # https://graph.microsoft.com/v1.0/identity/conditionalAccess/policies
            # Ou beta para mais funcionalidades: https://graph.microsoft.com/beta/identity/conditionalAccess/policies
            ca_policies_endpoint = "/identity/conditionalAccess/policies?$select=id,displayName,state"

            next_link: Optional[str] = ca_policies_endpoint
            while next_link:
                url_to_call = next_link
                if not next_link.startswith("https://"):
                     url_to_call = f"{GRAPH_API_BASE_URL}{next_link}"

                logger.info(f"Fetching M365 Conditional Access policies from: {url_to_call.split('?')[0]}...")
                response = await graph_client.get(url_to_call)

                if response.status_code != 200:
                    error_detail = f"Error fetching CA policies: {response.status_code} - {response.text[:200]}"
                    logger.error(error_detail)
                    if not policies_details:
                        return M365ConditionalAccessPolicyCollection(error_message=error_detail)
                    else:
                        # Não há um campo de erro por política no schema, então logar ou adicionar ao global
                        error_msg_global = (error_msg_global or "") + error_detail + "; "
                    break

                data = response.json()
                ca_list = data.get("value", [])

                for policy_data in ca_list:
                    policies_details.append(M365ConditionalAccessPolicyDetail(
                        id=policy_data.get("id"),
                        displayName=policy_data.get("displayName"),
                        state=policy_data.get("state")
                    ))

                next_link = data.get("@odata.nextLink")
                if next_link and next_link.startswith(GRAPH_API_BASE_URL):
                    next_link = next_link.replace(GRAPH_API_BASE_URL, "")

    except httpx.HTTPStatusError as e:
        error_msg_global = f"Graph API request failed for CA policies: {e.response.status_code} - {e.response.text[:200]}"
        logger.error(error_msg_global)
    except Exception as e:
        error_msg_global = f"Unexpected error collecting M365 CA policies: {str(e)}"
        logger.exception(error_msg_global)

    return M365ConditionalAccessPolicyCollection(
        policies=policies_details,
        total_policies_found=len(policies_details),
        error_message=error_msg_global
    )


if __name__ == "__main__":
    # Teste local rápido (requer M365_CLIENT_ID, etc. nas settings)

    # Mock settings para teste local
    class MockM365SettingsMain:
        M365_CLIENT_ID = "SEU_M365_CLIENT_ID"
        M365_TENANT_ID = "SEU_M365_TENANT_ID"
        M365_CLIENT_SECRET = "SEU_M365_CLIENT_SECRET"
        M365_HTTP_CLIENT_TIMEOUT = 30
        # Simular outras settings que o m365_client_manager possa precisar indiretamente de app.core.config
        # Se o settings global for usado, certifique-se que ele está carregado.

    # settings.M365_CLIENT_ID = MockM365SettingsMain.M365_CLIENT_ID
    # settings.M365_TENANT_ID = MockM365SettingsMain.M365_TENANT_ID
    # settings.M365_CLIENT_SECRET = MockM365SettingsMain.M365_CLIENT_SECRET
    # settings.M365_HTTP_CLIENT_TIMEOUT = MockM365SettingsMain.M365_HTTP_CLIENT_TIMEOUT

    async def main_test_m365_collectors():
        if not all([settings.M365_CLIENT_ID, settings.M365_TENANT_ID, settings.M365_CLIENT_SECRET]):
            print("M365 settings not fully configured. Skipping M365 collector tests.")
            return

        print("\n--- Testing M365 User MFA Status Collector ---")
        mfa_collection = await get_m365_users_mfa_status()
        if mfa_collection.error_message:
            print(f"Error collecting MFA Status: {mfa_collection.error_message}")
        else:
            print(f"Scanned {mfa_collection.total_users_scanned} users for MFA status.")
            print(f"Found {mfa_collection.total_users_with_mfa_issues} users with MFA issues (mocked data).")
            # print("Sample MFA Statuses:")
            # for user_mfa in mfa_collection.users_mfa_status[:2]:
            #     print(f"  User: {user_mfa.user_principal_name}, MFA State: {user_mfa.mfa_state}")

        print("\n--- Testing M365 Conditional Access Policies Collector ---")
        ca_policy_collection = await get_m365_conditional_access_policies()
        if ca_policy_collection.error_message:
            print(f"Error collecting CA Policies: {ca_policy_collection.error_message}")
        else:
            print(f"Found {ca_policy_collection.total_policies_found} Conditional Access policies.")
            # print("Sample CA Policies:")
            # for policy in ca_policy_collection.policies[:2]:
            #     print(f"  Policy: {policy.display_name}, State: {policy.state}")

    # asyncio.run(main_test_m365_collectors())
    print("M365 collector structure created. Run with configured M365 App credentials for live test.")
