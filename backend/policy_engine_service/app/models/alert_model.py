from sqlalchemy import Column, Integer, String, DateTime, JSON, Enum as SQLAlchemyEnum
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func
import enum
import datetime

Base = declarative_base()

class AlertSeverity(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFORMATIONAL = "INFORMATIONAL"

class AlertStatus(str, enum.Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    IGNORED = "IGNORED"

class AlertModel(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True) # Autoincrementing integer ID

    resource_id = Column(String, nullable=False, index=True)
    resource_type = Column(String, nullable=False, index=True)
    account_id = Column(String, nullable=True, index=True)
    region = Column(String, nullable=True, index=True)
    provider = Column(String, nullable=False, index=True)

    severity = Column(SQLAlchemyEnum(AlertSeverity, name="alert_severity_enum", create_type=False), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    policy_id = Column(String, nullable=False, index=True)

    status = Column(SQLAlchemyEnum(AlertStatus, name="alert_status_enum", create_type=False), nullable=False, default=AlertStatus.OPEN, index=True)

    details = Column(JSON, nullable=True)
    recommendation = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<AlertModel(id={self.id}, title='{self.title}', provider='{self.provider}', resource_id='{self.resource_id}')>"

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class AlertBase(BaseModel):
    resource_id: str = Field(..., description="Ex: nome do bucket S3, ID da instância EC2")
    resource_type: str = Field(..., description="Ex: S3Bucket, EC2SecurityGroup, IAMUser")
    account_id: Optional[str] = Field("N/A", description="Preencher se disponível")
    region: Optional[str] = Field("N/A", description="Preencher se disponível")
    provider: str = Field(..., description="Ex: aws, gcp, azure")
    severity: AlertSeverity = Field(..., description="Criticidade do alerta")
    title: str = Field(..., description="Título curto do alerta")
    description: str = Field(..., description="Descrição detalhada da má configuração")
    policy_id: str = Field(..., description="ID da política/regra que foi violada")
    status: AlertStatus = Field(AlertStatus.OPEN, description="Status atual do alerta")
    details: Optional[Dict[str, Any]] = Field(None, description="Detalhes adicionais específicos do alerta")
    recommendation: Optional[str] = Field(None, description="Sugestão de remediação")

class AlertCreate(AlertBase):
    pass

class AlertSchema(AlertBase):
    id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime
    first_seen_at: datetime.datetime
    last_seen_at: datetime.datetime

    class Config:
        from_attributes = True
        use_enum_values = True

class AlertUpdate(BaseModel):
    status: Optional[AlertStatus] = None
    severity: Optional[AlertSeverity] = None
    details: Optional[Dict[str, Any]] = None
    recommendation: Optional[str] = None

    class Config:
        use_enum_values = True
