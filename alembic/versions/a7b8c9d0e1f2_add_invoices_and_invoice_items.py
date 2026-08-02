"""Add invoices and invoice_items tables

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-08-02 02:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, Sequence[str], None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'invoices',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('business_id', UUID(as_uuid=True), nullable=False),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('invoice_number', sa.String(), nullable=False),
        sa.Column('customer_name', sa.String(), nullable=False),
        sa.Column('customer_email', sa.String(), nullable=True),
        sa.Column('customer_phone', sa.String(), nullable=True),
        sa.Column('customer_address', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='draft'),
        sa.Column('template', sa.String(), nullable=False, server_default='clean_minimal'),
        sa.Column('total_amount', sa.Numeric(precision=18, scale=2), nullable=False, server_default='0'),
        sa.Column('currency', sa.String(), nullable=False, server_default='UGX'),
        sa.Column('notes', sa.String(), nullable=True),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_invoices_business_id', 'invoices', ['business_id'])

    op.create_table(
        'invoice_items',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('invoice_id', UUID(as_uuid=True), sa.ForeignKey('invoices.id'), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=18, scale=2), nullable=True, server_default='1'),
        sa.Column('unit_price', sa.Numeric(precision=18, scale=2), nullable=True, server_default='0'),
        sa.Column('total_price', sa.Numeric(precision=18, scale=2), nullable=True, server_default='0'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('invoice_items')
    op.drop_index('ix_invoices_business_id', table_name='invoices')
    op.drop_table('invoices')
