from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from typing import Optional, List
from app.core.config import settings
from app.models.user_model import UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/google/login")

class TokenData(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None
    role: Optional[UserRole] = None

async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        user_id_from_token = payload.get("sub")
        if user_id_from_token is None:
            raise credentials_exception

        token_data = TokenData(
            user_id=int(user_id_from_token),
            email=payload.get("email"),
            role=payload.get("role")
        )
    except JWTError:
        raise credentials_exception
    except Exception:
        raise credentials_exception

    return token_data

def require_role(allowed_roles: List[UserRole]):
    async def role_checker(current_user: TokenData = Depends(get_current_user)) -> TokenData:
        allowed_role_values = [role.value for role in allowed_roles]
        if current_user.role not in allowed_role_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User with role '{current_user.role}' does not have the required permissions. Allowed roles: {', '.join(allowed_role_values)}",
            )
        return current_user
    return role_checker
