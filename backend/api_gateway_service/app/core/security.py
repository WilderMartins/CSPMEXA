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
    user_id: Optional[int] = (
        None  # Ou str, dependendo do que o auth-service coloca no 'sub'
    )
    # Adicionar outros campos do token que possam ser úteis (ex: email, roles)


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

        token_data = TokenData(
            user_id=int(user_id_from_token)
        )  # Assumindo que user_id é int
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


# Opcional: uma dependência para superusuários, se o token tiver essa informação
# async def get_current_active_superuser(current_user: TokenData = Depends(get_current_user)):
#     # Esta função dependeria do auth-service ter incluído um campo 'is_superuser' no token
#     # ou o gateway teria que chamar o auth-service para verificar.
#     # Para o MVP, vamos manter simples.
#     # if not current_user.is_superuser: # Supondo que TokenData tenha is_superuser
#     #     raise HTTPException(status_code=403, detail="The user doesn't have enough privileges")
#     return current_user
