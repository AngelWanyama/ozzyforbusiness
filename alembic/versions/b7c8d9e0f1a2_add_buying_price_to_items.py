"""Add buying_price column to items, so profit can be calculated for products added mid-sale

Revision ID: b7c8d9e0f1a2
Revises: e1f2a3b4c5d6
Create Date: 2026-09-23 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c8d9e0f1a2'
down_revision: Union[str, Sequence[str], None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('items', sa.Column('buying_price', sa.Numeric(precision=18, scale=2), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('items', 'buying_price')
