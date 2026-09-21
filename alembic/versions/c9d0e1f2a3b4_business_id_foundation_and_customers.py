"""Migrate items/payments/summaries to business_id, require it on transactions, add customers table

Revision ID: c9d0e1f2a3b4
Revises: a7b8c9d0e1f2
Create Date: 2026-08-30 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'c9d0e1f2a3b4'
down_revision: Union[str, Sequence[str], None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Add business_id as nullable first so existing rows don't break the add
    op.add_column('items', sa.Column('business_id', UUID(as_uuid=True), nullable=True))
    op.add_column('payments', sa.Column('business_id', UUID(as_uuid=True), nullable=True))
    op.add_column('summaries', sa.Column('business_id', UUID(as_uuid=True), nullable=True))

    # 2. Backfill every existing row's business_id from its owning user's business_id
    conn = op.get_bind()
    conn.execute(sa.text(
        "UPDATE items SET business_id = "
        "(SELECT business_id FROM users WHERE users.id = items.user_id) "
        "WHERE business_id IS NULL"
    ))
    conn.execute(sa.text(
        "UPDATE payments SET business_id = "
        "(SELECT business_id FROM users WHERE users.id = payments.user_id) "
        "WHERE business_id IS NULL"
    ))
    conn.execute(sa.text(
        "UPDATE summaries SET business_id = "
        "(SELECT business_id FROM users WHERE users.id = summaries.user_id) "
        "WHERE business_id IS NULL"
    ))

    # 3. Now that every row has a value, make business_id required.
    # batch mode is needed for SQLite (no native ALTER COLUMN); it's a
    # no-op wrapper around a plain ALTER on Postgres.
    with op.batch_alter_table('items') as batch_op:
        batch_op.alter_column('business_id', existing_type=UUID(as_uuid=True), nullable=False)
    with op.batch_alter_table('payments') as batch_op:
        batch_op.alter_column('business_id', existing_type=UUID(as_uuid=True), nullable=False)
    with op.batch_alter_table('summaries') as batch_op:
        batch_op.alter_column('business_id', existing_type=UUID(as_uuid=True), nullable=False)

    # transactions.business_id was added (nullable) and backfilled back in the
    # Workers Stage A migration/backfill script. Every row already has a value
    # — this just closes the column off to future nulls.
    with op.batch_alter_table('transactions') as batch_op:
        batch_op.alter_column('business_id', existing_type=UUID(as_uuid=True), nullable=False)

    # 4. Index business_id on the three tables that just got it, matching the
    # pattern already used on invoices/invites.
    op.create_index('ix_items_business_id', 'items', ['business_id'])
    op.create_index('ix_payments_business_id', 'payments', ['business_id'])
    op.create_index('ix_summaries_business_id', 'summaries', ['business_id'])

    # 5. New customers table (Volume 8 of the Brain doc)
    op.create_table(
        'customers',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('business_id', UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('outstanding_balance', sa.Numeric(precision=18, scale=2), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_customers_business_id', 'customers', ['business_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_customers_business_id', table_name='customers')
    op.drop_table('customers')

    op.drop_index('ix_summaries_business_id', table_name='summaries')
    op.drop_index('ix_payments_business_id', table_name='payments')
    op.drop_index('ix_items_business_id', table_name='items')

    with op.batch_alter_table('transactions') as batch_op:
        batch_op.alter_column('business_id', existing_type=UUID(as_uuid=True), nullable=True)

    with op.batch_alter_table('summaries') as batch_op:
        batch_op.alter_column('business_id', existing_type=UUID(as_uuid=True), nullable=True)
    with op.batch_alter_table('payments') as batch_op:
        batch_op.alter_column('business_id', existing_type=UUID(as_uuid=True), nullable=True)
    with op.batch_alter_table('items') as batch_op:
        batch_op.alter_column('business_id', existing_type=UUID(as_uuid=True), nullable=True)

    op.drop_column('summaries', 'business_id')
    op.drop_column('payments', 'business_id')
    op.drop_column('items', 'business_id')
