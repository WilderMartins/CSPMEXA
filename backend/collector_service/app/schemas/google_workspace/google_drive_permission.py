from pydantic import BaseModel, Field, EmailStr
from typing import Optional

class DrivePermission(BaseModel):
    id: str # ID da permissão
    type: str  # user, group, domain, anyone
    role: str  # owner, organizer, fileOrganizer, writer, commenter, reader
    email_address: Optional[EmailStr] = Field(None, alias="emailAddress")
    domain: Optional[str] = None
    allow_file_discovery: Optional[bool] = Field(None, alias="allowFileDiscovery") # Para type='anyone'
    deleted: Optional[bool] = None # Se a permissão foi explicitamente deletada
    display_name: Optional[str] = Field(None, alias="displayName")
    # Adicionar 'kind' se for útil para distinguir de outros objetos permission
    # kind: str = Field("drive#permission", alias="kind")

    class Config:
        populate_by_name = True
        extra = 'ignore'
        frozen = True # Tornar imutável para uso em sets se necessário, mas pode não ser necessário.
                      # Removido frozen=True pois Pydantic v1 não tem. Se for v2, pode ser útil.
                      # Para Pydantic V1, a imutabilidade é controlada pela classe Config.
                      # allow_mutation = False (Pydantic V1)
                      # frozen = True (Pydantic V2)
        # Para Pydantic V1, se precisar de imutabilidade (ex: para usar em sets):
        # class Config:
        #     allow_mutation = False
        # Mas para simples transferência de dados, mutabilidade é ok.
        # O principal é `populate_by_name` e `extra = 'ignore'`.

# Exemplo de como o `fields` pode ser usado para obter apenas o necessário:
# GET https://www.googleapis.com/drive/v3/files/{fileId}/permissions?fields=permissions(id,type,role,emailAddress,domain,allowFileDiscovery,deleted,displayName)
# Isso ajuda a reduzir o tamanho da resposta da API.
# O coletor deve usar o parâmetro `fields` nas chamadas da API do Google.
