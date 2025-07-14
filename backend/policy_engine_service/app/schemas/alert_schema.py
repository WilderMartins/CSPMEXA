from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import datetime
from enum import Enum

# Using string enums for compatibility with Pydantic V1/V2 and SQLAlchemy model
class AlertSeverityEnum(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFORMATIONAL = "INFORMATIONAL"

class AlertStatusEnum(str, Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    IGNORED = "IGNORED"

class AlertBase(BaseModel):
    resource_id: str = Field(..., description="Ex: nome do bucket S3, ID da instância EC2")
    resource_type: str = Field(..., description="Ex: S3Bucket, EC2SecurityGroup, IAMUser")
    account_id: Optional[str] = Field("N/A", description="Preencher se disponível")
    region: Optional[str] = Field("N/A", description="Preencher se disponível")
    provider: str = Field(..., description="Ex: aws, gcp, azure")
    severity: AlertSeverityEnum = Field(..., description="Criticidade do alerta")
    title: str = Field(..., description="Título curto do alerta")
    description: str = Field(..., description="Descrição detalhada da má configuração")
    policy_id: str = Field(..., description="ID da política/regra que foi violada")
    # status: AlertStatusEnum = Field(AlertStatusEnum.OPEN, description="Status atual do alerta") # Status will be handled by DB default or on create
    details: Optional[Dict[str, Any]] = Field(None, description="Detalhes adicionais específicos do alerta")
    recommendation: Optional[str] = Field(None, description="Sugestão de remediação")

class AlertCreate(AlertBase):
    # Potentially add fields specific to creation if any, e.g. if status can be set at creation
    pass

class Alert(AlertBase):
    id: int
    status: AlertStatusEnum # Status is part of the full alert representation
    created_at: datetime.datetime
    updated_at: datetime.datetime
    first_seen_at: datetime.datetime # Added to match the model
    last_seen_at: datetime.datetime  # Added to match the model


    class Config:
        orm_mode = True # Pydantic v1
        # from_attributes = True # Pydantic v2
        use_enum_values = True # Ensure enum values are used in serialization

# Schema for updating an alert (e.g., changing status)
class AlertUpdate(BaseModel):
    status: Optional[AlertStatusEnum] = None
    severity: Optional[AlertSeverityEnum] = None
    details: Optional[Dict[str, Any]] = None
    recommendation: Optional[str] = None
    # updated_at will be handled by the database on update

    class Config:
        use_enum_values = True
