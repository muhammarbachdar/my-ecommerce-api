"""add_xendit_fields_to_payments

Revision ID: 64a2b6b953a5
Revises: 9d4adbd92591
Create Date: 2026-05-17 11:20:05.497472

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '64a2b6b953a5'
down_revision: Union[str, None] = '9d4adbd92591'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('payments', sa.Column('xendit_invoice_id', sa.String(length=100), nullable=True))
    op.add_column('payments', sa.Column('invoice_url', sa.String(length=500), nullable=True))
    op.create_index(op.f('ix_payments_xendit_invoice_id'), 'payments', ['xendit_invoice_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_payments_xendit_invoice_id'), table_name='payments')
    op.drop_column('payments', 'invoice_url')
    op.drop_column('payments', 'xendit_invoice_id')