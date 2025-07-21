from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import datetime
from enum import Enum

# These enums should be identical to the ones in policy_engine_service/app/schemas/alert_schema.py
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

# This schema is used for responses from the gateway for GET /alerts and GET /alerts/{id}
# It should mirror AlertSchema from the policy_engine_service
class Alert(BaseModel):
    id: int # Matches the integer ID from the database model
    resource_id: str = Field(..., description="Identifier of the affected resource")
    resource_type: str = Field(..., description="Type of the affected resource")
    account_id: Optional[str] = Field("N/A", description="Cloud account ID")
    region: Optional[str] = Field("N/A", description="Region of the resource")
    provider: str = Field(..., description="Cloud provider name")
    severity: AlertSeverityEnum = Field(..., description="Severity of the alert")
    title: str = Field(..., description="A concise title for the alert")
    description: str = Field(..., description="A detailed description of the finding")
    policy_id: str = Field(..., description="ID of the policy or rule violated")
    status: AlertStatusEnum = Field(..., description="Current status of the alert")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional structured details")
    recommendation: Optional[str] = Field(None, description="Suggested remediation steps")
    created_at: datetime.datetime
    updated_at: datetime.datetime
    first_seen_at: datetime.datetime
    last_seen_at: datetime.datetime

    class Config:
        from_attributes = True # For Pydantic V2, or orm_mode = True for V1
        use_enum_values = True # Ensures enum values are used, not enum members

# This schema is used for the request body when updating an alert via PUT /alerts/{id}
# It should mirror AlertUpdate from the policy_engine_service
class AlertUpdate(BaseModel):
    status: Optional[AlertStatusEnum] = None
    severity: Optional[AlertSeverityEnum] = None
    details: Optional[Dict[str, Any]] = None
    recommendation: Optional[str] = None

    class Config:
        use_enum_values = True

# Example for OpenAPI documentation (Optional, but good practice)
# This example should align with the fields in AlertSchema
alert_example = {
    "id": 101,
    "resource_id": "my-public-s3-bucket",
    "resource_type": "S3Bucket",
    "account_id": "123456789012",
    "region": "us-east-1",
    "provider": "aws",
    "severity": "CRITICAL",
    "title": "S3 Bucket com Política de Acesso Público",
    "description": "A política do bucket S3 permite acesso público.",
    "policy_id": "S3_Public_Policy_V2",
    "status": "OPEN",
    "details": {"bucket_name": "my-public-s3-bucket"},
    "recommendation": "Revise a política do bucket.",
    "created_at": "2023-11-15T10:00:00Z",
    "updated_at": "2023-11-15T10:00:00Z",
    "first_seen_at": "2023-11-15T10:00:00Z",
    "last_seen_at": "2023-11-15T10:00:00Z"
}

# For Pydantic V1, you might need a staticmethod for schema_extra as in the original file.
# However, FastAPI typically handles examples well with `Field(example=...)` or response_model examples.
# For simplicity, if using Pydantic V1 with FastAPI, you might rely on FastAPI's example generation
# or provide examples directly in the endpoint definition.
# If using Pydantic V2 `from_attributes = True` is the modern way for ORM mode.
# If Pydantic V1, `orm_mode = True`.
# Let's assume Pydantic V2 for `from_attributes` and `json_schema_extra`.
# If it's Pydantic V1, it should be:
# class AlertSchema(BaseModel):
#     # ... fields ...
#     class Config:
#         orm_mode = True
#         use_enum_values = True
#         schema_extra = {"example": alert_example} # Pydantic V1 style for example in schema
#
# class AlertUpdate(BaseModel):
#     # ... fields ...
#     class Config:
#         use_enum_values = True
