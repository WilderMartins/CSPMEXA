from pydantic import BaseModel, constr

class MFASetupResponse(BaseModel):
    mfa_secret: str
    otp_uri: str

class MFAEnableRequest(BaseModel):
    # O usuário submete o segredo que foi gerado e exibido para ele na etapa de setup,
    # junto com o primeiro código TOTP do seu app autenticador, para confirmar que ele
    # configurou corretamente. O backend então armazena este segredo permanentemente para o usuário.
    mfa_secret_from_setup: str
    totp_code: constr(min_length=6, max_length=8) # TOTP pode ter 6-8 dígitos

class MFADisableRequest(BaseModel):
    totp_code: constr(min_length=6, max_length=8)

class MFALoginVerifyRequest(BaseModel):
    # user_id é usado para identificar o usuário que está tentando completar o login com MFA.
    # Este user_id seria obtido de uma etapa anterior (ex: após o login OAuth, antes do JWT final).
    # Alternativamente, um token temporário de "pré-MFA" poderia ser usado.
    user_id: int
    totp_code: constr(min_length=6, max_length=8)

# Se o /mfa/verify-login retornar o token diretamente:
# class MFALoginVerifyResponse(BaseModel):
#     access_token: str
#     token_type: str = "bearer"
