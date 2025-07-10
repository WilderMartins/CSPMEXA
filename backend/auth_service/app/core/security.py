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

async def get_current_user_from_token( # Renomeado para clareza e para diferenciar de um get_current_user do request
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
    current_user: User = Depends(get_current_user_from_token),
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return current_user


def require_role(required_role: str):
    """
    Dependência FastAPI para exigir um papel específico do usuário.
    Usa get_current_active_user para obter o usuário e depois verifica seu papel.
    """
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        # O token JWT deve incluir um claim 'role'.
        # A função get_current_user_from_token já buscou o User do DB, que tem o campo role.
        if not current_user.role:
            # Log: Usuário não tem papel definido, mas deveria ter (default 'user')
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User role not defined.",
            )
        if current_user.role != required_role:
            # Se quisermos uma hierarquia (ex: admin pode fazer tudo que user faz),
            # a lógica aqui seria mais complexa (ex: if required_role == "user" and current_user.role == "admin": return current_user)
            # Para uma verificação exata de papel:
            # Log: Tentativa de acesso a recurso com papel insuficiente
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have the required '{required_role}' role.",
            )
        if required_role == "admin" and not current_user.is_superuser and current_user.role != "admin":
             # Exemplo de como 'is_superuser' poderia interagir ou ser um papel especial
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User requires admin privileges or to be a superuser.",
            )
        return current_user
    return role_checker


# Exemplo para superusuário, usando o campo is_superuser ou o papel 'admin'
async def get_current_active_superuser( # Nome mantido para consistência com usos anteriores
    current_user: User = Depends(get_current_active_user),
):
    if not current_user.is_superuser and current_user.role != "admin": # Adaptar conforme seu modelo
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="The user doesn't have enough privileges for this action."
        )
    return current_user
