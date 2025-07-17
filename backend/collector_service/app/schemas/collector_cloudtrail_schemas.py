from pydantic import BaseModel, Field
from typing import Optional, List

class CloudTrailTrail(BaseModel):
    name: str = Field(..., description="Nome do trail.")
    s3_bucket_name: str = Field(..., description="Bucket S3 onde os logs são armazenados.")
    is_multi_region_trail: bool = Field(..., description="Indica se o trail é multi-região.")
    log_file_validation_enabled: bool = Field(..., description="Indica se a validação de arquivos de log está habilitada.")
    home_region: str = Field(..., description="Região principal do trail.")
    trail_arn: str = Field(..., description="ARN do trail.")

class CloudTrailStatus(BaseModel):
    is_logging: bool = Field(..., description="Indica se o trail está ativamente registrando logs.")
    latest_delivery_time: Optional[str] = Field(None, description="Hora da última entrega de log.")
    latest_notification_time: Optional[str] = Field(None, description="Hora da última notificação.")
    start_logging_time: Optional[str] = Field(None, description="Hora de início do logging.")
    stop_logging_time: Optional[str] = Field(None, description="Hora de parada do logging.")
    latest_error: Optional[str] = Field(None, description="Último erro de entrega de log.")

class CloudTrailData(BaseModel):
    trail_info: CloudTrailTrail
    status: CloudTrailStatus
