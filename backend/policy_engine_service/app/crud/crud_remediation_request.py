from sqlalchemy.orm import Session
from typing import List, Optional

from app.models.remediation_request_model import RemediationRequest, RemediationStatusEnum
from app.schemas.remediation_request_schema import RemediationRequestCreate

class CRUDRemediationRequest:
    def get(self, db: Session, id: int) -> Optional[RemediationRequest]:
        return db.query(RemediationRequest).filter(RemediationRequest.id == id).first()

    def get_multi_by_status(self, db: Session, *, status: RemediationStatusEnum, skip: int = 0, limit: int = 100) -> List[RemediationRequest]:
        return db.query(RemediationRequest).filter(RemediationRequest.status == status).offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: RemediationRequestCreate) -> RemediationRequest:
        db_obj = RemediationRequest(
            alert_id=obj_in.alert_id,
            requested_by_user_id=obj_in.requested_by_user_id,
            status=RemediationStatusEnum.PENDING
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_status(self, db: Session, *, db_obj: RemediationRequest, status: RemediationStatusEnum, user_id: Optional[int] = None) -> RemediationRequest:
        db_obj.status = status
        if status == RemediationStatusEnum.APPROVED and user_id:
            db_obj.approved_by_user_id = user_id
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

remediation_request_crud = CRUDRemediationRequest()
