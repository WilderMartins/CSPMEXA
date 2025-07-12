from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, ValidationError # Importar Field se usar Pydantic V2 com default_factory
from typing import Optional, List
import enum # Para o Enum de Roles

from app.core.config import settings


# Definir os papéis aqui para que o security module os conheça.
# Idealmente, isso viria de um local compartilhado se o auth_service também precisasse referenciá-lo
# diretamente, mas como o token JWT conterá o valor string do UserRole do auth_service,
# podemos definir um Enum correspondente aqui para facilitar a verificação.
class UserRoleEnum(str, enum.Enum):
    USER = "User"
    TECHNICAL_LEAD = "TechnicalLead"
    MANAGER = "Manager"
    ADMINISTRATOR = "Administrator"
    SUPER_ADMINISTRATOR = "SuperAdministrator"

# Hierarquia dos papéis (do menos privilegiado para o mais privilegiado)
# Isso ajudará a verificar se um usuário tem um papel "igual ou superior"
ROLE_HIERARCHY = {
    UserRoleEnum.USER: 1,
    UserRoleEnum.TECHNICAL_LEAD: 2,
    UserRoleEnum.MANAGER: 3,
    UserRoleEnum.ADMINISTRATOR: 4,
    UserRoleEnum.SUPER_ADMINISTRATOR: 5,
}


# Este é o URL que o frontend usaria para "logar" (obter o token).
# No nosso caso, o login é via Google, e o token é obtido após o callback.
# O frontend armazenaria o token e o enviaria nas chamadas subsequentes.
# Este tokenUrl pode apontar para um endpoint no gateway que inicia o fluxo OAuth
# ou ser apenas um placeholder se o token é obtido de outra forma.
# Para o propósito da dependência OAuth2PasswordBearer, ele precisa ser definido.
# Vamos apontá-lo para o endpoint de login do Google no gateway.
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/google/login"
)


class TokenData(BaseModel):
    user_id: Optional[int] = None  # Ou str, dependendo do que o auth-service coloca no 'sub'
    email: Optional[str] = None
    role: Optional[str] = None
    # Adicionar outros claims relevantes que o auth_service possa incluir


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
        # O auth-service deve colocar o ID do usuário no campo 'sub' (subject) do JWT
        user_id_from_token = payload.get("sub")
        if user_id_from_token is None:
            raise credentials_exception

        # Você pode adicionar mais validações aqui se necessário (ex: verificar 'exp')
        # A biblioteca python-jose já valida 'exp' por padrão.

        # Extrair outros claims esperados
        email_from_token = payload.get("email")
        role_from_token = payload.get("role")

        token_data = TokenData(
            user_id=int(user_id_from_token), # Assumindo que user_id é int
            email=email_from_token,
            role=role_from_token
        )
    except JWTError as exc:
        import logging
        logging.warning(f"JWTError during token decoding: {exc}")
        raise credentials_exception
    except ValidationError as exc:  # Se o TokenData falhar na validação
        import logging
        logging.warning(f"TokenData ValidationError: {exc}")
        raise credentials_exception
    except Exception as exc:  # Outras exceções
        import logging
        logging.exception(f"Unexpected error in get_current_user: {exc}") # Usando logging.exception para incluir stack trace
        raise credentials_exception

    return token_data


# --- Dependências para verificação de roles ---

async def require_role(required_role: str, current_user: TokenData = Depends(get_current_user)):
    """
    Verifica se o usuário atual possui o role especificado.
    Levanta HTTPException 403 se o role não corresponder.
    """
    Verifica se o usuário atual possui o papel especificado ou um superior na hierarquia.
    Levanta HTTPException 403 se o papel não for suficiente.
    `required_role` pode ser um valor string do Enum UserRoleEnum.
    """
    if not current_user.role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User role is not defined in token.",
        )
    try:
        # O 'role' no token é uma string, ex: "User", "Administrator"
        user_role_enum_value = UserRoleEnum(current_user.role)

        # required_role (string) deve ser um valor do UserRoleEnum
        if isinstance(required_role, str):
            required_role_enum_value = UserRoleEnum(required_role)
        elif isinstance(required_role, UserRoleEnum): # Se já for Enum (uso interno)
            required_role_enum_value = required_role
        else:
            raise HTTPException(status_code=500, detail="Invalid required_role type for permission check.")

    except ValueError:
        # Se o role no token ou o required_role não for um valor válido do Enum UserRoleEnum
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Invalid role specified or found in token. User role: '{current_user.role}'. Allowed roles: {[r.value for r in UserRoleEnum]}.",
        )

    user_level = ROLE_HIERARCHY.get(user_role_enum_value, 0)
    required_level = ROLE_HIERARCHY.get(required_role_enum_value, float('inf'))

    if user_level < required_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User role '{current_user.role}' does not meet minimum requirement of '{required_role_enum_value.value}'.",
        )
    return current_user

# Funções de dependência específicas para cada nível mínimo de papel

async def get_current_active_user(user: TokenData = Depends(get_current_user)): # Renomeado param para 'user'
    # Esta função é um alias para get_current_user, mas pode ser expandida para verificar se o usuário está ativo
    # se essa lógica for movida do auth_service para o gateway ou se o token tiver um claim 'is_active'.
    # Por enquanto, get_current_user já garante um token válido.
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user or invalid token")
    return user


async def require_user(current_user: TokenData = Depends(get_current_active_user)):
    return await require_role(UserRoleEnum.USER.value, current_user)

async def require_technical_lead(current_user: TokenData = Depends(get_current_active_user)):
    return await require_role(UserRoleEnum.TECHNICAL_LEAD.value, current_user)

async def require_manager(current_user: TokenData = Depends(get_current_active_user)):
    return await require_role(UserRoleEnum.MANAGER.value, current_user)

async def require_administrator(current_user: TokenData = Depends(get_current_active_user)):
    return await require_role(UserRoleEnum.ADMINISTRATOR.value, current_user)

async def require_super_administrator(current_user: TokenData = Depends(get_current_active_user)):
    return await require_role(UserRoleEnum.SUPER_ADMINISTRATOR.value, current_user)


# require_admin_role antigo agora verifica UserRoleEnum.ADMINISTRATOR ou superior.
async def require_admin_role(current_user: TokenData = Depends(get_current_active_user)):
    """
    Dependência específica para verificar se o usuário é um 'Administrator' ou superior.
    """
    return await require_role(required_role=UserRoleEnum.ADMINISTRATOR.value, current_user=current_user)

# require_user_role antigo agora verifica UserRoleEnum.USER ou superior.
async def require_user_role(current_user: TokenData = Depends(get_current_active_user)):
    """
    Dependência específica para verificar se o usuário tem pelo menos o papel 'User'.
    """
    return await require_role(required_role=UserRoleEnum.USER.value, current_user=current_user)


# Exemplo de como seria uma dependência para superusuário (se 'is_superuser' estivesse no token)
# class TokenDataWithSuperuser(TokenData):
# is_superuser: Optional[bool] = False
#
# async def get_current_active_superuser(current_user: TokenDataWithSuperuser = Depends(get_current_user_com_superuser_flag)):
# if not current_user.is_superuser:
# raise HTTPException(status_code=403, detail="The user doesn't have enough privileges")
# return current_user
