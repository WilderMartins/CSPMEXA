"""update_user_role_to_enum

Revision ID: d001_update_user_role_to_enum
Revises: c04c86a36527
Create Date: 2024-07-26 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Nome do Enum como será criado no PostgreSQL
user_role_enum_name = 'user_role_enum'

# Valores do Enum (de auth_service.app.models.user_model.UserRole)
user_role_values = ('User', 'TechnicalLead', 'Manager', 'Administrator', 'SuperAdministrator')

# revision identifiers, used by Alembic.
revision: str = 'd001_update_user_role_to_enum'
down_revision: Union[str, None] = 'c04c86a36527' # Revisão que criou a tabela 'alerts'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Criar o novo tipo ENUM no PostgreSQL
    sa_user_role_enum = postgresql.ENUM(*user_role_values, name=user_role_enum_name, create_type=True)
    sa_user_role_enum.create(op.get_bind(), checkfirst=True)

    # 2. Alterar a coluna 'role' na tabela 'users' para usar o novo tipo ENUM
    #    e definir o novo valor padrão.
    #    A conversão de dados existentes de string para enum é feita com USING.
    #    O default antigo era 'user' (string). O novo default é UserRole.USER ('User' string).
    op.alter_column(
        'users',
        'role',
        type_is=sa_user_role_enum, # type_is para o novo tipo
        postgresql_using=f"role::text::{user_role_enum_name}", # Cast de string para o novo enum
        nullable=False,
        server_default=user_role_values[0] # 'User'
    )
    # Nota: Se o default antigo fosse diferente do novo (ex: 'user' vs 'User'),
    # seria preciso tratar os valores existentes antes ou durante a alteração da coluna.
    # Neste caso, 'user' para 'User' deve funcionar se o case for o mesmo no DB.
    # Se o default no modelo era 'user' e o enum é 'User', o server_default deve ser 'User'.

def downgrade() -> None:
    # 1. Reverter a coluna 'role' para String e remover o default do enum
    op.alter_column(
        'users',
        'role',
        type_is=sa.String(),
        postgresql_using="role::text", # Cast de enum para string
        nullable=False,
        server_default='user' # Default antigo
    )

    # 2. Remover o tipo ENUM do PostgreSQL
    sa_user_role_enum = postgresql.ENUM(*user_role_values, name=user_role_enum_name, create_type=False)
    sa_user_role_enum.drop(op.get_bind(), checkfirst=True)
