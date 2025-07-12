import pytest
import datetime
from app.engine.gcp_cai_policies import evaluate_gcp_cai_policies, REQUIRED_LABELS_BY_ASSET_TYPE
from app.schemas.gcp.gcp_cai_input_schemas import GCPAssetCollectionInput, GCPAssetInput
from app.schemas.alert_schema import AlertSeverityEnum

GCP_ACCOUNT_ID = "projects/test-project-cai" # Escopo da consulta

@pytest.fixture
def cai_compute_instance_missing_labels():
    return GCPAssetInput(
        name="//compute.googleapis.com/projects/test-project-cai/zones/us-central1-a/instances/instance-1",
        assetType="compute.googleapis.com/Instance",
        project_id="test-project-cai",
        location="us-central1-a",
        resource={"labels": {"name": "my-vm"}} # Falta owner, environment, cost-center
    )

@pytest.fixture
def cai_compute_instance_all_labels():
    labels = {key: "test-value" for key in REQUIRED_LABELS_BY_ASSET_TYPE.get("compute.googleapis.com/Instance", [])}
    return GCPAssetInput(
        name="//compute.googleapis.com/projects/test-project-cai/zones/us-central1-a/instances/instance-2",
        assetType="compute.googleapis.com/Instance",
        project_id="test-project-cai",
        location="us-central1-a",
        resource={"labels": labels}
    )

@pytest.fixture
def cai_storage_bucket_missing_labels():
    return GCPAssetInput(
        name="//storage.googleapis.com/projects/_/buckets/my-bucket-missing-labels",
        assetType="storage.googleapis.com/Bucket",
        project_id="test-project-cai", # Extraído do nome ou fornecido
        location="US-MULTIREGION",
        resource={"labels": {"department": "finance"}} # Falta owner, data-classification, cost-center
    )

@pytest.fixture
def cai_unsupported_asset_type():
    return GCPAssetInput(
        name="//unsupported.googleapis.com/projects/test-project-cai/services/my-service",
        assetType="unsupported.googleapis.com/Service",
        project_id="test-project-cai"
    )

def test_gcp_cai_missing_labels_compute_instance(cai_compute_instance_missing_labels):
    asset_collection = GCPAssetCollectionInput(assets=[cai_compute_instance_missing_labels], scope_queried=GCP_ACCOUNT_ID)
    alerts = evaluate_gcp_cai_policies(asset_collection, GCP_ACCOUNT_ID)

    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["policy_id"] == "GCP_Resource_Missing_Required_Labels"
    assert alert["resource_id"] == cai_compute_instance_missing_labels.name
    assert alert["severity"] == AlertSeverityEnum.LOW
    assert "compute.googleapis.com/Instance" in alert["title"]
    assert "owner" in alert["details"]["missing_labels"]
    assert "environment" in alert["details"]["missing_labels"]
    assert "cost-center" in alert["details"]["missing_labels"]

def test_gcp_cai_all_labels_compute_instance(cai_compute_instance_all_labels):
    asset_collection = GCPAssetCollectionInput(assets=[cai_compute_instance_all_labels], scope_queried=GCP_ACCOUNT_ID)
    alerts = evaluate_gcp_cai_policies(asset_collection, GCP_ACCOUNT_ID)
    assert len(alerts) == 0

def test_gcp_cai_missing_labels_storage_bucket(cai_storage_bucket_missing_labels):
    asset_collection = GCPAssetCollectionInput(assets=[cai_storage_bucket_missing_labels], scope_queried=GCP_ACCOUNT_ID)
    alerts = evaluate_gcp_cai_policies(asset_collection, GCP_ACCOUNT_ID)

    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["policy_id"] == "GCP_Resource_Missing_Required_Labels"
    assert "storage.googleapis.com/Bucket" in alert["title"]
    assert "owner" in alert["details"]["missing_labels"]
    assert "data-classification" in alert["details"]["missing_labels"]
    assert "cost-center" in alert["details"]["missing_labels"]

def test_gcp_cai_unsupported_asset_type_no_alert(cai_unsupported_asset_type):
    asset_collection = GCPAssetCollectionInput(assets=[cai_unsupported_asset_type], scope_queried=GCP_ACCOUNT_ID)
    alerts = evaluate_gcp_cai_policies(asset_collection, GCP_ACCOUNT_ID)
    assert len(alerts) == 0 # Nenhuma política de label para este tipo

def test_gcp_cai_collection_error():
    error_msg = "Global CAI collection failed."
    asset_collection_error = GCPAssetCollectionInput(error_message=error_msg, scope_queried=GCP_ACCOUNT_ID)
    alerts = evaluate_gcp_cai_policies(asset_collection_error, GCP_ACCOUNT_ID)

    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["policy_id"] == "GCP_CAI_GlobalCollection_Error"
    assert alert["severity"] == AlertSeverityEnum.MEDIUM
    assert error_msg in alert["description"]

def test_gcp_cai_asset_parsing_error():
    asset_with_error = GCPAssetInput(
        name="//error.asset/name",
        assetType="error.Type",
        collection_error_details="Failed to parse this asset."
    )
    asset_collection = GCPAssetCollectionInput(assets=[asset_with_error], scope_queried=GCP_ACCOUNT_ID)
    alerts = evaluate_gcp_cai_policies(asset_collection, GCP_ACCOUNT_ID)

    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["policy_id"] == "GCP_CAI_AssetParsing_Error"
    assert alert["severity"] == AlertSeverityEnum.INFORMATIONAL
    assert "Failed to parse this asset" in alert["description"]

```
