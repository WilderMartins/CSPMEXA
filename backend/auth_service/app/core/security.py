from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, ValidationError # Importar ValidationError
from typing import Optional

from app.core.config import settings
from app.db.session import get_db
from sqlalchemy.orm import Session
from app.models.user_model import User
# from app.services.user_service import user_service # Evitar dependência circular se user_service usar isso

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token")

class TokenPayload(BaseModel): # Renomeado para TokenPayload para clareza
    sub: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    # Adicionar outros campos que você coloca no token
    # google_id: Optional[str] = None # Se incluído no token

async def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload_dict = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        user_id_from_sub: Optional[str] = payload_dict.get("sub")
        if user_id_from_sub is None:
            raise credentials_exception

        # Validar o payload com Pydantic (opcional, mas bom)
        # token_data = TokenPayload(**payload_dict)

    except JWTError as e:
        import logging
        logging.warning(f"JWTError in auth-service token validation: {e}")
        raise credentials_exception
    # except ValidationError as e: # Se usar TokenPayload(**payload_dict)
    #     import logging
    #     logging.warning(f"Token payload validation error: {e}")
    #     raise credentials_exception

    try:
        user_id = int(user_id_from_sub)
    except ValueError:
        # Log: user_id (sub) no token não é um inteiro válido
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user( # Esta é a dependência principal para endpoints protegidos
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return current_user



def require_permission(permission: str):
    """
    Dependência FastAPI para exigir uma permissão específica.
    """
    async def permission_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if permission not in current_user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have the required '{permission}' permission.",
            )
        return current_user
    return permission_checker
