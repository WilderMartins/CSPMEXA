from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from app.core.config import settings
from app.schemas.token_schema import Token # Para o tipo de retorno, se necessário

class TokenService:
    def __init__(self):
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES

    def create_access_token(
        self,
        subject: Any, # O 'sub' claim, geralmente user_id ou email
        expires_delta: Optional[timedelta] = None
    ) -> str:
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)

        to_encode = {"exp": expire, "sub": str(subject)} # subject deve ser string
        # Adicionar outros claims se necessário, ex: email, roles
        # Ex: to_encode.update({"email": email_do_usuario, "roles": ["user"]})

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def create_jwt_token_with_custom_claims(
        self,
        subject: Any,
        claims: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)

        to_encode = {"exp": expire, "sub": str(subject)}
        to_encode.update(claims) # Adiciona claims customizados

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def verify_token(self, token: str) -> Optional[dict]: # Ou um schema Pydantic para o payload
        """
        Verifica um token JWT. Retorna o payload se válido, None caso contrário.
        Levanta exceções específicas se necessário.
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError: # Captura qualquer erro da lib jose (expirado, inválido, etc)
            # Logar o erro aqui seria bom
            return None

token_service = TokenService()
