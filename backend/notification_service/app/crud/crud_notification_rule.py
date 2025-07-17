from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from app.models.notification_rule_model import NotificationRule
from app.schemas.notification_schema import NotificationRuleCreate

class CRUDNotificationRule:
    def get(self, db: Session, id: int) -> Optional[NotificationRule]:
        return db.query(NotificationRule).filter(NotificationRule.id == id).first()

    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[NotificationRule]:
        return db.query(NotificationRule).options(joinedload(NotificationRule.channel)).offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: NotificationRuleCreate) -> NotificationRule:
        db_obj = NotificationRule(
            name=obj_in.name,
            provider=obj_in.provider,
            severity=obj_in.severity,
            channel_id=obj_in.channel_id,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: int) -> Optional[NotificationRule]:
        obj = db.query(NotificationRule).get(id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

notification_rule_crud = CRUDNotificationRule()
