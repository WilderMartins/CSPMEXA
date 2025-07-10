from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Any
from app.aws import s3_collector, ec2_collector, iam_collector
from app.schemas.s3 import S3BucketData
from app.schemas.ec2 import Ec2InstanceData, SecurityGroup
from app.schemas.iam import IAMUserData, IAMRoleData, IAMPolicyData

# from app.core.security import get_current_active_user # Se precisarmos de autenticação para este endpoint
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/s3", response_model=List[S3BucketData])
async def collect_s3_data(
    # current_user: Any = Depends(get_current_active_user) # Descomentar se autenticação for necessária
):
    """
    Endpoint para coletar dados de configuração de buckets S3.
    Retorna uma lista de dados de buckets S3 ou levanta HTTPException em caso de erro global.
    Erros específicos de bucket são incluídos no campo 'error_details' de cada item da lista.
    """
    try:
        data = await s3_collector.get_s3_data()
        return data
    except HTTPException as http_exc:
        logger.error(f"HTTPException during S3 data collection: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.exception("Unexpected error in collect_s3_data endpoint")
        raise HTTPException(
            status_code=500, detail=f"An unexpected internal server error occurred: {str(e)}"
        )

@router.get("/ec2/instances", response_model=List[Ec2InstanceData])
async def collect_ec2_instances_data(
    # current_user: Any = Depends(get_current_active_user)
):
    """
    Endpoint para coletar dados de instâncias EC2 de todas as regiões habilitadas.
    Erros de coleta em uma região específica podem ser indicados no campo 'error_details'
    do objeto Ec2InstanceData correspondente a essa região (com instance_id="ERROR_REGION").
    """
    try:
        data = await ec2_collector.get_ec2_instance_data_all_regions()
        return data
    except HTTPException as http_exc: # Erros globais como falha de credenciais em get_all_regions
        logger.error(f"HTTPException during EC2 instance data collection: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.exception("Unexpected error in collect_ec2_instances_data endpoint")
        raise HTTPException(
            status_code=500, detail=f"An unexpected internal server error occurred: {str(e)}"
        )

@router.get("/ec2/security-groups", response_model=List[SecurityGroup])
async def collect_ec2_security_groups_data(
    # current_user: Any = Depends(get_current_active_user)
):
    """
    Endpoint para coletar dados de Security Groups EC2 de todas as regiões habilitadas.
    Falhas na coleta de uma região específica são logadas, mas a coleta continua para outras regiões.
    O endpoint pode retornar uma lista parcial se algumas regiões falharem.
    """
    try:
        data = await ec2_collector.get_security_group_data_all_regions()
        return data
    except HTTPException as http_exc: # Erros globais como falha de credenciais em get_all_regions
        logger.error(f"HTTPException during EC2 Security Group data collection: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.exception("Unexpected error in collect_ec2_security_groups_data endpoint")
        raise HTTPException(
            status_code=500, detail=f"An unexpected internal server error occurred: {str(e)}"
        )


@router.get("/iam/users", response_model=List[IAMUserData])
async def collect_iam_users_data(
    # current_user: Any = Depends(get_current_active_user)
):
    """
    Endpoint para coletar dados de usuários IAM.
    """
    try:
        data = await iam_collector.get_iam_users_data()
        return data
    except HTTPException as http_exc:
        logger.error(f"HTTPException during IAM users data collection: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.exception("Unexpected error in collect_iam_users_data endpoint")
        raise HTTPException(
            status_code=500, detail=f"An unexpected internal server error occurred: {str(e)}"
        )

@router.get("/iam/roles", response_model=List[IAMRoleData])
async def collect_iam_roles_data(
    # current_user: Any = Depends(get_current_active_user)
):
    """
    Endpoint para coletar dados de roles IAM.
    """
    try:
        data = await iam_collector.get_iam_roles_data()
        return data
    except HTTPException as http_exc:
        logger.error(f"HTTPException during IAM roles data collection: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.exception("Unexpected error in collect_iam_roles_data endpoint")
        raise HTTPException(
            status_code=500, detail=f"An unexpected internal server error occurred: {str(e)}"
        )

@router.get("/iam/policies", response_model=List[IAMPolicyData])
async def collect_iam_policies_data(
    scope: str = Query("Local", enum=["All", "AWS", "Local"]),
    # current_user: Any = Depends(get_current_active_user)
):
    """
    Endpoint para coletar dados de políticas IAM gerenciadas.
    Use o parâmetro 'scope' para filtrar por 'All', 'AWS', ou 'Local' (padrão).
    """
    try:
        data = await iam_collector.get_iam_policies_data(scope=scope)
        return data
    except HTTPException as http_exc:
        logger.error(f"HTTPException during IAM policies data collection (scope: {scope}): {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.exception(f"Unexpected error in collect_iam_policies_data endpoint (scope: {scope})")
        raise HTTPException(
            status_code=500, detail=f"An unexpected internal server error occurred: {str(e)}"
        )
