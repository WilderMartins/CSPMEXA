from pydantic import BaseModel
from typing import List, Optional, Any, Dict
# import datetime # Removido
# from pydantic import EmailStr # Removido


# Schema para um item de bucket S3 individual, como recebido do collector-service
class S3BucketData(BaseModel):
    name: str
    creation_date: str  # ou datetime.datetime se o collector garantir a conversão
    region: str
    is_public_by_acl: Any  # Pode ser bool ou str ('Error', 'Unknown')
    public_acl_details: str
    # Adicionar outros campos relevantes que o collector possa enviar
    # por exemplo, resultados de verificação de política de bucket, tags, etc.


# Schema para a lista de dados de S3 que o policy engine receberá
class S3InputData(BaseModel):
    s3_buckets: List[S3BucketData]


# No futuro, podemos ter um schema mais genérico para qualquer tipo de dado de recurso
class ResourceData(BaseModel):
    resource_type: str  # ex: "s3_bucket", "ec2_instance", "iam_user"
    data: Dict[str, Any]  # Dados específicos do recurso


class AnalysisRequest(BaseModel):
    # Por enquanto, focamos em S3. No futuro, pode ser uma lista de ResourceData.
    s3_data: Optional[List[S3BucketData]] = None
    # ec2_data: Optional[List[EC2InstanceData]] = None # Exemplo futuro
    # iam_data: Optional[List[IAMUserData]] = None # Exemplo futuro
    # account_id: Optional[str] = None # Para contextualizar
    # provider: Optional[str] = "aws" # Para contextualizar
