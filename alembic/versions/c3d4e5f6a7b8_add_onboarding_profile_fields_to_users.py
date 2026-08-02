"""Add onboarding profile fields to users

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('owner_name', sa.String(), nullable=True))
    op.add_column('users', sa.Column('business_description', sa.String(), nullable=True))
    op.add_column('users', sa.Column('years_in_business', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('email', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'email')
    op.drop_column('users', 'years_in_business')
    op.drop_column('users', 'business_description')
    op.drop_column('users', 'owner_name')
