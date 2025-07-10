from huaweicloudsdkcore.exceptions import exceptions as sdk_exceptions
from huaweicloudsdkiam.v3.model import (
    KeystoneListUsersRequest, # Mantido - usado para listar usuários no domínio
    KeystoneShowUserRequest,  # Mantido - usado para detalhes do usuário
    ListPermanentAccessKeysRequest, # Mantido - usado para listar chaves de acesso
    ListUserMfaDevicesRequest # Mantido - embora não usado ativamente, pode ser útil no futuro
    # ListUsersRequest e ShowUserRequest foram removidos pois não são usados e ListUsersRequest causava ImportError
)
# Outros imports de request/response podem ser necessários

from typing import List, Optional, Dict, Any
from app.schemas.huawei_iam import (
    HuaweiIAMUserData, HuaweiIAMUserLoginProtect, HuaweiIAMUserAccessKey, HuaweiIAMUserMfaDevice
)
from app.huawei.huawei_client_manager import get_iam_client, get_huawei_credentials
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

def _parse_huawei_iam_timestamp(timestamp_str: Optional[str]) -> Optional[datetime]:
    if not timestamp_str:
        return None
    try:
        # Formato comum: "2023-10-27T10:30:00.000000Z" ou "2023-10-27T10:30:00Z"
        if isinstance(timestamp_str, datetime): # Se já for datetime
            if timestamp_str.tzinfo is None:
                return timestamp_str.replace(tzinfo=timezone.utc)
            return timestamp_str.astimezone(timezone.utc)

        if '.' in timestamp_str and timestamp_str.endswith('Z'):
            dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        elif timestamp_str.endswith('Z'):
            dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ")
        elif '.' in timestamp_str: # Sem Z, mas com microssegundos
            dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S.%f")
        else: # Sem Z e sem microssegundos
            dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S")

        if dt.tzinfo is None: # Se o parse resultou em naive datetime
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc) # Normalizar para UTC
    except ValueError as e:
        logger.warning(f"Could not parse Huawei IAM timestamp string '{timestamp_str}': {e}")
        return None


