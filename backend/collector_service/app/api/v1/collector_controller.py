from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from app.aws import s3_collector  # , ec2_collector, iam_collector (serão adicionados)

# from app.core.security import get_current_active_user # Se precisarmos de autenticação para este endpoint

router = APIRouter()


@router.get("/s3", response_model=List[Dict[str, Any]])
async def collect_s3_data(
    # current_user: Any = Depends(get_current_active_user) # Descomentar se autenticação for necessária
):
    """
    Endpoint para coletar dados de configuração de buckets S3.
    """
    try:
        data = await s3_collector.get_s3_data()
        if data and isinstance(data, list) and data[0].get("error"):
            # Tratar o caso de erro retornado por list_s3_buckets
            raise HTTPException(status_code=500, detail=data[0]["error"])
        return data
    except Exception as e:
        # Logar a exceção e retornar um erro genérico
        # import logging; logging.exception("Error in collect_s3_data")
        raise HTTPException(
            status_code=500, detail=f"An internal server error occurred: {str(e)}"
        )


# Endpoints para EC2 e IAM serão adicionados aqui
# @router.get("/ec2")
# async def collect_ec2_data():
#     # data = await ec2_collector.get_ec2_data()
#     # return data
#     return {"message": "EC2 collector not yet implemented"}

# @router.get("/iam")
# async def collect_iam_data():
#     # data = await iam_collector.get_iam_data()
#     # return data
#     return {"message": "IAM collector not yet implemented"}
