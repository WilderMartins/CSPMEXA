from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.crud.crud_asset import asset_crud
from app.schemas.asset_schema import AssetSchema

router = APIRouter()

@router.get("/", response_model=List[AssetSchema])
def read_assets(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    provider: Optional[str] = Query(None),
    asset_type: Optional[str] = Query(None),
    account_id: Optional[str] = Query(None),
):
    """
    Recupera uma lista de ativos do inventário com filtros e paginação.
    """
    # A função get_multi no CRUD precisa ser atualizada para aceitar filtros
    assets = asset_crud.get_multi(
        db=db, skip=skip, limit=limit,
        provider=provider, asset_type=asset_type, account_id=account_id
    )
    return assets

@router.get("/{asset_id}", response_model=AssetSchema)
def read_asset(
    asset_id: int,
    db: Session = Depends(get_db),
):
    """
    Obtém os detalhes de um ativo específico.
    """
    asset = asset_crud.get(db=db, id=asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Ativo não encontrado.")
    return asset