async def get_huawei_iam_users(domain_id: Optional[str] = None, region_id: str = "ap-southeast-1") -> List[HuaweiIAMUserData]:
    """
    Coleta dados de usuários IAM para um domínio (conta) Huawei Cloud.
    IAM na Huawei é geralmente um serviço global, mas o SDK é instanciado com uma região
    para determinar o endpoint. O domain_id é crucial para escopo.
    """
    collected_users: List[HuaweiIAMUserData] = []

    # Obter credenciais para extrair o domain_id se não for fornecido
    # No entanto, o domain_id da conta que executa a chamada pode não ser o mesmo
    # que o domain_id alvo se estivermos listando usuários de outro domínio (menos comum para este caso de uso).
    # Vamos assumir que o domain_id das credenciais é o domínio alvo.

    effective_domain_id = domain_id
    if not effective_domain_id:
        try:
            creds, project_id_from_creds = get_huawei_credentials() # project_id aqui é o default das creds
            # O domain_id pode ser parte do AK (raro) ou configurado junto.
            # O SDK BasicCredentials pode ter domain_id.
            # Se o SDK não expor domain_id facilmente das creds, ele precisa ser uma entrada.
            # Para IAM, o domain_id da conta é o escopo principal.
            # Para simplificar, vamos exigir domain_id ou tentar obtê-lo de uma variável de ambiente específica.
            effective_domain_id = os.getenv("HUAWEICLOUD_SDK_DOMAIN_ID") # Ou project_id se usado como domain scope
            if not effective_domain_id:
                 effective_domain_id = project_id_from_creds # Usar project_id como fallback se for o mesmo que domain_id
                 logger.warning(f"Huawei IAM domain_id not explicitly provided, using project_id from credentials ('{effective_domain_id}') as domain_id. This may not be correct for all setups.")

            if not effective_domain_id:
                msg = "Huawei Cloud Domain ID (HUAWEICLOUD_SDK_DOMAIN_ID) ou como parâmetro é necessário para listar usuários IAM."
                logger.error(msg)
                return [HuaweiIAMUserData(id="ERROR_DOMAIN_ID", name="ERROR_DOMAIN_ID", domain_id="N/A", enabled=False, error_details=msg)]
        except ValueError as ve: # Erro de credenciais
             logger.error(f"Credential error for Huawei IAM: {ve}")
             return [HuaweiIAMUserData(id="ERROR_CREDENTIALS", name="ERROR_CREDENTIALS", domain_id="N/A", enabled=False, error_details=str(ve))]


    try:
        # A região passada para get_iam_client é para ajudar o SDK a encontrar o endpoint IAM global/regional.
        # A documentação/exemplos do SDK devem esclarecer qual região usar para o cliente IAM.
        # Se IAM for global, uma região "mestra" ou qualquer região válida pode funcionar.
        iam_client = get_iam_client(region_id=region_id)
    except ValueError as ve: # Erro de credenciais
        logger.error(f"Credential error for Huawei IAM in region {region_id}: {ve}")
        return [HuaweiIAMUserData(id="ERROR_CREDENTIALS", name="ERROR_CREDENTIALS", domain_id=effective_domain_id, enabled=False, error_details=str(ve))]
    except Exception as e:
        logger.error(f"Failed to initialize IAM client for region {region_id}: {e}")
        return [HuaweiIAMUserData(id=f"ERROR_CLIENT_INIT_{region_id}", name=f"ERROR_CLIENT_INIT_{region_id}", domain_id=effective_domain_id, enabled=False, error_details=str(e))]

    try:
        # KeystoneListUsersRequest é usado para listar usuários IAM dentro de um domínio.
        # ListUsersRequest (sem Keystone) é para um serviço IAM diferente, mais antigo ou global.
        # Para usuários de conta, KeystoneListUsersRequest é o mais provável.
        # Ele requer domain_id.
        list_users_request = KeystoneListUsersRequest(domain_id=effective_domain_id)
        # Adicionar paginação se necessário (ex: list_users_request.page, list_users_request.per_page)

        response = iam_client.keystone_list_users(list_users_request) # Bloqueante

        if not hasattr(response, 'users') or not response.users:
            logger.info(f"No IAM users found for domain {effective_domain_id}.")
            return []

        for user_native in response.users:
            user_id = user_native.id
            user_name = user_native.name
            error_msg_user = []
            access_keys_data = []
            mfa_devices_data = []

            # Get User Details (inclui login_protect, pwd_status)
            login_protect_data = None
            # pwd_status_data = None # Esboço

            try:
                # ShowUserRequest ou KeystoneShowUserRequest
                # KeystoneShowUserRequest precisa de domain_id e user_id
                detail_req = KeystoneShowUserRequest(domain_id=effective_domain_id, user_id=user_id)
                user_detail_native = iam_client.keystone_show_user(detail_req).user # Bloqueante

                if hasattr(user_detail_native, 'login_protect'):
                    login_protect_data = HuaweiIAMUserLoginProtect(
                        enabled=user_detail_native.login_protect.enabled,
                        verification_method=getattr(user_detail_native.login_protect, 'verification_method', None)
                    )
                # `pwd_status` e outros detalhes como email/phone podem estar aqui também
                email_val = getattr(user_detail_native, 'email', None)
                phone_val = getattr(user_detail_native, 'mobile', None) # O SDK pode usar 'mobile'
                if not phone_val: # Tentar 'areacode_mobile' se for um nome de campo diferente
                    phone_val = getattr(user_detail_native, 'areacode_mobile', None)


            except sdk_exceptions.SdkException as e_detail:
                logger.warning(f"Error getting details for IAM user {user_name} ({user_id}): {e_detail.error_code} - {e_detail.error_message}")
                error_msg_user.append(f"Detail fetch error: {e_detail.error_code} - {e_detail.error_message}")

            # List Permanent Access Keys
            try:
                keys_req = ListPermanentAccessKeysRequest(user_id=user_id)
                keys_resp = iam_client.list_permanent_access_keys(keys_req).credentials # Bloqueante
                if keys_resp: # É uma lista de objetos Credential
                    for key_native in keys_resp:
                        access_keys_data.append(HuaweiIAMUserAccessKey(
                            access=key_native.access, # AK
                            status=key_native.status, # Active / Inactive
                            create_time_format=_parse_huawei_iam_timestamp(getattr(key_native,'create_time', None)), # Verificar nome exato do campo
                            description=getattr(key_native, 'description', None)
                        ))
            except sdk_exceptions.SdkException as e_keys:
                logger.warning(f"Error listing access keys for IAM user {user_name}: {e_keys.error_code} - {e_keys.error_message}")
                error_msg_user.append(f"Access key fetch error: {e_keys.error_code} - {e_keys.error_message}")

            # List MFA Devices
            try:
                mfa_req = ListUserMfaDevicesRequest(user_id=user_id) # Este request pode não existir ou ser diferente
                                                                    # A info de MFA pode estar em login_protect
                # Se ListUserMfaDevicesRequest não for o correto, a informação de MFA já está em login_protect
                # Se houver uma chamada específica para listar dispositivos MFA detalhados:
                # mfa_resp = iam_client.list_user_mfa_devices(mfa_req).virtual_mfa_devices # Exemplo, nome pode variar
                # if mfa_resp:
                #     for mfa_native in mfa_resp:
                #         mfa_devices_data.append(HuaweiIAMUserMfaDevice(
                #             serial_number=mfa_native.serial_number,
                #             type="virtual" # Assumindo virtual, pode variar
                #         ))
                # Por agora, usaremos o login_protect.enabled como indicador principal de MFA.
                if login_protect_data and login_protect_data.enabled:
                    # Criar um item dummy MFA se login_protect estiver habilitado, pois não temos detalhes do device aqui.
                    # Ou, se a API ShowUser já detalha o device (ex: serial_number no login_protect), usar isso.
                    # O schema `login_protect` já tem `verification_method`.
                    # Se quisermos um objeto `HuaweiIAMUserMfaDevice` separado, precisaríamos de mais dados.
                    # Para o MVP, o `login_protect` no objeto principal do usuário é suficiente.
                    # Se a política precisar de detalhes do device, esta parte precisa ser expandida.
                    pass # MFA info está em login_protect

            except sdk_exceptions.SdkException as e_mfa:
                logger.warning(f"Error listing MFA devices for IAM user {user_name}: {e_mfa.error_code} - {e_mfa.error_message}")
                error_msg_user.append(f"MFA device fetch error: {e_mfa.error_code} - {e_mfa.error_message}")


            user_data = HuaweiIAMUserData(
                id=user_id,
                name=user_name,
                domain_id=user_native.domain_id,
                enabled=user_native.enabled,
                email=email_val if 'email_val' in locals() else getattr(user_native, 'email', None),
                phone=phone_val if 'phone_val' in locals() else getattr(user_native, 'mobile', None), # Ou areacode_mobile
                login_protect=login_protect_data,
                access_keys=access_keys_data if access_keys_data else None,
                mfa_devices=mfa_devices_data if mfa_devices_data else None, # Pode ser preenchido com base em login_protect
                error_details="; ".join(error_msg_user) if error_msg_user else None
            )
            collected_users.append(user_data)

    except sdk_exceptions.SdkException as e:
        logger.error(f"Huawei SDK error listing IAM users for domain {effective_domain_id}: Code: {e.error_code}, Msg: {e.error_message}")
        return [HuaweiIAMUserData(id=f"ERROR_LIST_USERS_SDK", name=f"ERROR_LIST_USERS_SDK", domain_id=effective_domain_id, enabled=False, error_details=f"{e.error_code}: {e.error_message}")]
    except Exception as e:
        logger.error(f"Unexpected error listing IAM users for domain {effective_domain_id}: {e}", exc_info=True)
        return [HuaweiIAMUserData(id=f"ERROR_LIST_USERS_UNEXPECTED", name=f"ERROR_LIST_USERS_UNEXPECTED", domain_id=effective_domain_id, enabled=False, error_details=str(e))]

    logger.info(f"Collected {len(collected_users)} Huawei IAM users for domain {effective_domain_id}.")
    return collected_users

