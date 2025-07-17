from fastapi import APIRouter, HTTPException
from typing import List
from app.aws import s3_collector, ec2_collector, iam_collector, cloudtrail_collector
from app.schemas.s3 import S3BucketData
from app.schemas.ec2 import Ec2InstanceData, SecurityGroup
from app.schemas.iam import IAMUserData, IAMRoleData, IAMPolicyData
from app.schemas.collector_cloudtrail_schemas import CloudTrailData
from app.schemas.base import CredentialsPayload
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/s3", response_model=List[S3BucketData])
async def collect_s3_data(payload: CredentialsPayload):
    try:
        data = await s3_collector.get_s3_data(credentials=payload.credentials)
        return data
    except Exception as e:
        logger.exception("Erro ao coletar dados do S3.")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ec2/instances", response_model=List[Ec2InstanceData])
async def collect_ec2_instances_data(payload: CredentialsPayload):
    try:
        data = await ec2_collector.get_ec2_instance_data_all_regions(credentials=payload.credentials)
        return data
    except Exception as e:
        logger.exception("Erro ao coletar dados de instâncias EC2.")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ec2/security-groups", response_model=List[SecurityGroup])
async def collect_ec2_security_groups_data(payload: CredentialsPayload):
    try:
        data = await ec2_collector.get_security_group_data_all_regions(credentials=payload.credentials)
        return data
    except Exception as e:
        logger.exception("Erro ao coletar dados de Security Groups.")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/iam/users", response_model=List[IAMUserData])
async def collect_iam_users_data(payload: CredentialsPayload):
    try:
        data = await iam_collector.get_iam_users_data(credentials=payload.credentials)
        return data
    except Exception as e:
        logger.exception("Erro ao coletar dados de usuários IAM.")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/iam/roles", response_model=List[IAMRoleData])
async def collect_iam_roles_data(payload: CredentialsPayload):
    try:
        data = await iam_collector.get_iam_roles_data(credentials=payload.credentials)
        return data
    except Exception as e:
        logger.exception("Erro ao coletar dados de roles IAM.")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/iam/policies", response_model=List[IAMPolicyData])
async def collect_iam_policies_data(payload: CredentialsPayload, scope: str = "Local"):
    try:
        data = await iam_collector.get_iam_policies_data(credentials=payload.credentials, scope=scope)
        return data
    except Exception as e:
        logger.exception("Erro ao coletar dados de políticas IAM.")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cloudtrail", response_model=List[CloudTrailData])
async def collect_cloudtrail_data(payload: CredentialsPayload):
    try:
        data = await cloudtrail_collector.list_trails(credentials=payload.credentials)
        return data
    except Exception as e:
        logger.exception("Erro ao coletar dados do CloudTrail.")
        raise HTTPException(status_code=500, detail=str(e))
