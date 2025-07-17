from pydantic import BaseModel
from typing import Dict, Any

class CredentialsPayload(BaseModel):
    credentials: Dict[str, Any]
