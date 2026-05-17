"""add indexes for performance

Revision ID: 9d4adbd92591
Revises: a19905dbb08d
Create Date: 2026-05-16 17:22:51.873830

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9d4adbd92591'
down_revision: Union[str, None] = 'a19905dbb08d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Index untuk orders
    op.create_index('ix_orders_status', 'orders', ['status'])
    op.create_index('ix_orders_user_id', 'orders', ['user_id'])
    op.create_index('ix_orders_user_id_status', 'orders', ['user_id', 'status'])

    # Index untuk products
    op.create_index('ix_products_category_id', 'products', ['category_id'])
    op.create_index('ix_products_is_active', 'products', ['is_active'])

    # Index untuk carts
    op.create_index('ix_carts_user_id', 'carts', ['user_id'])

    # Index untuk soft delete columns
    op.create_index('ix_orders_is_deleted', 'orders', ['is_deleted'])
    op.create_index('ix_addresses_is_deleted', 'addresses', ['is_deleted'])


def downgrade() -> None:
    op.drop_index('ix_addresses_is_deleted', table_name='addresses')
    op.drop_index('ix_orders_is_deleted', table_name='orders')
    op.drop_index('ix_carts_user_id', table_name='carts')
    op.drop_index('ix_products_is_active', table_name='products')
    op.drop_index('ix_products_category_id', table_name='products')
    op.drop_index('ix_orders_user_id_status', table_name='orders')
    op.drop_index('ix_orders_user_id', table_name='orders')
    op.drop_index('ix_orders_status', table_name='orders')