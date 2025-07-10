from sqlalchemy.orm import Session
from ..db.models.alert_model import Alert as DBAlertModel # O modelo SQLAlchemy
from app.schemas.alert_schema import Alert as AlertSchema # O schema Pydantic para entrada/saída

def create_alert(db: Session, *, alert_in: AlertSchema) -> DBAlertModel:
    """
    Cria um novo alerta no banco de dados.
    """
    # Converter o schema Pydantic para um dict, garantindo que os enums sejam valores
    # e não os objetos Enum em si, se necessário (SQLAlchemy geralmente lida bem com isso).
    alert_data = alert_in.model_dump()

    # Tratar enums explicitamente se necessário, convertendo para seus valores.
    # SQLAlchemy 1.4+ com SAEnum geralmente lida com isso automaticamente.
    # if isinstance(alert_data.get("severity"), enum.Enum):
    #     alert_data["severity"] = alert_data["severity"].value
    # if isinstance(alert_data.get("status"), enum.Enum):
    #     alert_data["status"] = alert_data["status"].value

    db_alert = DBAlertModel(**alert_data)
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    return db_alert

def get_alert(db: Session, alert_id: str) -> DBAlertModel | None:
    """
    Obtém um alerta pelo seu ID.
    """
    return db.query(DBAlertModel).filter(DBAlertModel.id == alert_id).first()

# Adicionar outras funções CRUD conforme necessário (get_alerts, update_alert, delete_alert)
# Exemplo:
# from typing import List, Optional
# def get_alerts(db: Session, skip: int = 0, limit: int = 100) -> List[DBAlertModel]:
#     return db.query(DBAlertModel).offset(skip).limit(limit).all()
