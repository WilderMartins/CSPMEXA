from sqlalchemy.orm import Session
from typing import List, Optional

from app.models.linked_account_model import LinkedAccount
from app.schemas.linked_account_schema import LinkedAccountCreate, LinkedAccountUpdate

class CRUDLinkedAccount:
    def get(self, db: Session, id: int) -> Optional[LinkedAccount]:
        return db.query(LinkedAccount).filter(LinkedAccount.id == id).first()

    def get_by_account_id(self, db: Session, *, account_id: str) -> Optional[LinkedAccount]:
        return db.query(LinkedAccount).filter(LinkedAccount.account_id == account_id).first()

    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[LinkedAccount]:
        return db.query(LinkedAccount).offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: LinkedAccountCreate) -> LinkedAccount:
        db_obj = LinkedAccount(
            name=obj_in.name,
            provider=obj_in.provider,
            account_id=obj_in.account_id,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self, db: Session, *, db_obj: LinkedAccount, obj_in: LinkedAccountUpdate
    ) -> LinkedAccount:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        for field in update_data:
            if hasattr(db_obj, field):
                setattr(db_obj, field, update_data[field])

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: int) -> Optional[LinkedAccount]:
        obj = db.query(LinkedAccount).get(id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

linked_account_crud = CRUDLinkedAccount()
