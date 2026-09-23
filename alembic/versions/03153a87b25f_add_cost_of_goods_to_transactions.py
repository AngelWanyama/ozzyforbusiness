"""Add cost_of_goods/cost_of_goods_complete to transactions, so profit can subtract COGS

Revision ID: 03153a87b25f
Revises: b7c8d9e0f1a2
Create Date: 2026-09-23 22:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '03153a87b25f'
down_revision: Union[str, Sequence[str], None] = 'b7c8d9e0f1a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('transactions', sa.Column('cost_of_goods', sa.Numeric(precision=18, scale=2), nullable=True))
    op.add_column('transactions', sa.Column('cost_of_goods_complete', sa.Boolean(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('transactions', 'cost_of_goods_complete')
    op.drop_column('transactions', 'cost_of_goods')
