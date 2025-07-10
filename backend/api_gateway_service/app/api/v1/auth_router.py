from fastapi import APIRouter, Request, HTTPException, Depends, status
from fastapi.responses import RedirectResponse, JSONResponse
from app.services.http_client import auth_service_client
# from app.core.config import settings # Removido pois não está sendo usado diretamente aqui
from app.core.security import get_current_user, TokenData  # Importar de security.py

router = APIRouter()

# A dependência oauth2_scheme já está definida em security.py e usada por get_current_user


@router.get("/auth/google/login", name="auth:google-login")
async def google_login_proxy(request: Request):
    """
    Proxies the request to the auth-service to get the Google login URL.
    The auth-service is expected to return a redirect URL.
    """
    # O auth_service deve retornar uma resposta com a URL de redirecionamento do Google
    # ou diretamente um RedirectResponse.
    # Para este exemplo, vamos assumir que o auth_service retorna JSON com a URL.
    try:
        response = await auth_service_client.get(
            "/auth/google/login"
        )  # Endpoint no auth-service

        if (
            response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
            or response.status_code == status.HTTP_302_FOUND
        ):
            return RedirectResponse(url=response.headers["location"])

        response_data = response.json()
        if "redirect_url" not in response_data:
            raise HTTPException(
                status_code=500, detail="Auth service did not return a redirect URL."
            )

        return RedirectResponse(url=response_data["redirect_url"])
    except HTTPException as e:
        # Re-raise HTTPExceptions para que o FastAPI as manipule corretamente
        raise e
    except Exception as e:
        # import logging; logging.exception("Error in google_login_proxy")
        raise HTTPException(
            status_code=500, detail=f"Error proxying Google login: {str(e)}"
        )


@router.get("/auth/google/callback", name="auth:google-callback")
async def google_callback_proxy(request: Request):
    """
    Proxies the Google callback to the auth-service.
    The auth-service handles the code exchange, user creation/login, JWT generation,
    and then should redirect the user to the frontend, possibly with the token.
    This gateway endpoint will receive the same query parameters from Google.
    """
    # Query params from Google (code, state, etc.)
    query_params = request.query_params

    try:
        # Passa os query params para o auth-service
        response = await auth_service_client.get(
            "/auth/google/callback", params=query_params
        )

        # O auth-service deve lidar com a lógica e, idealmente, redirecionar para o frontend.
        # O gateway apenas repassa a resposta do auth-service.
        # Se o auth-service retornar um redirect, o gateway o seguirá.
        if response.status_code in [
            status.HTTP_307_TEMPORARY_REDIRECT,
            status.HTTP_302_FOUND,
            status.HTTP_303_SEE_OTHER,
        ]:
            # Se o auth_service redirecionar para o frontend com o token, o gateway repassa esse redirect.
            return RedirectResponse(
                url=response.headers["location"], status_code=response.status_code
            )

        # Se o auth_service retornar o token diretamente (menos comum para callbacks OAuth)
        # O frontend precisaria buscar esse token de alguma forma.
        # É mais comum o auth_service redirecionar para o frontend com o token.
        # Se o auth_service retornar JSON, o gateway pode repassá-lo.
        # No entanto, o fluxo OAuth padrão espera um redirecionamento aqui.
        try:
            response_json = response.json()
            return JSONResponse(content=response_json, status_code=response.status_code)
        except Exception:  # Se não for JSON
            return response  # Retorna a resposta como está

    except HTTPException as e:
        raise e
    except Exception as e:
        # import logging; logging.exception("Error in google_callback_proxy")
        raise HTTPException(
            status_code=500, detail=f"Error proxying Google callback: {str(e)}"
        )


# Exemplo de endpoint protegido
@router.get("/users/me", response_model=TokenData, name="users:get_current_user")
async def read_users_me(
    request: Request,  # Adicionado para poder repassar headers, se necessário
    current_user: TokenData = Depends(get_current_user),
):
    """
    Retorna informações básicas do usuário logado (obtidas do token JWT).
    Este endpoint é protegido e requer um token JWT válido.
    """
    # Se precisarmos de mais detalhes do usuário que não estão no token,
    # poderíamos chamar o auth-service aqui:
    # try:
    #     # Passar o token original para o auth-service para que ele possa validar/usar
    #     auth_header = request.headers.get("Authorization")
    #     headers = {"Authorization": auth_header} if auth_header else {}
    #     response = await auth_service_client.get(f"/users/me", headers=headers) # Supondo que auth-service tem /users/me
    #     if response.status_code == 200:
    #         return response.json() # Retorna os dados do auth-service
    #     else:
    #         raise HTTPException(status_code=response.status_code, detail="Failed to fetch user details from auth service.")
    # except Exception as e:
    #     raise HTTPException(status_code=500, detail=f"Error fetching user details: {str(e)}")

    # Para o MVP, apenas retornar os dados do token é suficiente.
    return current_user