# Importar os para uso no if __name__
import os
import asyncio
if __name__ == '__main__':
    # Teste local (requer variáveis de ambiente Huawei Cloud setadas)
    # HUAWEICLOUD_SDK_AK, HUAWEICLOUD_SDK_SK, HUAWEICLOUD_SDK_PROJECT_ID (usado como domain_id aqui se HUAWEICLOUD_SDK_DOMAIN_ID não setado)
    # HUAWEICLOUD_SDK_TEST_REGION (ex: ap-southeast-1)

    async def main():
        test_domain_id = os.getenv("HUAWEICLOUD_SDK_DOMAIN_ID") # ou os.getenv("HUAWEICLOUD_SDK_PROJECT_ID")
        test_reg = os.getenv("HUAWEICLOUD_SDK_TEST_REGION", "ap-southeast-3") # Default para uma região comum
        if not test_domain_id:
            print("Por favor, configure HUAWEICLOUD_SDK_DOMAIN_ID (ou HUAWEICLOUD_SDK_PROJECT_ID como fallback) e HUAWEICLOUD_SDK_TEST_REGION para teste.")
            # Tentar usar project_id das credenciais como domain_id se não especificado
            try:
                _, project_id_from_creds = get_huawei_credentials()
                test_domain_id = project_id_from_creds
                print(f"Usando project_id das credenciais ('{test_domain_id}') como domain_id para o teste.")
            except ValueError:
                 print("Credenciais não encontradas. Encerrando teste.")
                 return

        print(f"Testando coletor IAM para domínio: {test_domain_id} na região de endpoint: {test_reg}")
        users = await get_huawei_iam_users(domain_id=test_domain_id, region_id=test_reg)
        if users:
            print(f"Encontrados {len(users)} usuários.")
            for u in users:
                print(f"  Usuário: {u.name} (ID: {u.id}), Habilitado: {u.enabled}")
                if u.login_protect:
                    print(f"    Login Protect: Habilitado={u.login_protect.enabled}, Método={u.login_protect.verification_method}")
                if u.access_keys:
                    print(f"    Chaves de Acesso ({len(u.access_keys)}):")
                    for key in u.access_keys:
                        print(f"      AK: {key.access}, Status: {key.status}, Criada: {key.create_time_format}")
                if u.error_details:
                    print(f"    Erros: {u.error_details}")
        else:
            print("Nenhum usuário encontrado ou erro na coleta.")

    # Para rodar um script async a partir de um síncrono (como if __name__ == '__main__')
    # asyncio.run(main()) # Python 3.7+
    # Ou, se já estiver em um loop de eventos (improvável aqui): await main()
    # Para este ambiente, vamos simular a chamada.
    # Se for rodar este arquivo diretamente para teste, descomente a linha abaixo:
    # asyncio.run(main())
    pass

