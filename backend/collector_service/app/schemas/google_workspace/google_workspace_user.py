from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime

# Schemas para Google Workspace Users

class GoogleWorkspaceUserInput(BaseModel): # Para entrada, se necessário, mas o foco é na saída do coletor
    primary_email: EmailStr = Field(..., alias="primaryEmail")
    # Adicionar outros campos se o coletor aceitar input para criar/atualizar usuários

class GoogleWorkspaceUserEmail(BaseModel):
    address: Optional[EmailStr] = None
    primary: Optional[bool] = None
    class Config:
        extra = 'ignore' # Ignorar campos extras da API

class GoogleWorkspaceUserName(BaseModel):
    given_name: Optional[str] = Field(None, alias="givenName")
    family_name: Optional[str] = Field(None, alias="familyName")
    full_name: Optional[str] = Field(None, alias="fullName")
    class Config:
        populate_by_name = True
        extra = 'ignore'

class GoogleWorkspaceUserData(BaseModel):
    id: str # ID do usuário no Google
    primary_email: EmailStr = Field(..., alias="primaryEmail")
    name: GoogleWorkspaceUserName
    is_admin: bool = Field(False, alias="isAdmin")
    is_delegated_admin: Optional[bool] = Field(None, alias="isDelegatedAdmin")
    last_login_time: Optional[datetime] = Field(None, alias="lastLoginTime")
    creation_time: Optional[datetime] = Field(None, alias="creationTime")
    suspended: Optional[bool] = False
    archived: Optional[bool] = False
    org_unit_path: Optional[str] = Field(None, alias="orgUnitPath")
    is_enrolled_in_2sv: bool = Field(False, alias="isEnrolledIn2Sv") # 2-Step Verification
    emails: Optional[List[GoogleWorkspaceUserEmail]] = None # Lista de todos os emails do usuário

    # Campos para informações adicionais que podem ser úteis para políticas
    # groups: Optional[List[Dict[str, str]]] = None # Grupos a que o usuário pertence
    # roles: Optional[List[Dict[str, str]]] = None # Papéis administrativos do usuário

    error_details: Optional[str] = None # Para registrar erros durante a coleta deste usuário

    class Config:
        populate_by_name = True # Permite usar 'primaryEmail' do JSON para popular 'primary_email'
        extra = 'ignore' # Ignorar campos extras que a API do Google possa retornar

class GoogleWorkspaceUserCollection(BaseModel):
    users: List[GoogleWorkspaceUserData] = Field(default_factory=list)
    next_page_token: Optional[str] = Field(None, alias="nextPageToken")
    error_message: Optional[str] = None # Para erros globais na coleta de usuários

    class Config:
        populate_by_name = True
        extra = 'ignore'
