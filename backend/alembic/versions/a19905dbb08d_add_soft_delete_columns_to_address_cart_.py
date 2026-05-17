"""add soft delete columns to address cart wishlist order payment

Revision ID: a19905dbb08d
Revises: 6c9a9cabb9b1
Create Date: 2026-05-16 14:26:29.699353

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a19905dbb08d'
down_revision: Union[str, None] = '6c9a9cabb9b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Soft delete columns untuk semua tabel
    op.add_column('addresses', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('addresses', sa.Column('deleted_at', sa.DateTime(), nullable=True))

    op.add_column('carts', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('carts', sa.Column('deleted_at', sa.DateTime(), nullable=True))

    op.add_column('wishlists', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('wishlists', sa.Column('deleted_at', sa.DateTime(), nullable=True))

    op.add_column('orders', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('orders', sa.Column('deleted_at', sa.DateTime(), nullable=True))

    op.add_column('payments', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('payments', sa.Column('deleted_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('payments', 'deleted_at')
    op.drop_column('payments', 'is_deleted')
    op.drop_column('orders', 'deleted_at')
    op.drop_column('orders', 'is_deleted')
    op.drop_column('wishlists', 'deleted_at')
    op.drop_column('wishlists', 'is_deleted')
    op.drop_column('carts', 'deleted_at')
    op.drop_column('carts', 'is_deleted')
    op.drop_column('addresses', 'deleted_at')
    op.drop_column('addresses', 'is_deleted')