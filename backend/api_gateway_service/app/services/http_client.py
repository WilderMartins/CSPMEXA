import httpx
from fastapi import HTTPException, status
from typing import Optional, Dict, Any, Union
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class HttpClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.timeout = settings.HTTP_CLIENT_TIMEOUT

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[
            Union[Dict[str, Any], Any]
        ] = None,  # Permite enviar dados não-JSON também
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        is_json_data: bool = True,  # Flag para controlar se o 'data' é JSON
    ) -> httpx.Response:
        url = f"{self.base_url}{endpoint}"

        # Prepare headers for internal communication
        internal_headers = {
            "X-Internal-API-Key": settings.INTERNAL_API_KEY
        }
        if headers:
            internal_headers.update(headers)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if is_json_data:
                    response = await client.request(
                        method, url, json=data, params=params, headers=internal_headers
                    )
                else:
                    response = await client.request(
                        method, url, data=data, params=params, headers=internal_headers
                    )
                # response.raise_for_status() # Levanta exceção para 4xx/5xx, pode ser muito agressivo aqui
                return response
        except httpx.TimeoutException:
            logger.error(f"Timeout requesting {method} {url}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Request to downstream service timed out: {url}",
            )
        except httpx.RequestError as e:
            logger.error(f"RequestError for {method} {url}: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Error connecting to downstream service: {url}",
            )
        except Exception as e:
            logger.error(f"Unexpected error in HttpClient for {method} {url}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred in HttpClient.",
            )

    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        return await self._request("GET", endpoint, params=params, headers=headers)

    async def post(
        self,
        endpoint: str,
        data: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        is_json_data: bool = True,
    ) -> httpx.Response:
        return await self._request(
            "POST",
            endpoint,
            data=data,
            params=params,
            headers=headers,
            is_json_data=is_json_data,
        )

    async def put(
        self,
        endpoint: str,
        data: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        is_json_data: bool = True,
    ) -> httpx.Response:
        return await self._request(
            "PUT",
            endpoint,
            data=data,
            params=params,
            headers=headers,
            is_json_data=is_json_data,
        )

    async def delete(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        return await self._request("DELETE", endpoint, params=params, headers=headers)


# Instâncias de cliente para cada serviço downstream
auth_service_client = HttpClient(base_url=settings.AUTH_SERVICE_URL)
collector_service_client = HttpClient(base_url=settings.COLLECTOR_SERVICE_URL)
policy_engine_service_client = HttpClient(base_url=settings.POLICY_ENGINE_SERVICE_URL)
