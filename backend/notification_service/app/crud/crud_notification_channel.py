from sqlalchemy.orm import Session
from typing import List, Optional

from app.models.notification_channel_model import NotificationChannel
from app.schemas.notification_schema import NotificationChannelCreate

class CRUDNotificationChannel:
    def get(self, db: Session, id: int) -> Optional[NotificationChannel]:
        return db.query(NotificationChannel).filter(NotificationChannel.id == id).first()

    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[NotificationChannel]:
        return db.query(NotificationChannel).offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: NotificationChannelCreate) -> NotificationChannel:
        db_obj = NotificationChannel(
            name=obj_in.name,
            type=obj_in.type,
            configuration=obj_in.configuration,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: int) -> Optional[NotificationChannel]:
        obj = db.query(NotificationChannel).get(id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

notification_channel_crud = CRUDNotificationChannel()
