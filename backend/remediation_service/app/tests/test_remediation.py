import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_remediate_s3_bucket_public_acl():
    response = client.post(
        "/remediate",
        json={
            "provider": "aws",
            "policy_id": "S3_BUCKET_PUBLIC_ACL",
            "resource_id": "my-bucket",
            "credentials": {
                "aws_access_key_id": "test",
                "aws_secret_access_key": "test",
            },
        },
    )
    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "message": "Remediation for my-bucket completed successfully.",
    }

def test_remediate_iam_user_no_mfa():
    response = client.post(
        "/remediate",
        json={
            "provider": "aws",
            "policy_id": "IAM_USER_NO_MFA",
            "resource_id": "my-user",
            "credentials": {
                "aws_access_key_id": "test",
                "aws_secret_access_key": "test",
            },
        },
    )
    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "message": "Remediation for my-user completed successfully.",
    }

def test_remediate_policy_not_found():
    response = client.post(
        "/remediate",
        json={
            "provider": "aws",
            "policy_id": "POLICY_NOT_FOUND",
            "resource_id": "my-resource",
            "credentials": {
                "aws_access_key_id": "test",
                "aws_secret_access_key": "test",
            },
        },
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Policy POLICY_NOT_FOUND not found for provider aws"}

def test_remediate_provider_not_found():
    response = client.post(
        "/remediate",
        json={
            "provider": "PROVIDER_NOT_FOUND",
            "policy_id": "S3_BUCKET_PUBLIC_ACL",
            "resource_id": "my-resource",
            "credentials": {
                "aws_access_key_id": "test",
                "aws_secret_access_key": "test",
            },
        },
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Provider PROVIDER_NOT_FOUND not found"}
