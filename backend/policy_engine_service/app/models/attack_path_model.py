from sqlalchemy import Column, Integer, String, DateTime, func, JSON, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()

class AttackPathSeverityEnum(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"

class AttackPath(Base):
    __tablename__ = "attack_paths"

    id = Column(Integer, primary_key=True, index=True)
    path_id = Column(String, nullable=False, unique=True, comment="Um ID único para o tipo de caminho de ataque, ex: 'EC2_PUBLIC_TO_ADMIN_ROLE'.")
    description = Column(String, nullable=False, comment="Descrição do caminho de ataque.")
    severity = Column(SQLEnum(AttackPathSeverityEnum), nullable=False)
    nodes = Column(JSON, nullable=False, comment="Uma lista de JSONs, cada um representando um nó no caminho (ex: a VM, a Role).")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
