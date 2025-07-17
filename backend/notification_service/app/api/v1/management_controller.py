from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.schemas.notification_schema import NotificationChannelSchema, NotificationChannelCreate, NotificationRuleSchema, NotificationRuleCreate
from app.crud.crud_notification_channel import notification_channel_crud
from app.crud.crud_notification_rule import notification_rule_crud

channels_router = APIRouter()
rules_router = APIRouter()

# --- Endpoints para Canais ---
@channels_router.post("/", response_model=NotificationChannelSchema, status_code=201)
def create_channel(*, db: Session = Depends(get_db), channel_in: NotificationChannelCreate):
    return notification_channel_crud.create(db=db, obj_in=channel_in)

@channels_router.get("/", response_model=List[NotificationChannelSchema])
def read_channels(db: Session = Depends(get_db), skip: int = 0, limit: int = 100):
    return notification_channel_crud.get_multi(db, skip=skip, limit=limit)

@channels_router.delete("/{channel_id}", response_model=NotificationChannelSchema)
def delete_channel(channel_id: int, db: Session = Depends(get_db)):
    deleted_channel = notification_channel_crud.remove(db=db, id=channel_id)
    if not deleted_channel:
        raise HTTPException(status_code=404, detail="Canal não encontrado.")
    return deleted_channel

# --- Endpoints para Regras ---
@rules_router.post("/", response_model=NotificationRuleSchema, status_code=201)
def create_rule(*, db: Session = Depends(get_db), rule_in: NotificationRuleCreate):
    # Verificar se o canal existe
    channel = notification_channel_crud.get(db, id=rule_in.channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail=f"Canal com id {rule_in.channel_id} não encontrado.")
    return notification_rule_crud.create(db=db, obj_in=rule_in)

@rules_router.get("/", response_model=List[NotificationRuleSchema])
def read_rules(db: Session = Depends(get_db), skip: int = 0, limit: int = 100):
    return notification_rule_crud.get_multi(db, skip=skip, limit=limit)

@rules_router.delete("/{rule_id}", response_model=NotificationRuleSchema)
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    deleted_rule = notification_rule_crud.remove(db=db, id=rule_id)
    if not deleted_rule:
        raise HTTPException(status_code=404, detail="Regra não encontrada.")
    return deleted_rule
