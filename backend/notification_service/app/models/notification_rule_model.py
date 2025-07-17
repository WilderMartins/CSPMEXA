from sqlalchemy import Column, Integer, String, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base
import enum

# Enum duplicado para evitar acoplamento entre serviços
class CloudProviderEnum(str, enum.Enum):
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"
    HUAWEI = "huawei"
    GOOGLE_WORKSPACE = "google_workspace"
    MICROSOFT_365 = "microsoft_365"

class AlertSeverityEnum(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFORMATIONAL = "INFORMATIONAL"

class NotificationRule(Base):
    __tablename__ = "notification_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    provider = Column(SQLEnum(CloudProviderEnum), nullable=False)
    severity = Column(SQLEnum(AlertSeverityEnum), nullable=False)
    channel_id = Column(Integer, ForeignKey("notification_channels.id"))

    channel = relationship("NotificationChannel")
