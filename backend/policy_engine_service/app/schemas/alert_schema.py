from pydantic import BaseModel
from typing import Optional, Dict, Any
import datetime


class Alert(BaseModel):
    id: Optional[str]  # Pode ser um UUID gerado
    resource_id: str  # Ex: nome do bucket S3, ID da instância EC2
    resource_type: str  # Ex: "S3Bucket", "EC2SecurityGroup", "IAMUser"
    account_id: Optional[str] = "N/A"  # Preencher se disponível
    region: Optional[str] = "N/A"  # Preencher se disponível
    provider: str = "aws"
    severity: str  # Ex: "Critical", "High", "Medium", "Low", "Informational"
    title: str  # Título curto do alerta
    description: str  # Descrição detalhada da má configuração
    policy_id: str  # ID da política/regra que foi violada
    status: str = "OPEN"  # Ex: OPEN, ACKNOWLEDGED, RESOLVED, IGNORED
    details: Optional[Dict[str, Any]] = (
        None  # Detalhes adicionais específicos do alerta
    )
    recommendation: Optional[str] = None  # Sugestão de remediação
    created_at: datetime.datetime = datetime.datetime.now(datetime.timezone.utc)
    updated_at: datetime.datetime = datetime.datetime.now(datetime.timezone.utc)

    class Config:
        orm_mode = True  # Pydantic v1
        # from_attributes = True # Pydantic v2
