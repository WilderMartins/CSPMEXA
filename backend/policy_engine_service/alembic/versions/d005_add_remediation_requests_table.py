"""Add remediation_requests table

Revision ID: d005
Revises: d004
Create Date: 2025-07-17 04:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd005'
down_revision = 'd004'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('remediation_requests',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('alert_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'APPROVED', 'REJECTED', 'EXECUTING', 'COMPLETED', 'FAILED', name='remediationstatusenum'), nullable=False),
    sa.Column('requested_by_user_id', sa.Integer(), nullable=False),
    sa.Column('approved_by_user_id', sa.Integer(), nullable=True),
    sa.Column('requested_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['alert_id'], ['alerts.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_remediation_requests_id'), 'remediation_requests', ['id'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_remediation_requests_id'), table_name='remediation_requests')
    op.drop_table('remediation_requests')
    # ### end Alembic commands ###
