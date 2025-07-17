from sqlalchemy.orm import Session
from typing import List, Optional

from app.models.attack_path_model import AttackPath
from app.schemas.attack_path_schema import AttackPathCreate

class CRUDAttackPath:
    def get_by_path_id(self, db: Session, *, path_id: str) -> Optional[AttackPath]:
        return db.query(AttackPath).filter(AttackPath.path_id == path_id).first()

    def create(self, db: Session, *, obj_in: AttackPathCreate) -> AttackPath:
        # Converte a lista de nós Pydantic para uma lista de dicts para o JSON
        nodes_as_dicts = [node.model_dump() for node in obj_in.nodes]

        db_obj = AttackPath(
            path_id=obj_in.path_id,
            description=obj_in.description,
            severity=obj_in.severity,
            nodes=nodes_as_dicts
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

attack_path_crud = CRUDAttackPath()
