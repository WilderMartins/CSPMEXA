from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.services.google_oauth_service import google_oauth_service
from app.services.user_service import user_service
from app.services.token_service import token_service
from app.schemas.token_schema import Token # Se precisarmos tipar o retorno do token
from app.db.session import get_db
from app.core.config import settings

router = APIRouter()

@router.get("/auth/google/login", name="auth:google-login")
async def google_login(request: Request): # Adicionado request para potencial uso de session state
    """
    Inicia o fluxo de login com Google, redirecionando o usuário para a página de autorização do Google.
    """
    # Opcional: gerar e armazenar um 'state' para proteção CSRF
    # state_value = "random_state_string_generated_here"
    # request.session["oauth_state"] = state_value # Se usar sessions (requer middleware de session)
    # auth_url = google_oauth_service.get_google_auth_url(state=state_value)
    auth_url = google_oauth_service.get_google_auth_url()
    return RedirectResponse(url=auth_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get("/auth/google/callback", name="auth:google-callback")
async def google_callback(
    request: Request,
    code: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    db: Session = Depends(get_db) # Injetar sessão do DB
):
    """
    Callback do Google OAuth. Troca o código por tokens, obtém informações do usuário,
    Próximos passos: criar/autenticar o usuário localmente e gerar um token JWT interno.
    """
    # Opcional: Validar o 'state' recebido com o armazenado na sessão
    # stored_state = request.session.pop("oauth_state", None)
    # if not state or state != stored_state:
    #     # Log de segurança: tentativa de login com state inválido
    #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state parameter.")

    if error:
        # Log: Erro retornado pelo Google
        # Idealmente, redirecionar para uma página de erro no frontend com detalhes amigáveis
        # frontend_error_url = f"{settings.FRONTEND_BASE_URL}/login?error={error}" # Assumindo FRONTEND_BASE_URL em settings
        # return RedirectResponse(url=frontend_error_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google OAuth error: {error}. Please try logging in again."
        )

    if not code:
        # Log: Código não recebido
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing authorization code from Google. Please try logging in again."
        )

    try:
        google_tokens = await google_oauth_service.exchange_code_for_tokens(code)
        access_token = google_tokens.get("access_token")

        if not access_token:
            # Log: Access token não encontrado nos tokens do Google
            raise HTTPException(status_code=500, detail="Failed to retrieve access token from Google.")

        user_info = await google_oauth_service.get_google_user_info(access_token)

        google_id = user_info.get("sub")
        email = user_info.get("email")
        # name = user_info.get("name")
        # picture = user_info.get("picture")

        if not google_id or not email:
            # Log: Informações essenciais não encontradas no user_info
            raise HTTPException(status_code=500, detail="Could not retrieve essential user information (Google ID or email) from Google.")

        # ---- Próximos passos (a serem implementados na próxima etapa do plano) ----
        # 1. Obter/Criar usuário local
        local_user = user_service.get_or_create_user_oauth(
            db,
            google_id=google_id,
            email=email
            # Passar name, picture se quiser armazená-los:
            # name=user_info.get("name"),
            # picture=user_info.get("picture")
        )

        if not local_user:
            # Log: Falha ao criar ou obter usuário local
            raise HTTPException(status_code=500, detail="Could not get or create local user account.")

        # 2. Gerar token JWT interno
        # Adicionar claims relevantes ao token. Para RBAC, o 'role' do usuário seria importante.
        # Por enquanto, vamos adicionar email e google_id para referência.
        jwt_claims = {
            "email": local_user.email,
            "google_id": local_user.google_id, # Pode ser útil para o frontend/outros serviços
            "role": local_user.role # O campo 'role' agora tem default no modelo
        }
        internal_jwt = token_service.create_jwt_token_with_custom_claims(
            subject=local_user.id, # 'sub' claim é o ID do nosso usuário local
            claims=jwt_claims
        )

        # 3. Redirecionar para o frontend com o token JWT
        # A URL do frontend para o callback deve ser configurável.
        # O frontend espera o token como um query parameter.

        # Verificar se MFA está habilitado para este usuário
        if local_user.is_mfa_enabled:
            # Redirecionar para a página de entrada de MFA do frontend, passando user_id
            # O frontend usará este user_id para chamar /mfa/verify-login
            frontend_mfa_required_url = f"{settings.FRONTEND_URL_MFA_REQUIRED}?user_id={local_user.id}"
            return RedirectResponse(url=frontend_mfa_required_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
        else:
            # MFA não habilitado, proceder com o redirecionamento normal com token JWT
            frontend_callback_url_with_token = f"{settings.FRONTEND_URL_AUTH_CALLBACK}?token={internal_jwt}"
            return RedirectResponse(url=frontend_callback_url_with_token, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
        # ---- Fim dos próximos passos ----

    except HTTPException as e:
        # Re-lançar HTTPExceptions para que o FastAPI as manipule corretamente
        # Adicionar logging aqui seria bom
        raise e
    except Exception as e:
        import logging
        logging.exception("Critical error during Google OAuth callback processing")
        # Mensagem genérica para o usuário
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during the login process. Please try again later."
        )

from app.services.mfa_service import mfa_service
from app.schemas.mfa_schema import MFASetupResponse, MFAEnableRequest, MFADisableRequest, MFALoginVerifyRequest
from app.core.security import get_current_active_user # Para proteger endpoints
from app.models.user_model import User # Para type hint

# --- Endpoints MFA ---

@router.post("/mfa/setup", response_model=MFASetupResponse, name="mfa:setup")
async def mfa_setup(
    current_user: User = Depends(get_current_active_user)
):
    """
    Inicia o processo de configuração do MFA para o usuário logado.
    Gera um novo segredo MFA e a URI para o QR code.
    O frontend deve exibir o QR code e instruir o usuário a guardar o segredo.
    O segredo NÃO é salvo no DB nesta etapa. Ele é verificado e salvo no /enable.
    """
    if current_user.is_mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled for this user."
        )

    # Gerar um novo segredo. Este segredo será verificado e salvo no passo /enable.
    # Não o armazenamos no usuário ainda.
    new_mfa_secret = mfa_service.generate_mfa_secret()
    otp_uri = mfa_service.get_totp_uri(email=current_user.email, secret=new_mfa_secret)

    # O frontend precisará do new_mfa_secret para enviá-lo de volta no /mfa/enable
    # junto com o primeiro código TOTP para verificação.
    return MFASetupResponse(mfa_secret=new_mfa_secret, otp_uri=otp_uri)

