from fastapi import APIRouter, HTTPException, Body
from typing import List
from app.schemas.input_data_schema import AnalysisRequest
from app.schemas.alert_schema import Alert
from app.engine import s3_policy_checker  # , ec2_policy_checker, iam_policy_checker

router = APIRouter()


@router.post("/analyze", response_model=List[Alert])
async def analyze_resources(analysis_request: AnalysisRequest = Body(...)):
    """
    Endpoint para analisar dados de configuração de recursos e retornar alertas.
    No MVP, foca em dados S3.
    """
    alerts: List[Alert] = []

    if analysis_request.s3_data:
        try:
            s3_alerts = s3_policy_checker.analyze_s3_data(analysis_request.s3_data)
            alerts.extend(s3_alerts)
        except Exception as e:
            # Log a exceção
            # import logging; logging.exception("Error during S3 analysis")
            # Considerar se um erro na análise de S3 deve parar toda a análise ou apenas ser logado
            raise HTTPException(
                status_code=500, detail=f"Error during S3 data analysis: {str(e)}"
            )

    # Adicionar chamadas para outros checkers (EC2, IAM) aqui no futuro
    # if analysis_request.ec2_data:
    #     ec2_alerts = ec2_policy_checker.analyze_ec2_data(analysis_request.ec2_data)
    #     alerts.extend(ec2_alerts)

    if not alerts and not analysis_request.s3_data:  # Se nenhum dado foi enviado
        return []  # Retorna lista vazia se nenhum dado foi processado
        # Ou poderia ser um HTTPException(status_code=400, detail="No resource data provided for analysis")

    return alerts
