from sqlalchemy import Column, Integer, String, DateTime, func, Enum as SQLEnum, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()

class CloudProviderEnum(str, enum.Enum):
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"
    HUAWEI = "huawei"
    GOOGLE_WORKSPACE = "google_workspace"
    MICROSOFT_365 = "microsoft_365"

class CloudAsset(Base):
    __tablename__ = "cloud_assets"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(String, nullable=False, index=True, comment="ID único do recurso no provedor (ex: ARN, selfLink).")
    asset_type = Column(String, nullable=False, index=True, comment="Tipo do recurso (ex: S3Bucket, EC2Instance).")
    name = Column(String, nullable=True, comment="Nome amigável do recurso.")
    provider = Column(SQLEnum(CloudProviderEnum), nullable=False)
    account_id = Column(String, nullable=False, index=True)
    region = Column(String, nullable=True)
    configuration = Column(JSON, nullable=True, comment="Configuração completa do recurso em formato JSON.")

    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), onupdate=func.now())

class AssetRelationship(Base):
    __tablename__ = "asset_relationships"

    id = Column(Integer, primary_key=True, index=True)
    source_asset_id = Column(Integer, ForeignKey("cloud_assets.id"), nullable=False)
    target_asset_id = Column(Integer, ForeignKey("cloud_assets.id"), nullable=False)
    relationship_type = Column(String, nullable=False, comment="Tipo de relação (ex: CONTAINS, ATTACHED_TO, ROUTES_TO).")

    source_asset = relationship("CloudAsset", foreign_keys=[source_asset_id])
    target_asset = relationship("CloudAsset", foreign_keys=[target_asset_id])
