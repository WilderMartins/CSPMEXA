from sqlalchemy.orm import Session
from typing import List, Optional

from app.models.asset_model import CloudAsset
from app.schemas.asset_schema import AssetCreate

class CRUDAsset:
    def get_by_asset_id(self, db: Session, *, account_id: str, asset_id: str) -> Optional[CloudAsset]:
        return db.query(CloudAsset).filter(CloudAsset.account_id == account_id, CloudAsset.asset_id == asset_id).first()

    def create_or_update(self, db: Session, *, obj_in: AssetCreate) -> CloudAsset:
        db_obj = self.get_by_asset_id(db, account_id=obj_in.account_id, asset_id=obj_in.asset_id)

        if db_obj:
            # Atualiza o objeto existente
            db_obj.name = obj_in.name
            db_obj.configuration = obj_in.configuration
            # last_seen_at será atualizado pelo onupdate
        else:
            # Cria um novo objeto
            db_obj = CloudAsset(
                asset_id=obj_in.asset_id,
                asset_type=obj_in.asset_type,
                name=obj_in.name,
                provider=obj_in.provider,
                account_id=obj_in.account_id,
                region=obj_in.region,
                configuration=obj_in.configuration,
            )
            db.add(db_obj)

        db.commit()
        db.refresh(db_obj)
        return db_obj

asset_crud = CRUDAsset()
