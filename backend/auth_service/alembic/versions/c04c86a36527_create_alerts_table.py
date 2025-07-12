"""create_alerts_table from policy_engine_service model

Revision ID: c04c86a36527
Revises: a003_add_profile_fields
Create Date: 2025-07-10 19:25:31.822821

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Nomes dos Enums como serão criados no PostgreSQL
alert_severity_enum_name = 'alert_severity_enum'
alert_status_enum_name = 'alert_status_enum'

# Valores dos Enums (de policy_engine_service.app.models.alert_model)
alert_severity_values = ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFORMATIONAL')
alert_status_values = ('OPEN', 'ACKNOWLEDGED', 'RESOLVED', 'IGNORED')

# revision identifiers, used by Alembic.
revision: str = 'c04c86a36527'
down_revision: Union[str, None] = 'a003_add_profile_fields' #  Última migração do auth_service antes desta.
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Criar os tipos ENUM no PostgreSQL
    sa_alert_severity_enum = postgresql.ENUM(*alert_severity_values, name=alert_severity_enum_name, create_type=True)
    sa_alert_severity_enum.create(op.get_bind(), checkfirst=True)

    sa_alert_status_enum = postgresql.ENUM(*alert_status_values, name=alert_status_enum_name, create_type=True)
    sa_alert_status_enum.create(op.get_bind(), checkfirst=True)

    # Criar a tabela 'alerts'
    op.create_table('alerts',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True, index=True),
        sa.Column('resource_id', sa.String(), nullable=False, index=True),
        sa.Column('resource_type', sa.String(), nullable=False, index=True),
        sa.Column('account_id', sa.String(), nullable=True, index=True),
        sa.Column('region', sa.String(), nullable=True, index=True),
        sa.Column('provider', sa.String(), nullable=False, index=True),
        sa.Column('severity', sa_alert_severity_enum, nullable=False, index=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('policy_id', sa.String(), nullable=False, index=True),
        sa.Column('status', sa_alert_status_enum, nullable=False, default='OPEN', index=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('recommendation', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    )


def downgrade() -> None:
    # Remover a tabela 'alerts'
    op.drop_table('alerts')

    # Remover os tipos ENUM
    sa_alert_severity_enum = postgresql.ENUM(*alert_severity_values, name=alert_severity_enum_name, create_type=False)
    sa_alert_severity_enum.drop(op.get_bind(), checkfirst=True)

    sa_alert_status_enum = postgresql.ENUM(*alert_status_values, name=alert_status_enum_name, create_type=False)
    sa_alert_status_enum.drop(op.get_bind(), checkfirst=True)
