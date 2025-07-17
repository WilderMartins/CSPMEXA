from sqlalchemy.orm import Session
from typing import List, Optional, Type
# from uuid import uuid4 # UUID not used for primary key in the current model
import datetime

from app.models.alert_model import AlertModel, AlertStatus, AlertSeverity, AlertCreate, AlertUpdate
from app.schemas.alert_schema import AlertSchema # Using the refined AlertSchema for responses
from sqlalchemy import desc, asc, func

class CRUDAlert:
    def __init__(self, model: Type[AlertModel]):
        self.model = model

    def get_alert(self, db: Session, alert_id: int) -> Optional[AlertModel]:
        return db.query(self.model).filter(self.model.id == alert_id).first()

    def get_alerts(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = "desc",
        provider: Optional[str] = None,
        severity: Optional[AlertSeverity] = None, # Uses AlertSeverity enum from model
        status: Optional[AlertStatus] = None,     # Uses AlertStatus enum from model
        resource_id: Optional[str] = None,
        policy_id: Optional[str] = None,
        account_id: Optional[str] = None,
        region: Optional[str] = None,
        start_date: Optional[datetime.datetime] = None,
        end_date: Optional[datetime.datetime] = None
    ) -> List[AlertModel]:
        query = db.query(self.model)

        if provider:
            query = query.filter(self.model.provider == provider)
        if severity:
            query = query.filter(self.model.severity == severity)
        if status:
            query = query.filter(self.model.status == status)
        if resource_id:
            query = query.filter(self.model.resource_id.ilike(f"%{resource_id}%"))
        if policy_id:
            query = query.filter(self.model.policy_id == policy_id)
        if account_id:
            query = query.filter(self.model.account_id == account_id)
        if region:
            query = query.filter(self.model.region == region)
        if start_date:
            query = query.filter(self.model.created_at >= start_date)
        if end_date:
            query = query.filter(self.model.created_at <= end_date)


        if sort_by:
            column = getattr(self.model, sort_by, None)
            if column:
                if sort_order.lower() == "asc":
                    query = query.order_by(asc(column))
                else:
                    query = query.order_by(desc(column))
            else:
                query = query.order_by(desc(self.model.last_seen_at)) # Default sort
        else:
             query = query.order_by(desc(self.model.last_seen_at))


        return query.offset(skip).limit(limit).all()

    def create_alert(self, db: Session, *, alert_in: AlertCreate) -> AlertModel:
        """
        Creates a new alert or updates the last_seen_at timestamp if an identical open alert exists.
        Identical is defined by: provider, resource_id, policy_id, and status=OPEN.
        """

        existing_alert = db.query(self.model).filter(
            self.model.provider == alert_in.provider,
            self.model.resource_id == alert_in.resource_id,
            self.model.policy_id == alert_in.policy_id,
            self.model.status == AlertStatus.OPEN
        ).first()

        current_time = datetime.datetime.now(datetime.timezone.utc)

        if existing_alert:
            existing_alert.last_seen_at = current_time
            # Optionally update severity if it has changed, or other mutable fields for an open alert
            if alert_in.severity != existing_alert.severity:
                existing_alert.severity = alert_in.severity
            if alert_in.details != existing_alert.details: # If details can change
                 existing_alert.details = alert_in.details
            if alert_in.description != existing_alert.description: # If description can change
                 existing_alert.description = alert_in.description
            if alert_in.recommendation != existing_alert.recommendation: # If recommendation can change
                 existing_alert.recommendation = alert_in.recommendation

            db.add(existing_alert)
            db.commit()
            db.refresh(existing_alert)
            return existing_alert
        else:
            # Create a new alert entry
            # For Pydantic V1, use .dict(). For V2, use .model_dump()
            alert_data = alert_in.model_dump() if hasattr(alert_in, 'model_dump') else alert_in.dict()

            db_alert = self.model(
                **alert_data,
                # first_seen_at and last_seen_at are set by server_default on creation,
                # but for a new alert, they should effectively be 'now'.
                # The model's server_default will handle created_at, updated_at, first_seen_at, last_seen_at.
                # Explicitly setting them here might override server_default depending on DB and SQLAlchemy version.
                # It's often better to rely on server_default for these on initial creation.
                # However, if we want first_seen_at and last_seen_at to be exactly this moment:
                # first_seen_at=current_time, # Let server_default handle this
                # last_seen_at=current_time,  # Let server_default handle this
                status=AlertStatus.OPEN # Explicitly set status to OPEN for new alerts
            )
            db.add(db_alert)
            db.commit()
            db.refresh(db_alert)
            return db_alert

    def update_alert_status(
        self, db: Session, *, alert_id: int, status: AlertStatus, # Use AlertStatus enum
    ) -> Optional[AlertModel]:
        alert_db_obj = self.get_alert(db, alert_id)
        if alert_db_obj:
            alert_db_obj.status = status
            # updated_at will be handled by the database onupdate trigger
            db.add(alert_db_obj)
            db.commit()
            db.refresh(alert_db_obj)
        return alert_db_obj

    def update_alert(
        self, db: Session, *, alert_id: int, alert_in: AlertUpdate
    ) -> Optional[AlertModel]:
        alert_db_obj = self.get_alert(db, alert_id)
        if alert_db_obj:
            # For Pydantic V1, use .dict(). For V2, use .model_dump()
            update_data = alert_in.model_dump(exclude_unset=True) if hasattr(alert_in, 'model_dump') else alert_in.dict(exclude_unset=True)

            for field, value in update_data.items():
                if value is not None: # Ensure we don't overwrite with None if not intended
                    setattr(alert_db_obj, field, value)

            # updated_at will be handled by the database's onupdate mechanism
            db.add(alert_db_obj)
            db.commit()
            db.refresh(alert_db_obj)
        return alert_db_obj


    def remove_alert(self, db: Session, *, alert_id: int) -> Optional[AlertModel]:
        alert_obj = db.query(self.model).get(alert_id)
        if alert_obj:
            db.delete(alert_obj)
            db.commit()
        return alert_obj

    def get_summary(self, db: Session) -> dict:
        """
        Calcula um resumo dos alertas, como contagem por severidade e status.
        """
        severity_counts = db.query(
            self.model.severity, func.count(self.model.id)
        ).group_by(self.model.severity).all()

        status_counts = db.query(
            self.model.status, func.count(self.model.id)
        ).group_by(self.model.status).all()

        total_alerts = db.query(func.count(self.model.id)).scalar()

        summary = {
            "total_alerts": total_alerts,
            "by_severity": {str(severity.name): count for severity, count in severity_counts},
            "by_status": {str(status.name): count for status, count in status_counts}
        }
        return summary

