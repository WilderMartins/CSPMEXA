from fastapi import APIRouter, Depends, HTTPException, Request, Query
from typing import List, Optional, Any
import datetime

from app.services.http_client import policy_engine_service_client
from app.core.security import (
    TokenData,
    require_permission
)

require_user = require_permission("read:alert")
require_technical_lead = require_permission("update:alert_status")
require_manager = require_permission("update:alert_details")
require_administrator = require_permission("delete:alert")
from app.schemas.policy_engine_alert_schema import AlertSchema, AlertUpdate, AlertStatusEnum, AlertSeverityEnum

import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Helper function to proxy requests to the policy_engine_service for alerts
async def _proxy_alerts_request(
    method: str,
    endpoint: str, # Endpoint relative to POLICY_ENGINE_SERVICE_URL/alerts
    current_user: TokenData, # Ensure endpoint is protected
    request_obj: Request, # FastAPI Request object
    params: Optional[dict] = None,
    payload: Optional[dict] = None,
) -> Any:
    # Headers for downstream services.
    # For now, policy_engine_service does not validate the end-user token itself for /alerts,
    # but the gateway protects access to these proxied endpoints.
    downstream_headers = {}
    # If you needed to pass the original Authorization header:
    # auth_header = request_obj.headers.get("Authorization")
    # if auth_header:
    #     downstream_headers["Authorization"] = auth_header

    full_endpoint = f"/alerts{endpoint}" # Prepend /alerts to the specific endpoint path

    try:
        if method.upper() == "GET":
            response = await policy_engine_service_client.get(full_endpoint, params=params, headers=downstream_headers)
        elif method.upper() == "POST":
            response = await policy_engine_service_client.post(full_endpoint, data=payload, headers=downstream_headers, is_json_data=True)
        elif method.upper() == "PUT":
            response = await policy_engine_service_client.put(full_endpoint, data=payload, headers=downstream_headers, is_json_data=True)
        elif method.upper() == "PATCH":
            response = await policy_engine_service_client.patch(full_endpoint, data=payload, params=params, headers=downstream_headers, is_json_data=True)
        elif method.upper() == "DELETE":
            response = await policy_engine_service_client.delete(full_endpoint, params=params, headers=downstream_headers)
        else:
            logger.error(f"Unsupported proxy method: {method} for alerts endpoint {full_endpoint}")
            raise HTTPException(status_code=500, detail=f"Unsupported proxy method: {method}")

        # Process response
        if response.status_code >= 300: # Handle errors (2xx are success)
            detail_error = response.text
            try:
                detail_json = response.json()
                if isinstance(detail_json, dict) and "detail" in detail_json:
                    detail_error = detail_json["detail"]
            except Exception:
                pass
            logger.warning(f"Error from Policy Engine Service (Alerts - {full_endpoint}): Status {response.status_code}, Detail: {detail_error}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Policy Engine Service error (Alerts - {endpoint}): {detail_error}",
            )

        # For 204 No Content, return None or an empty dict, as .json() would fail
        if response.status_code == 204:
            return None

        return response.json()

    except HTTPException as e:
        raise e # Re-throw if already an HTTPException
    except Exception as e:
        logger.exception(f"Gateway error proxying to Policy Engine (Alerts - {full_endpoint})")
        raise HTTPException(
            status_code=500, detail=f"Gateway error proxying to Policy Engine for alerts: {str(e)}"
        )

