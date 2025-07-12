from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import datetime

from app.db.session import get_db
from app.crud.crud_alert import alert_crud
from app.schemas.alert_schema import AlertSchema, AlertCreate, AlertUpdate, AlertStatusEnum, AlertSeverityEnum
from app.models.alert_model import AlertModel # For direct model usage if necessary
from app.core.security import verify_internal_api_key

router = APIRouter(dependencies=[Depends(verify_internal_api_key)])

@router.post("/", response_model=AlertSchema, status_code=201)
def create_alert(
    *,
    db: Session = Depends(get_db),
    alert_in: AlertCreate
):
    """
    Create a new alert.
    If an identical open alert already exists (based on provider, resource_id, policy_id, status=OPEN),
    it will update the `last_seen_at` of the existing alert instead of creating a new one.
    """
    alert = alert_crud.create_alert(db=db, alert_in=alert_in)
    return alert

@router.get("/{alert_id}", response_model=AlertSchema)
def read_alert(
    *,
    db: Session = Depends(get_db),
    alert_id: int,
):
    """
    Get a specific alert by ID.
    """
    alert = alert_crud.get_alert(db=db, alert_id=alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert

@router.get("/", response_model=List[AlertSchema])
def read_alerts(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500), # Added max limit
    sort_by: Optional[str] = Query(None, description="Column to sort by (e.g., 'created_at', 'severity', 'status')"),
    sort_order: Optional[str] = Query("desc", description="Sort order: 'asc' or 'desc'"),
    provider: Optional[str] = Query(None, description="Filter by provider (e.g., 'aws', 'gcp')"),
    severity: Optional[AlertSeverityEnum] = Query(None, description="Filter by severity level"),
    status: Optional[AlertStatusEnum] = Query(None, description="Filter by status"),
    resource_id: Optional[str] = Query(None, description="Filter by resource ID (partial match)"),
    policy_id: Optional[str] = Query(None, description="Filter by policy ID"),
    account_id: Optional[str] = Query(None, description="Filter by account ID"),
    region: Optional[str] = Query(None, description="Filter by region"),
    start_date: Optional[datetime.datetime] = Query(None, description="Filter alerts created after this date (ISO format)"),
    end_date: Optional[datetime.datetime] = Query(None, description="Filter alerts created before this date (ISO format)")
):
    """
    Retrieve a list of alerts with optional filtering and pagination.
    """
    alerts = alert_crud.get_alerts(
        db=db, skip=skip, limit=limit, sort_by=sort_by, sort_order=sort_order,
        provider=provider, severity=severity, status=status, resource_id=resource_id,
        policy_id=policy_id, account_id=account_id, region=region,
        start_date=start_date, end_date=end_date
    )
    return alerts

@router.put("/{alert_id}", response_model=AlertSchema)
def update_alert_details(
    *,
    db: Session = Depends(get_db),
    alert_id: int,
    alert_in: AlertUpdate,
):
    """
    Update an alert's mutable details (e.g., status, severity, custom details, recommendation).
    """
    alert_db_obj = alert_crud.get_alert(db=db, alert_id=alert_id)
    if not alert_db_obj:
        raise HTTPException(status_code=404, detail="Alert not found")

    updated_alert = alert_crud.update_alert(db=db, alert_id=alert_id, alert_in=alert_in)
    return updated_alert

@router.patch("/{alert_id}/status", response_model=AlertSchema)
def update_alert_status_only(
    *,
    db: Session = Depends(get_db),
    alert_id: int,
    new_status: AlertStatusEnum = Query(..., description="The new status for the alert")
):
    """
    Quickly update the status of an alert.
    """
    alert = alert_crud.update_alert_status(db=db, alert_id=alert_id, status=new_status)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.delete("/{alert_id}", response_model=AlertSchema)
def delete_alert(
    *,
    db: Session = Depends(get_db),
    alert_id: int,
):
    """
    Delete an alert by ID.
    """
    alert = alert_crud.get_alert(db=db, alert_id=alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found to delete")

    deleted_alert_obj = alert_crud.remove_alert(db=db, alert_id=alert_id)
    # remove_alert returns the object that was deleted, so we can return it.
    # If it couldn't be found for deletion (e.g. race condition), it would be None.
    if not deleted_alert_obj:
         raise HTTPException(status_code=404, detail="Alert could not be deleted or was already deleted.")
    return deleted_alert_obj
