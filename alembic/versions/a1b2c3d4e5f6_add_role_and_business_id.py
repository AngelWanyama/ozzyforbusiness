"""Add role and business_id for workers system

Revision ID: a1b2c3d4e5f6
Revises: bf1917403105
Create Date: 2026-08-01 23:30:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'bf1917403105'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('role', sa.String(), nullable=False, server_default='owner'))
    op.add_column('users', sa.Column('business_id', UUID(as_uuid=True), nullable=True))
    op.add_column('transactions', sa.Column('business_id', UUID(as_uuid=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('transactions', 'business_id')
    op.drop_column('users', 'business_id')
    op.drop_column('users', 'role')
