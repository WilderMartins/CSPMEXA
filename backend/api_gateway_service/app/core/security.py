from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, ValidationError
from typing import Optional
from app.core.config import settings

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
    if not current_user.role or current_user.role.lower() != required_role.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User does not have the required '{required_role}' role.",
        )
    return current_user

async def require_admin_role(current_user: TokenData = Depends(get_current_user)):
    """
    Dependência específica para verificar se o usuário é um 'admin'.
    """
    return await require_role(required_role="admin", current_user=current_user)

async def require_user_role(current_user: TokenData = Depends(get_current_user)):
    """
    Dependência específica para verificar se o usuário é um 'user' (ou qualquer role não-admin,
    se a lógica for apenas admin vs não-admin).
    Para ser mais explícito, pode-se verificar se o role é 'user'.
    Se um admin também puder fazer ações de usuário, essa verificação é mais simples.
    """
    # Se admin pode fazer tudo que user faz, então get_current_user é suficiente.
    # Se for para distinguir estritamente, usar require_role("user", current_user)
    # ou verificar if current_user.role not in ["admin", "outro_role_privilegiado"]
    if not current_user.role: # Garante que o role existe
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User role is not defined.",
        )
    # Esta implementação permite qualquer usuário autenticado que tenha um role.
    # Para restringir a apenas 'user' ou 'admin', use require_role.
    return current_user


# Exemplo de como seria uma dependência para superusuário (se 'is_superuser' estivesse no token)
# class TokenDataWithSuperuser(TokenData):
# is_superuser: Optional[bool] = False
#
# async def get_current_active_superuser(current_user: TokenDataWithSuperuser = Depends(get_current_user_com_superuser_flag)):
# if not current_user.is_superuser:
# raise HTTPException(status_code=403, detail="The user doesn't have enough privileges")
# return current_user
