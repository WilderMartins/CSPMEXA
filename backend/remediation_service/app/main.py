from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

app = FastAPI(
    title="Remediation Service",
    description="Service for automated remediation of security issues.",
    version="1.0.0"
)

class RemediationRequest(BaseModel):
    provider: str
    policy_id: str
    resource_id: str
    credentials: Dict[str, Any]

import boto3
from botocore.exceptions import ClientError

@app.post("/remediate", summary="Trigger a remediation action")
async def remediate(request: RemediationRequest):
    """
    Triggers a remediation action for a given policy and resource.
    """
    if request.provider == "aws":
        if request.policy_id == "S3_BUCKET_PUBLIC_ACL":
            try:
                s3 = boto3.client(
                    "s3",
                    aws_access_key_id=request.credentials.get("aws_access_key_id"),
                    aws_secret_access_key=request.credentials.get("aws_secret_access_key"),
                )
                s3.put_public_access_block(
                    Bucket=request.resource_id,
                    PublicAccessBlockConfiguration={
                        "BlockPublicAcls": True,
                        "IgnorePublicAcls": True,
                        "BlockPublicPolicy": True,
                        "RestrictPublicBuckets": True,
                    },
                )
                return {"status": "success", "message": f"Remediation for {request.resource_id} completed successfully."}
            except ClientError as e:
                raise HTTPException(status_code=500, detail=str(e))
        elif request.policy_id == "IAM_USER_NO_MFA":
            try:
                iam = boto3.client(
                    "iam",
                    aws_access_key_id=request.credentials.get("aws_access_key_id"),
                    aws_secret_access_key=request.credentials.get("aws_secret_access_key"),
                )
                iam.attach_user_policy(
                    UserName=request.resource_id,
                    PolicyArn="arn:aws:iam::aws:policy/IAMUserChangePassword"
                )
                return {"status": "success", "message": f"Remediation for {request.resource_id} completed successfully."}
            except ClientError as e:
                raise HTTPException(status_code=500, detail=str(e))
        else:
            raise HTTPException(status_code=404, detail=f"Policy {request.policy_id} not found for provider {request.provider}")
    else:
        raise HTTPException(status_code=404, detail=f"Provider {request.provider} not found")

@app.get("/health", summary="Health check")
async def health_check():
    """
    Health check endpoint.
    """
    return {"status": "ok"}
