import httpx
from urllib.parse import urlencode
from fastapi import HTTPException, status
from app.core.config import settings # Para GOOGLE_CLIENT_ID, etc.
from typing import Dict, Optional, Tuple

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


class GoogleOAuthService:
    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI # Do auth-service, não do gateway

    def get_google_auth_url(self, state: Optional[str] = None) -> str:
        """
        Constrói a URL de autorização do Google para iniciar o fluxo OAuth.
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid email profile", # openid é necessário para ID token
            "access_type": "offline",  # Para solicitar refresh_token
            # "prompt": "consent", # Descomentar para forçar o usuário a reconceder permissão
        }
        if state:
            params["state"] = state

        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    async def exchange_code_for_tokens(self, code: str) -> Dict[str, any]:
        """
        Troca o código de autorização por tokens de acesso, ID e refresh do Google.
        """
        payload = {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri, # Deve ser o mesmo usado para obter o código
            "grant_type": "authorization_code",
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(GOOGLE_TOKEN_URL, data=payload)
                response.raise_for_status()  # Levanta exceção para 4xx/5xx
                tokens = response.json()

                # Validar o ID token seria uma boa prática aqui (verificar assinatura, exp, aud, iss)
                # Usando uma biblioteca como google-auth ou jwt para decodificar e validar.
                # Por simplicidade no MVP, vamos pular a validação manual do ID token aqui
                # e confiar que o Google o emitiu corretamente se a chamada foi bem-sucedida.
                # No entanto, em produção, a validação do ID token é crucial.

                if "id_token" not in tokens or "access_token" not in tokens:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="ID token or access token missing from Google response"
                    )
                return tokens
            except httpx.HTTPStatusError as e:
                # Logar e.response.text para mais detalhes do erro do Google
                print(f"Google token exchange error: {e.response.text}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to exchange authorization code with Google: {e.response.text}",
                )
            except Exception as e:
                print(f"Unexpected error during token exchange: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="An unexpected error occurred during token exchange with Google.",
                )

    async def get_google_user_info(self, access_token: str) -> Dict[str, any]:
        """
        Obtém informações do perfil do usuário do Google usando o access token.
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(GOOGLE_USERINFO_URL, headers=headers)
                response.raise_for_status()
                user_info = response.json()

                # O user_info geralmente contém 'sub' (Google ID), 'email', 'name', 'picture', etc.
                if "sub" not in user_info or "email" not in user_info:
                     raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="User ID (sub) or email missing from Google userinfo response"
                    )
                return user_info
            except httpx.HTTPStatusError as e:
                print(f"Google userinfo error: {e.response.text}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to get user info from Google: {e.response.text}",
                )
            except Exception as e:
                print(f"Unexpected error during userinfo fetch: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="An unexpected error occurred while fetching user info from Google.",
                )

google_oauth_service = GoogleOAuthService()
