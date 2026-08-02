"""Add logo_url, notifications_enabled, receipt_template to users

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-02 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('logo_url', sa.String(), nullable=True))
    op.add_column('users', sa.Column('notifications_enabled', sa.Boolean(), server_default=sa.true(), nullable=False))
    op.add_column('users', sa.Column('receipt_template', sa.String(), server_default='clean_minimal', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'receipt_template')
    op.drop_column('users', 'notifications_enabled')
    op.drop_column('users', 'logo_url')