@router.get("/", response_model=List[AlertSchema], name="alerts:list_alerts")
async def list_alerts_gateway(
    request: Request,
    current_user: TokenData = Depends(require_user), # Papel mínimo: User
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    sort_by: Optional[str] = Query(None),
    sort_order: Optional[str] = Query("desc"),
    provider: Optional[str] = Query(None),
    severity: Optional[AlertSeverityEnum] = Query(None),
    status: Optional[AlertStatusEnum] = Query(None),
    resource_id: Optional[str] = Query(None),
    policy_id: Optional[str] = Query(None),
    account_id: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    start_date: Optional[datetime.datetime] = Query(None),
    end_date: Optional[datetime.datetime] = Query(None),
):
    """
    Proxy to list alerts from the Policy Engine Service.
    """
    params = {
        "skip": skip, "limit": limit, "sort_by": sort_by, "sort_order": sort_order,
        "provider": provider, "severity": severity.value if severity else None,
        "status": status.value if status else None, "resource_id": resource_id,
        "policy_id": policy_id, "account_id": account_id, "region": region,
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
    }
    # Remove None params
    params = {k: v for k, v in params.items() if v is not None}
    return await _proxy_alerts_request("GET", "/", current_user, request, params=params)

@router.get("/{alert_id}", response_model=AlertSchema, name="alerts:get_alert")
async def get_alert_gateway(
    alert_id: int,
    request: Request,
    current_user: TokenData = Depends(require_user), # Papel mínimo: User
):
    """
    Proxy to get a specific alert by ID from the Policy Engine Service.
    """
    return await _proxy_alerts_request("GET", f"/{alert_id}", current_user, request)

@router.put("/{alert_id}", response_model=AlertSchema, name="alerts:update_alert_details")
async def update_alert_details_gateway(
    alert_id: int,
    alert_in: AlertUpdate, # Use the schema defined in gateway
    request: Request,
    current_user: TokenData = Depends(require_manager), # Papel mínimo: Manager
):
    """
    Proxy to update an alert's details in the Policy Engine Service.
    """
    return await _proxy_alerts_request("PUT", f"/{alert_id}", current_user, request, payload=alert_in.model_dump(exclude_unset=True))

@router.patch("/{alert_id}/status", response_model=AlertSchema, name="alerts:update_alert_status")
async def update_alert_status_gateway(
    alert_id: int,
    request: Request,
    new_status: AlertStatusEnum = Query(..., description="The new status for the alert"),
    current_user: TokenData = Depends(require_technical_lead), # Papel mínimo: TechnicalLead
):
    """
    Proxy to update only the status of an alert in the Policy Engine Service.
    """
    # The policy_engine_service expects `new_status` as a query parameter for its PATCH endpoint.
    params = {"new_status": new_status.value}
    return await _proxy_alerts_request("PATCH", f"/{alert_id}/status", current_user, request, params=params)

@router.delete("/{alert_id}", response_model=AlertSchema, name="alerts:delete_alert") # Or status_code=204 if no content
async def delete_alert_gateway(
    alert_id: int,
    request: Request,
    current_user: TokenData = Depends(require_administrator), # Papel mínimo: Administrator
):
    """
    Proxy to delete an alert by ID from the Policy Engine Service.
    """
    # If the downstream service returns 204, _proxy_alerts_request will return None.
    # If it returns the deleted object (e.g. with 200), it will be proxied.
    # The response_model here should match what the downstream service actually returns on delete.
    # If it's 204, then response_model should be None or excluded, and status_code set to 204.
    # For now, assuming policy_engine returns the deleted AlertSchema.
    return await _proxy_alerts_request("DELETE", f"/{alert_id}", current_user, request)

# Nota: O endpoint POST "/" para criar alertas geralmente não é exposto diretamente no gateway,
# pois os alertas são criados como resultado de uma operação de "/analyze".
# Se houvesse um caso de uso para criar alertas manualmente via API, ele seria adicionado aqui.
# Exemplo:
# @router.post("/", response_model=AlertSchema, status_code=201, name="alerts:create_alert_manually")
# async def create_alert_manually_gateway(
#     alert_in: AlertCreate, # Schema para criação manual
#     request: Request,
#     current_user: TokenData = Depends(get_current_user),
# ):
#     """ Proxy to manually create an alert (if such an endpoint exists on policy engine). """
#     return await _proxy_alerts_request("POST", "/", current_user, request, payload=alert_in.model_dump())
