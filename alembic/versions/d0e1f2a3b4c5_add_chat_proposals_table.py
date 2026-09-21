"""Add chat_proposals table for the PROPOSE/COMMIT chat state machine

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-08-30 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'd0e1f2a3b4c5'
down_revision: Union[str, Sequence[str], None] = 'c9d0e1f2a3b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'chat_proposals',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('business_id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('function_name', sa.String(), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('preview_text', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_chat_proposals_business_id', 'chat_proposals', ['business_id'])
    op.create_index('ix_chat_proposals_user_id', 'chat_proposals', ['user_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_chat_proposals_user_id', table_name='chat_proposals')
    op.drop_index('ix_chat_proposals_business_id', table_name='chat_proposals')
    op.drop_table('chat_proposals')
