from sqlalchemy import Column, Integer, String, Enum as SQLEnum
from app.db.base import Base
import enum

class ChannelTypeEnum(str, enum.Enum):
    WEBHOOK = "webhook"
    EMAIL = "email"
    SLACK = "slack"
    GOOGLE_CHAT = "google_chat"

class NotificationChannel(Base):
    __tablename__ = "notification_channels"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    type = Column(SQLEnum(ChannelTypeEnum), nullable=False)
    configuration = Column(String, nullable=False, comment="Ex: URL do webhook, endereço de e-mail")