alert_crud = CRUDAlert(AlertModel)

# Adicionar import para o cliente de notificação e AlertSeverity enum
from app.services.notification_client import notification_client
from app.models.alert_model import AlertSeverity as AlertSeverityDBEnum # Enum do modelo DB

# Sobrescrever create_alert para incluir notificação
_original_create_alert = alert_crud.create_alert

async def create_alert_and_notify(db: Session, *, alert_in: AlertCreate) -> AlertModel:
    created_alert_model = _original_create_alert(db=db, alert_in=alert_in)

    # Verificar se o alerta criado (ou existente atualizado) é crítico
    # A severidade em alert_in é AlertSeverityEnum (str enum de schemas.alert_schema)
    # A severidade em created_alert_model é AlertSeverityDBEnum (enum de models.alert_model)

    is_critical = False
    if isinstance(created_alert_model.severity, str): # Se o enum do DB for armazenado como string
        is_critical = created_alert_model.severity == AlertSeverityDBEnum.CRITICAL.value
    elif isinstance(created_alert_model.severity, AlertSeverityDBEnum): # Se for o objeto enum
        is_critical = created_alert_model.severity == AlertSeverityDBEnum.CRITICAL

    if is_critical:
        # Precisamos converter AlertModel (SQLAlchemy) para AlertSchema (Pydantic) para o cliente de notificação
        # ou garantir que o cliente de notificação possa lidar com o modelo do DB diretamente
        # ou, mais simples, o cliente de notificação espera um AlertDataPayload, que é um subconjunto de AlertSchema.
        # Vamos converter o created_alert_model para AlertSchema.
        alert_schema_for_notification = AlertSchema.from_orm(created_alert_model)

        # Idealmente, a chamada de notificação não deve bloquear e deve ser feita em background.
        # No entanto, notification_client.send_critical_alert_notification é async.
        # Se create_alert_and_notify for chamado de um endpoint async, podemos fazer `await`.
        # Se for de um sync, precisaríamos de `asyncio.create_task` ou similar,
        # ou mover a lógica de notificação para o endpoint do controller que é async.
        # Por agora, assumindo que este CRUD pode ser chamado de um contexto que permite await.
        # Se não, a notificação deve ser movida para o controller.

        # Para MVP, a chamada será feita aqui. Se bloquear, precisará ser refatorada.
        # O controller de análise é async, então ele pode chamar este CRUD com await.
        # E o notification_client.send_critical_alert_notification é async.

        import asyncio # Adicionado para create_task
        # Disparar a notificação sem esperar pela conclusão para não atrasar a resposta principal.
        # Isso é um "fire-and-forget". Erros serão logados pelo notification_client.

        # Notificação por Email
        asyncio.create_task(notification_client.send_critical_alert_notification(alert_schema_for_notification))

        # Notificação por Webhook (chamada se configurado e habilitado)
        # A URL do webhook específica pode vir de uma configuração de política/alerta no futuro.
        # Por agora, se chamado, usará a URL default do notification_service.
        asyncio.create_task(notification_client.send_critical_alert_webhook_notification(alert_schema_for_notification))

        # Notificação por Google Chat (chamada se configurado e habilitado)
        asyncio.create_task(notification_client.send_critical_alert_google_chat_notification(alert_schema_for_notification))


    # Disparar a verificação de regras de notificação
    asyncio.create_task(notification_client.trigger_notifications_for_alert(alert_schema_for_notification))

    return created_alert_model

# Substituir o método no objeto crud
alert_crud.create_alert = create_alert_and_notify
