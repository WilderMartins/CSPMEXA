from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# Schemas para Políticas de Acesso de Bucket OBS (Bucket Policy)
# A estrutura exata dependerá da resposta da API GetBucketPolicy
class HuaweiOBSBucketPolicyStatementCondition(BaseModel):
    # Exemplo: StringEquals, IpAddress, etc. Chaves e valores são flexíveis.
    # Usar Dict[str, Dict[str, Any]] para representar algo como:
    # "StringEquals": {"aws:Referer": ["http://www.example.com/*"]}
    # Na Huawei, pode ser diferente, ex: "Condition": {"StringLikeIfExists": {"hws:Referer": ["*example.com"]}}
    condition_operator: str # StringLikeIfExists, etc.
    condition_key: str # hws:Referer, etc.
    condition_values: List[str]

class HuaweiOBSBucketPolicyStatement(BaseModel):
    sid: Optional[str] = Field(None, alias="Sid")
    effect: str = Field(alias="Effect") # Allow, Deny
    principal: Dict[str, Any] = Field(alias="Principal") # Ex: {"ID": ["domainId/*", "userId"]}, ou {"CanonicalUser": [...]}
                                                       # Na Huawei, pode ser {"AWS": ["arn:aws:iam::domainId:user/userName"]} ou {"CanonicalUser": [...]} ou "*"
                                                       # Para Huawei, pode ser {"ID": ["domainId/*", "userIdOfOBSInternalUser"]} ou {"HUAWEI": ["Account Id"]}
                                                       # Ou {"OBS": {"CanonicalUser": ["id1", "id2"]}}
    action: List[str] = Field(alias="Action") # Ex: obs:GetObject, obs:PutObject
    resource: List[str] = Field(alias="Resource") # Ex: bucketName/* , mybucket
    condition: Optional[Dict[str, Dict[str, List[str]]]] = Field(None, alias="Condition") # Estrutura pode variar

    class Config:
        populate_by_name = True


class HuaweiOBSBucketPolicy(BaseModel):
    version: Optional[str] = Field(None, alias="Version") # Ex: "2008-10-17" ou "1"
    statement: List[HuaweiOBSBucketPolicyStatement] = Field(alias="Statement")

    class Config:
        populate_by_name = True

# Schemas para ACLs de Bucket OBS
class HuaweiOBSGrantee(BaseModel):
    id: Optional[str] = Field(None, alias="ID", description="ID Canônico do usuário ou ID do Domínio/Conta para grupos predefinidos.")
    # type: Optional[str] = Field(None, alias="Type") # CanonicalUser, Group (Huawei pode usar nomes diferentes)
    # display_name: Optional[str] = Field(None, alias="DisplayName")
    uri: Optional[str] = Field(None, alias="URI", description="URI para grupos predefinidos como AllUsers, AuthenticatedUsers.") # Ex: http://acs.amazonaws.com/groups/global/AllUsers. Huawei pode ter URIs diferentes.
                                                                                                                             # Na Huawei, grupos como Everyone, LogDelivery
                                                                                                                             # são representados por IDs de domínio específicos ou URIs.

    class Config:
        populate_by_name = True

class HuaweiOBSGrant(BaseModel):
    grantee: HuaweiOBSGrantee = Field(alias="Grantee")
    permission: str = Field(alias="Permission") # READ, WRITE, READ_ACP, WRITE_ACP, FULL_CONTROL

    class Config:
        populate_by_name = True

class HuaweiOBSOwner(BaseModel):
    id: str = Field(alias="ID")
    # display_name: Optional[str] = Field(None, alias="DisplayName")
    class Config:
        populate_by_name = True

class HuaweiOBSBucketACL(BaseModel):
    owner: HuaweiOBSOwner = Field(alias="Owner")
    grants: List[HuaweiOBSGrant] = Field([], alias="Grant") # A API pode retornar 'Grant' como lista ou objeto único

    class Config:
        populate_by_name = True


class HuaweiOBSBucketVersioning(BaseModel):
    status: Optional[str] = Field(None, description="Ex: Enabled, Suspended, ou None se nunca habilitado.")
    # MFA Delete não é um recurso comum em OBS da mesma forma que S3, verificar documentação.

class HuaweiOBSBucketLogging(BaseModel):
    enabled: bool = False # Derivado da presença de target_bucket e target_prefix
    target_bucket: Optional[str] = Field(None)
    target_prefix: Optional[str] = Field(None)
    # TargetGrants para permissões no target bucket

class HuaweiOBSBucketData(BaseModel):
    name: str = Field(description="Nome do bucket OBS.")
    creation_date: Optional[datetime] = Field(None, description="Data de criação do bucket.")
    location: Optional[str] = Field(None, description="Região onde o bucket está localizado.") # Ou "LocationConstraint"
    storage_class: Optional[str] = Field(None, description="Classe de armazenamento padrão (ex: STANDARD, WARM, COLD).")

    bucket_policy: Optional[HuaweiOBSBucketPolicy] = Field(None, description="Política de acesso do bucket.")
    acl: Optional[HuaweiOBSBucketACL] = Field(None, description="ACLs do bucket.")
    versioning: Optional[HuaweiOBSBucketVersioning] = Field(None, description="Configuração de versionamento.")
    logging: Optional[HuaweiOBSBucketLogging] = Field(None, description="Configuração de logging de acesso.")

    # Campos para indicar acesso público inferido
    is_public_by_policy: Optional[bool] = Field(None)
    public_policy_details: List[str] = Field([])
    is_public_by_acl: Optional[bool] = Field(None)
    public_acl_details: List[str] = Field([])

    error_details: Optional[str] = Field(None, description="Detalhes de qualquer erro.")

    class Config:
        # Pydantic V1: allow_population_by_field_name = True
        # Pydantic V2: populate_by_name = True
        # Se os nomes dos campos da API não baterem com os do modelo, usar alias nos Fields.
        pass
