import pyotp
from typing import Optional

# Nome do emissor para a URI OTP. Geralmente o nome da sua aplicação.
ISSUER_NAME = "CSPMEXA" # Pode vir de settings

class MFAService:
    def generate_mfa_secret(self) -> str:
        """
        Gera um novo segredo TOTP em base32.
        """
        return pyotp.random_base32()

    def get_totp_uri(self, email: str, secret: str) -> str:
        """
        Gera a URI otpauth:// para provisionamento em apps autenticadores.
        O 'email' é usado como o label da conta no app autenticador.
        """
        # O nome do emissor (issuer) é importante para organização no app autenticador.
        return pyotp.totp.TOTP(secret).provisioning_uri(
            name=email,
            issuer_name=ISSUER_NAME
        )

    def verify_totp_code(self, secret: str, code: str, window: int = 1) -> bool:
        """
        Verifica um código TOTP contra o segredo do usuário.
        'window' permite uma pequena tolerância para dessincronização de relógio
        (1 significa verificar o código atual, o anterior e o próximo).
        """
        if not secret or not code:
            return False
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=window)

mfa_service = MFAService()
