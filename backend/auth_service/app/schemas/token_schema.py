from pydantic import BaseModel
from typing import Optional


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: Optional[int] = None  # Alterado de username para user_id


class MFALoginSchema(BaseModel):
    user_id: int  # Ou email, dependendo do fluxo pós-OAuth
    totp_code: str
