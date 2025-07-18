from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.crud.crud_attack_path import attack_path_crud
from app.schemas.attack_path_schema import AttackPathSchema

router = APIRouter()

@router.get("/", response_model=List[AttackPathSchema])
def read_attack_paths(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    Recupera uma lista de caminhos de ataque encontrados.
    """
    # O CRUD para attack_path precisa de uma função get_multi
    attack_paths = attack_path_crud.get_multi(db=db, skip=skip, limit=limit)
    return attack_paths
