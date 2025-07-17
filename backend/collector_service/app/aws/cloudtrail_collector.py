import boto3
from typing import List, Dict, Any
from app.schemas.collector_cloudtrail_schemas import CloudTrailTrail, CloudTrailStatus, CloudTrailData
from app.core.config import get_credentials_from_vault
from fastapi.concurrency import run_in_threadpool

def list_trails_sync(credentials: Dict[str, Any]) -> List[CloudTrailData]:
    """
    Lista todos os CloudTrails na conta e obtém seu status.
    """
    session = boto3.Session(
        aws_access_key_id=credentials.get("aws_access_key_id"),
        aws_secret_access_key=credentials.get("aws_secret_access_key"),
        aws_session_token=credentials.get("aws_session_token"),
    )

    ec2_client = session.client('ec2', region_name='us-east-1')
    regions = [region['RegionName'] for region in ec2_client.describe_regions()['Regions']]

    all_trails_data: List[CloudTrailData] = []
    trail_arns_processed = set()

    for region in regions:
        cloudtrail_client = session.client('cloudtrail', region_name=region)
        try:
            paginator = cloudtrail_client.get_paginator('describe_trails')
            for page in paginator.paginate():
                for trail in page.get('trailList', []):
                    trail_arn = trail['TrailARN']
                    if trail_arn in trail_arns_processed:
                        continue
                    trail_arns_processed.add(trail_arn)

                    status_response = cloudtrail_client.get_trail_status(Name=trail_arn)

                    trail_info = CloudTrailTrail(
                        name=trail.get('Name'),
                        s3_bucket_name=trail.get('S3BucketName'),
                        is_multi_region_trail=trail.get('IsMultiRegionTrail', False),
                        log_file_validation_enabled=trail.get('LogFileValidationEnabled', False),
                        home_region=trail.get('HomeRegion'),
                        trail_arn=trail_arn
                    )

                    status_info = CloudTrailStatus(
                        is_logging=status_response.get('IsLogging', False),
                        latest_delivery_time=str(status_response.get('LatestDeliveryTime')),
                        latest_notification_time=str(status_response.get('LatestNotificationTime')),
                        start_logging_time=str(status_response.get('StartLoggingTime')),
                        stop_logging_time=str(status_response.get('StopLoggingTime')),
                        latest_error=status_response.get('LatestDeliveryError')
                    )

                    all_trails_data.append(CloudTrailData(trail_info=trail_info, status=status_info))
        except Exception as e:
            print(f"Erro ao descrever trails na região {region}: {e}")
            continue

    return all_trails_data

async def list_trails() -> List[CloudTrailData]:
    aws_credentials = get_credentials_from_vault("aws")
    if not aws_credentials:
        raise Exception("Credenciais da AWS não encontradas no Vault.")
    return await run_in_threadpool(list_trails_sync, credentials=aws_credentials)
