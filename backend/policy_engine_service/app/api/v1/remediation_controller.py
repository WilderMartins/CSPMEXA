from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.schemas.remediation_request_schema import RemediationRequestSchema, RemediationRequestCreate
from app.crud.crud_remediation_request import remediation_request_crud
from app.crud.crud_alert import alert_crud
from app.models.remediation_request_model import RemediationStatusEnum
# Importar o cliente do collector service (a ser criado)
# from app.services.collector_client import collector_client

router = APIRouter()

@router.post("/", response_model=RemediationRequestSchema, status_code=201)
def request_remediation(
    *,
    db: Session = Depends(get_db),
    remediation_in: RemediationRequestCreate,
    # Obter o ID do usuário do token JWT (a ser implementado no gateway)
    # current_user: User = Depends(get_current_user)
):
    """
    Cria uma nova solicitação de remediação para um alerta.
    """
    alert = alert_crud.get(db, id=remediation_in.alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alerta não encontrado.")

    # remediation_in.requested_by_user_id = current_user.id
    remediation_request = remediation_request_crud.create(db=db, obj_in=remediation_in)
    return remediation_request

@router.post("/{remediation_id}/approve")
async def approve_remediation(
    remediation_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    # current_user: User = Depends(require_role("Manager"))
):
    """
    Aprova uma solicitação de remediação e aciona a execução em background.
    """
    remediation = remediation_request_crud.get(db, id=remediation_id)
    if not remediation:
        raise HTTPException(status_code=404, detail="Solicitação de remediação não encontrada.")
    if remediation.status != RemediationStatusEnum.PENDING:
        raise HTTPException(status_code=400, detail="Apenas solicitações pendentes podem ser aprovadas.")

    # approved_by = current_user.id
    approved_by = 999 # Placeholder
    remediation = remediation_request_crud.update_status(db, db_obj=remediation, status=RemediationStatusEnum.APPROVED, user_id=approved_by)

    # Adicionar a tarefa de execução da remediação em background
    # background_tasks.add_task(execute_remediation, db, remediation)

    return {"message": "Remediação aprovada e agendada para execução."}

# Função de execução (a ser movida para um serviço)
# async def execute_remediation(db: Session, remediation: RemediationRequestSchema):
#     remediation_request_crud.update_status(db, db_obj=remediation, status=RemediationStatusEnum.EXECUTING)
#     try:
#         # Lógica para chamar o collector_service
#         # await collector_client.remediate_s3(...)
#         remediation_request_crud.update_status(db, db_obj=remediation, status=RemediationStatusEnum.COMPLETED)
#     except Exception as e:
#         remediation_request_crud.update_status(db, db_obj=remediation, status=RemediationStatusEnum.FAILED)
