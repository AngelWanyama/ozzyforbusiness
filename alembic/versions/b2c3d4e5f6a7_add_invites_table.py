"""Add invites table for workers system

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-01 23:45:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'invites',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(length=6), nullable=False),
        sa.Column('business_id', UUID(as_uuid=True), nullable=False),
        sa.Column('created_by', UUID(as_uuid=True), nullable=False),
        sa.Column('phone_number', sa.String(), nullable=True),
        sa.Column('used', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_invites_code', 'invites', ['code'])
    op.create_index('ix_invites_business_id', 'invites', ['business_id'])


def downgrade() -> None:
    op.drop_index('ix_invites_business_id', table_name='invites')
    op.drop_index('ix_invites_code', table_name='invites')
    op.drop_table('invites')
