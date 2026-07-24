"""add missing last_transaction_at column

Revision ID: db933141236a
Revises: 99d1b9fa577f
Create Date: 2026-07-24 16:30:23.548652

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'db933141236a'
down_revision: Union[str, Sequence[str], None] = '99d1b9fa577f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('last_transaction_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'last_transaction_at')