@router.post("/mfa/enable", name="mfa:enable")
async def mfa_enable(
    request_data: MFAEnableRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Habilita o MFA para o usuário logado após verificar o primeiro código TOTP.
    O usuário deve submeter o segredo que foi exibido no /setup e o código TOTP atual.
    """
    if current_user.is_mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled."
        )

    # Verificar se o código TOTP é válido para o segredo fornecido (que deve ser o mesmo do /setup)
    is_valid_code = mfa_service.verify_totp_code(
        secret=request_data.mfa_secret_from_setup,
        code=request_data.totp_code
    )

    if not is_valid_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid TOTP code or secret. MFA not enabled."
        )

    # Se o código for válido, salvar o segredo no usuário e marcar MFA como habilitado
    user_service.enable_mfa(db, user=current_user, mfa_secret=request_data.mfa_secret_from_setup)
    return {"message": "MFA enabled successfully."}


@router.post("/mfa/disable", name="mfa:disable")
async def mfa_disable(
    request_data: MFADisableRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Desabilita o MFA para o usuário logado após verificar um código TOTP.
    """
    if not current_user.is_mfa_enabled or not current_user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled for this user."
        )

    is_valid_code = mfa_service.verify_totp_code(
        secret=current_user.mfa_secret,
        code=request_data.totp_code
    )

    if not is_valid_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid TOTP code. MFA not disabled."
        )

    user_service.disable_mfa(db, user=current_user)
    return {"message": "MFA disabled successfully."}


@router.post("/mfa/verify-login", name="mfa:verify-login") # , response_model=Token) # Se retornar token
async def mfa_verify_login(
    request_data: MFALoginVerifyRequest,
    db: Session = Depends(get_db)
):
    """
    Verifica o código TOTP durante um fluxo de login de dois fatores.
    Se bem-sucedido, gera e retorna o token JWT final.
    """
    user = db.query(User).filter(User.id == request_data.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if not user.is_mfa_enabled or not user.mfa_secret:
        # Este endpoint só deve ser chamado se MFA estiver habilitado.
        # Se chamado incorretamente, pode ser um erro de fluxo ou tentativa de bypass.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="MFA not enabled for this user.")

    is_valid_code = mfa_service.verify_totp_code(secret=user.mfa_secret, code=request_data.totp_code)

    if not is_valid_code:
        # Log: Falha na verificação do TOTP no login
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid TOTP code.")

    # Se o código TOTP for válido, gerar o token JWT final para o usuário
    jwt_claims = {
        "email": user.email,
        "google_id": user.google_id, # Se aplicável e desejado no token
        "role": getattr(user, 'role', 'user'),
        "mfa_verified": True # Adicionar um claim para indicar que MFA foi verificado
    }
    final_jwt = token_service.create_jwt_token_with_custom_claims(
        subject=user.id,
        claims=jwt_claims
    )

    # Retorna o token para o frontend, que completará o login.
    return Token(access_token=final_jwt, token_type="bearer")
