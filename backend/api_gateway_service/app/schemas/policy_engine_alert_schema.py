# Este arquivo é uma cópia de backend/policy_engine_service/app/schemas/alert_schema.py
# para ser usado pelo api_gateway_service como response_model.
# Manter sincronizado com a fonte original se houver alterações.

from pydantic import BaseModel, Field # Adicionado Field aqui
from typing import Optional, Dict, Any
import datetime # datetime direto é usado, não precisa de 'import datetime as dt'


class Alert(BaseModel):
    id: Optional[str] = Field(None, description="Unique ID for the alert, can be a UUID.")
    resource_id: str = Field(description="Identifier of the affected resource (e.g., S3 bucket name, EC2 instance ID).")
    resource_type: str = Field(description="Type of the affected resource (e.g., S3Bucket, EC2SecurityGroup, IAMUser).")
    account_id: Optional[str] = Field("N/A", description="AWS Account ID where the resource is located.")
    region: Optional[str] = Field("N/A", description="AWS Region where the resource is located (or 'global' for IAM).")
    provider: str = Field(default="aws", description="Cloud provider name.")
    severity: str = Field(description="Severity of the alert (e.g., Critical, High, Medium, Low, Informational).")
    title: str = Field(description="A concise title for the alert.")
    description: str = Field(description="A detailed description of the misconfiguration or finding.")
    policy_id: str = Field(description="ID of the policy or rule that was violated.")
    status: str = Field(default="OPEN", description="Current status of the alert (e.g., OPEN, ACKNOWLEDGED, RESOLVED, IGNORED).")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional structured details specific to this alert.")
    recommendation: Optional[str] = Field(None, description="Suggested steps for remediation.")
    # Pydantic V1 usa default_factory para campos que devem ser gerados no momento da instanciação.
    # Para Pydantic V2, pode-se usar `default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)`
    # ou deixar como está se o valor for preenchido explicitamente ao criar o Alert.
    # Se o Alert é apenas um schema de resposta, e os valores são preenchidos pelo policy_engine,
    # não precisamos de default_factory aqui.
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))


    class Config:
        # orm_mode = True # Pydantic v1 - útil se o objeto Alert fosse de um ORM
        from_attributes = True # Pydantic v2 - substitui orm_mode

        # Adicionando um exemplo para a documentação OpenAPI
        # Pydantic V1 usa schema_extra. Pydantic V2 usa json_schema_extra.
        # Para FastAPI/Pydantic V1, schema_extra é uma função.
        @staticmethod
        def schema_extra(schema: Dict[str, Any], model: Any) -> None:
            schema["example"] = {
                "id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
                "resource_id": "my-public-s3-bucket",
                "resource_type": "S3Bucket",
                "account_id": "123456789012",
                "region": "us-east-1",
                "provider": "aws",
                "severity": "Critical",
                "title": "S3 Bucket com Política de Acesso Público",
                "description": "A política do bucket S3 permite acesso público (ex: Principal AWS: '*'). Isso pode expor dados sensíveis a qualquer pessoa na internet.",
                "policy_id": "S3_Public_Policy",
                "status": "OPEN",
                "details": {
                    "bucket_name": "my-public-s3-bucket",
                    "policy_document": {"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":"*","Action":"s3:GetObject","Resource":"arn:aws:s3:::my-public-s3-bucket/*"}]}
                },
                "recommendation": "Revise a política do bucket. Se o acesso público não for intencional, restrinja o Principal ou as ações permitidas. Utilize o Bloqueio de Acesso Público S3 para evitar configurações públicas acidentais.",
                "created_at": "2023-10-27T10:30:00Z",
                "updated_at": "2023-10-27T10:30:00Z"
            }
