from fastapi import Depends, HTTPException, status, Security
from fastapi.security import APIKeyHeader

from app.core.config import settings

# Dependency for internal service-to-service authentication
api_key_header = APIKeyHeader(name="X-Internal-API-Key", auto_error=True)

async def verify_internal_api_key(api_key: str = Security(api_key_header)):
    """
    Verifies that the provided API key in the X-Internal-API-Key header matches
    the one configured in the settings.
    """
    if api_key != settings.INTERNAL_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing internal API Key",
        )
