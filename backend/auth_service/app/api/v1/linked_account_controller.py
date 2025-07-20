from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.schemas.linked_account_schema import LinkedAccountSchema, LinkedAccountCreate, LinkedAccountUpdate
from app.services.credentials_service import credentials_service
from app.crud.crud_linked_account import linked_account_crud
from app.core.security import require_permission

router = APIRouter()

@router.post("/", response_model=LinkedAccountSchema, status_code=201, dependencies=[Depends(require_permission("manage:linked_accounts"))])
def create_linked_account(
    *,
    db: Session = Depends(get_db),
    account_in: LinkedAccountCreate
):
    """
    Cria uma nova conta vinculada e salva suas credenciais no Vault.
    Apenas administradores podem executar esta ação.
    """
    try:
        result = credentials_service.save_credentials_for_account(db=db, account_in=account_in)
        linked_account = linked_account_crud.get(db, id=result["linked_account_id"])
        return linked_account
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[LinkedAccountSchema])
def read_linked_accounts(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    Lista todas as contas vinculadas.
    """
    accounts = linked_account_crud.get_multi(db, skip=skip, limit=limit)
    return accounts

@router.get("/{account_id}", response_model=LinkedAccountSchema)
def read_linked_account(
    account_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtém os detalhes de uma conta vinculada específica.
    """
    account = linked_account_crud.get(db, id=account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Conta não encontrada.")
    return account

@router.put("/{account_id}", response_model=LinkedAccountSchema, dependencies=[Depends(require_permission("manage:linked_accounts"))])
def update_linked_account(
    account_id: int,
    account_in: LinkedAccountUpdate,
    db: Session = Depends(get_db)
):
    """
    Atualiza os detalhes de uma conta vinculada (atualmente, apenas o nome).
    Apenas administradores podem executar esta ação.
    """
    db_account = linked_account_crud.get(db, id=account_id)
    if not db_account:
        raise HTTPException(status_code=404, detail="Conta não encontrada.")

    updated_account = linked_account_crud.update(db, db_obj=db_account, obj_in=account_in)
    return updated_account

@router.delete("/{account_id}", status_code=204, dependencies=[Depends(require_permission("manage:linked_accounts"))])
def delete_linked_account(
    account_id: int,
    db: Session = Depends(get_db)
):
    """
    Deleta uma conta vinculada e suas credenciais do Vault.
    Apenas administradores podem executar esta ação.
    """
    try:
        credentials_service.delete_credentials_for_account(db=db, linked_account_id=account_id)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/internal/credentials/{account_id}", dependencies=[Depends(require_permission("read:credentials"))])
def get_account_credentials(
    account_id: int,
    db: Session = Depends(get_db)
):
    """
    Endpoint interno para o API Gateway buscar as credenciais de uma conta.
    Protegido para garantir que apenas chamadas de serviço autorizadas (com um token de admin)
    possam acessar as credenciais.
    """
    try:
        # Verificar se a conta existe
        account = linked_account_crud.get(db, id=account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Conta não encontrada.")

        # Buscar as credenciais do Vault
        credentials = credentials_service.get_credentials_for_account(linked_account_id=account_id)
        if not credentials:
            raise HTTPException(status_code=404, detail="Credenciais não encontradas no Vault para esta conta.")

        return credentials
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
