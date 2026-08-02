"""Add business_location, contact_phone, onboarding_completed to users

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-08-02 00:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('business_location', sa.String(), nullable=True))
    op.add_column('users', sa.Column('contact_phone', sa.String(), nullable=True))
    op.add_column('users', sa.Column('onboarding_completed', sa.Boolean(), server_default=sa.false(), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'onboarding_completed')
    op.drop_column('users', 'contact_phone')
    op.drop_column('users', 'business_location')
