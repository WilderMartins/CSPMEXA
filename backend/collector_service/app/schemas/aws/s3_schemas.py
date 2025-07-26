from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class S3BucketACLGrantee(BaseModel):
    type: Optional[str] = Field(None, description="Type of grantee (e.g., CanonicalUser, Group).")
    display_name: Optional[str] = Field(None, description="Display name of the grantee.")
    uri: Optional[str] = Field(None, description="URI of the group (e.g., AllUsers, AuthenticatedUsers).")
    id: Optional[str] = Field(None, description="Canonical user ID of the grantee.")


class S3BucketACLGrant(BaseModel):
    grantee: S3BucketACLGrantee = Field(description="The grantee who is receiving the permission.")
    permission: Optional[str] = Field(None, description="The permission being granted (e.g., READ, WRITE).")


class S3BucketACLDetails(BaseModel):
    owner_display_name: Optional[str] = Field(None)
    owner_id: Optional[str] = Field(None)
    grants: List[S3BucketACLGrant] = Field([], description="A list of grants.")
    is_public: bool = Field(False, description="True if any ACL grant makes the bucket effectively public.")
    public_details: List[str] = Field([], description="Details of public grants if any.")


class S3BucketVersioning(BaseModel):
    status: Optional[str] = Field(None, description="Versioning status (e.g., Enabled, Suspended).")
    mfa_delete: Optional[str] = Field(None, description="MFA Delete status (e.g., Enabled, Disabled).")


class S3BucketPublicAccessBlock(BaseModel):
    block_public_acls: Optional[bool] = Field(None, alias="BlockPublicAcls")
    ignore_public_acls: Optional[bool] = Field(None, alias="IgnorePublicAcls")
    block_public_policy: Optional[bool] = Field(None, alias="BlockPublicPolicy")
    restrict_public_buckets: Optional[bool] = Field(None, alias="RestrictPublicBuckets")

    class Config:
        populate_by_name = True # Permite usar 'BlockPublicAcls' do Boto3 e mapear para 'block_public_acls'


class S3BucketLogging(BaseModel):
    enabled: bool = Field(False)
    target_bucket: Optional[str] = Field(None)
    target_prefix: Optional[str] = Field(None)


class S3BucketData(BaseModel):
    name: str = Field(description="Name of the S3 bucket.")
    creation_date: Optional[datetime] = Field(None, description="Date and time the bucket was created.")
    region: str = Field(description="AWS region where the bucket is located.")
    acl: Optional[S3BucketACLDetails] = Field(None, description="Access Control List information.")
    policy: Optional[Dict[str, Any]] = Field(None, description="Bucket policy document as a dictionary.")
    policy_is_public: Optional[bool] = Field(None, description="Indicates if the bucket policy allows public access.")
    versioning: Optional[S3BucketVersioning] = Field(None, description="Bucket versioning configuration.")
    public_access_block: Optional[S3BucketPublicAccessBlock] = Field(None, description="Public access block configuration.")
    logging: Optional[S3BucketLogging] = Field(None, description="Server access logging configuration.")
    # Adicionar mais campos conforme necessário (ex: encryption, replication, lifecycle)
    error_details: Optional[str] = Field(None, description="Details of any error encountered while fetching data for this bucket.")


class S3CollectionError(BaseModel):
    error: str = Field(description="Error message detailing why data collection failed globally (e.g., credentials).")


# O response_model no controller será List[S3BucketData].
# Erros globais serão tratados levantando HTTPErrors.
# Erros específicos de buckets podem ser incluídos em `error_details` dentro de S3BucketData.
