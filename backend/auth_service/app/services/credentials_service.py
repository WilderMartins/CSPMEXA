import hvac
from typing import List, Dict, Any, Optional
from app.core.config import get_vault_client
from app.crud.crud_linked_account import linked_account_crud
from app.schemas.linked_account_schema import LinkedAccountCreate, LinkedAccountUpdate
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

class CredentialsService:
    def __init__(self):
        self.vault_client: Optional[hvac.Client] = get_vault_client()
        if not self.vault_client:
            logger.warning("Não foi possível conectar ao Vault na inicialização.")

    def save_credentials_for_account(
        self, db: Session, *, account_in: LinkedAccountCreate
    ) -> Dict[str, Any]:
        """
        Cria ou atualiza uma LinkedAccount e salva suas credenciais no Vault.
        """
        if not self.vault_client:
            raise ConnectionError("A conexão com o Vault não está disponível.")

        # Verificar se já existe uma conta com o mesmo account_id
        db_account = linked_account_crud.get_by_account_id(db, account_id=account_in.account_id)

        if db_account:
            # Atualiza o nome se necessário
            update_schema = LinkedAccountUpdate(name=account_in.name)
            linked_account = linked_account_crud.update(db, db_obj=db_account, obj_in=update_schema)
        else:
            # Cria a nova conta
            linked_account = linked_account_crud.create(db, obj_in=account_in)

        # Salva as credenciais no Vault usando o ID da conta como parte do caminho
        vault_path = f"secret/credentials/{linked_account.id}"
        try:
            self.vault_client.secrets.kv.v2.create_or_update_secret(
                path=vault_path,
                secret=account_in.credentials,
            )
            logger.info(f"Credenciais salvas para a conta {linked_account.id} no Vault em '{vault_path}'.")
        except Exception as e:
            logger.error(f"Erro ao salvar credenciais para a conta {linked_account.id} no Vault: {e}")
            # Se a escrita no Vault falhar, podemos querer reverter a criação/atualização no DB.
            # Por enquanto, vamos levantar a exceção.
            raise

        return {"status": "success", "linked_account_id": linked_account.id}

    def get_credentials_for_account(self, linked_account_id: int) -> Optional[Dict[str, Any]]:
        """
        Busca as credenciais de uma conta específica do Vault.
        """
        if not self.vault_client:
            raise ConnectionError("A conexão com o Vault não está disponível.")

        vault_path = f"secret/credentials/{linked_account_id}"
        try:
            response = self.vault_client.secrets.kv.v2.read_secret_version(path=vault_path)
            return response['data']['data']
        except hvac.exceptions.InvalidPath:
            logger.warning(f"Nenhuma credencial encontrada no Vault para a conta ID: {linked_account_id}")
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar credenciais para a conta ID {linked_account_id} do Vault: {e}")
            raise

    def delete_credentials_for_account(self, db: Session, *, linked_account_id: int):
        """
        Deleta uma LinkedAccount e suas credenciais do Vault.
        """
        if not self.vault_client:
            raise ConnectionError("A conexão com o Vault não está disponível.")

        # Deleta as credenciais do Vault
        vault_path = f"secret/credentials/{linked_account_id}"
        try:
            self.vault_client.secrets.kv.v2.delete_metadata_and_all_versions(path=vault_path)
            logger.info(f"Credenciais deletadas do Vault para a conta ID: {linked_account_id}")
        except hvac.exceptions.InvalidPath:
            logger.warning(f"Nenhuma credencial encontrada no Vault para a conta ID {linked_account_id} ao tentar deletar.")
        except Exception as e:
            logger.error(f"Erro ao deletar credenciais para a conta ID {linked_account_id} do Vault: {e}")
            raise

        # Deleta a conta do banco de dados
        deleted_account = linked_account_crud.remove(db, id=linked_account_id)
        if not deleted_account:
            raise ValueError(f"Conta vinculada com ID {linked_account_id} não encontrada no banco de dados.")

        return {"status": "success", "deleted_account_id": linked_account_id}


credentials_service = CredentialsService()