# Observações durante a implementação do `huawei_iam_collector.py`:
# *   **Domain ID vs Project ID:** Para IAM, o `domain_id` (ID da conta) é geralmente o escopo principal para listar usuários. O `project_id` é mais para recursos dentro de um projeto. O SDK e as APIs podem usar um ou outro dependendo do contexto. O código tenta obter `domain_id` de `HUAWEICLOUD_SDK_DOMAIN_ID` ou usa o `project_id` das credenciais como fallback, com um aviso.
# *   **Tipos de Request IAM:** O SDK IAM da Huawei tem diferentes objetos de Request para listar usuários, por exemplo, `ListUsersRequest` (parece ser para uma versão mais antiga ou API IAM global) e `KeystoneListUsersRequest` (para listar usuários em um domínio específico, que é o que queremos). O código usa `KeystoneListUsersRequest`.
# *   **Detalhes do Usuário:** Para obter informações como `login_protect` (status do MFA), é necessário fazer uma chamada adicional `keystone_show_user` para cada usuário.
# *   **Chaves de Acesso (AK/SK):** A listagem de chaves de acesso (`ListPermanentAccessKeysRequest`) é feita por `user_id`.
# *   **Dispositivos MFA:** A informação principal de MFA (se está habilitado) vem de `login_protect`. Uma chamada `ListUserMfaDevicesRequest` poderia, teoricamente, listar os dispositivos, mas para o MVP, o status de `login_protect.enabled` é o mais importante. A implementação atual foca no `login_protect`.
# *   **Parse de Timestamps:** Adicionada uma função `_parse_huawei_iam_timestamp` para converter os formatos de data/hora da API IAM.
# *   **Chamadas Bloqueantes:** Assim como outros coletores Huawei, as chamadas ao SDK são bloqueantes e precisariam de `asyncio.to_thread` em um ambiente de produção FastAPI.
#
# Este coletor estabelece a base para obter informações de usuários IAM da Huawei Cloud.
# Fim do arquivo.
