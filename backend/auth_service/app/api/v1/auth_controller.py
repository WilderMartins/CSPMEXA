from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
from app.core.rate_limiter import limiter # Importar o limiter

from app.services.google_oauth_service import google_oauth_service
from app.services.user_service import user_service
from app.services.token_service import token_service
from app.schemas.token_schema import Token
from app.db.session import get_db
from app.core.config import settings

router = APIRouter()

@router.get("/google/login", name="auth:google-login")
@limiter.limit("5/minute") # Aplicar o rate limit
async def google_login(request: Request):
    """
    Inicia o fluxo de login com Google, redirecionando o usuário para a página de autorização do Google.
    """
    auth_url = google_oauth_service.get_google_auth_url()
    return RedirectResponse(url=auth_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get("/google/callback", name="auth:google-callback")
@limiter.limit("10/minute") # Limite um pouco mais alto para o callback
async def google_callback(
    request: Request,
    code: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Callback do Google OAuth. Troca o código por tokens, obtém informações do usuário,
    cria/autentica o usuário localmente e gera um token JWT interno.
    """
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google OAuth error: {error}. Please try logging in again."
        )

    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing authorization code from Google. Please try logging in again."
        )

    try:
        google_tokens = await google_oauth_service.exchange_code_for_tokens(code)
        access_token = google_tokens.get("access_token")

        if not access_token:
            raise HTTPException(status_code=500, detail="Failed to retrieve access token from Google.")

        user_info = await google_oauth_service.get_google_user_info(access_token)

        google_id = user_info.get("sub")
        email = user_info.get("email")

        if not google_id or not email:
            raise HTTPException(status_code=500, detail="Could not retrieve essential user information from Google.")

        local_user = user_service.get_or_create_user_oauth(
            db,
            google_id=google_id,
            email=email,
            full_name=user_info.get("name"),
            profile_picture_url=user_info.get("picture")
        )

        if not local_user:
            raise HTTPException(status_code=500, detail="Could not get or create local user account.")

        if local_user.is_mfa_enabled:
            frontend_mfa_required_url = f"{settings.FRONTEND_URL_MFA_REQUIRED}?user_id={local_user.id}"
            return RedirectResponse(url=frontend_mfa_required_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
        else:
            jwt_claims = {
                "email": local_user.email,
                "role": local_user.role,
                "full_name": local_user.full_name,
            }
            internal_jwt = token_service.create_jwt_token_with_custom_claims(
                subject=local_user.id,
                claims=jwt_claims
            )
            frontend_callback_url_with_token = f"{settings.FRONTEND_URL_AUTH_CALLBACK}?token={internal_jwt}"
            return RedirectResponse(url=frontend_callback_url_with_token, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    except HTTPException as e:
        raise e
    except Exception as e:
        import logging
        logging.exception("Critical error during Google OAuth callback processing")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during the login process."
        )

# O restante do arquivo (endpoints de MFA) permanece o mesmo
from app.services.mfa_service import mfa_service
from app.schemas.mfa_schema import MFASetupResponse, MFAEnableRequest, MFADisableRequest, MFALoginVerifyRequest
from app.core.security import get_current_active_user

@router.post("/mfa/setup", response_model=MFASetupResponse, name="mfa:setup")
@limiter.limit("5/minute")
async def mfa_setup(
    request: Request,
    current_user: Session = Depends(get_current_active_user)
):
    if current_user.is_mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled for this user."
        )
    new_mfa_secret = mfa_service.generate_mfa_secret()
    otp_uri = mfa_service.get_totp_uri(email=current_user.email, secret=new_mfa_secret)
    return MFASetupResponse(mfa_secret=new_mfa_secret, otp_uri=otp_uri)

@router.post("/mfa/enable", name="mfa:enable")
@limiter.limit("5/minute")
async def mfa_enable(
    request: Request,
    request_data: MFAEnableRequest,
    db: Session = Depends(get_db),
    current_user: Session = Depends(get_current_active_user)
):
    if current_user.is_mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled."
        )
    is_valid_code = mfa_service.verify_totp_code(
        secret=request_data.mfa_secret_from_setup,
        code=request_data.totp_code
    )
    if not is_valid_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid TOTP code or secret. MFA not enabled."
        )
    user_service.enable_mfa(db, user=current_user, mfa_secret=request_data.mfa_secret_from_setup)
    return {"message": "MFA enabled successfully."}

@router.post("/mfa/disable", name="mfa:disable")
@limiter.limit("5/minute")
async def mfa_disable(
    request: Request,
    request_data: MFADisableRequest,
    db: Session = Depends(get_db),
    current_user: Session = Depends(get_current_active_user)
):
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

@router.post("/mfa/verify-login", name="mfa:verify-login", response_model=Token)
@limiter.limit("5/minute")
async def mfa_verify_login(
    request: Request,
    request_data: MFALoginVerifyRequest,
    db: Session = Depends(get_db)
):
    user = user_service.get_user_by_id(db, user_id=request_data.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if not user.is_mfa_enabled or not user.mfa_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="MFA not enabled for this user.")
    is_valid_code = mfa_service.verify_totp_code(secret=user.mfa_secret, code=request_data.totp_code)
    if not is_valid_code:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid TOTP code.")
    jwt_claims = {
        "email": user.email,
        "role": getattr(user, 'role', 'user'),
        "full_name": getattr(user, 'full_name', None),
        "mfa_verified": True
    }
    final_jwt = token_service.create_jwt_token_with_custom_claims(
        subject=user.id,
        claims=jwt_claims
    )
    return Token(access_token=final_jwt, token_type="bearer")
