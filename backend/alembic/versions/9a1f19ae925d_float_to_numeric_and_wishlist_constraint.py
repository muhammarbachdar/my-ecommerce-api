"""float_to_numeric_and_wishlist_constraint

Revision ID: 9a1f19ae925d
Revises: 64a2b6b953a5
Create Date: 2026-05-19 15:20:48.512494

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9a1f19ae925d'
down_revision: Union[str, None] = '64a2b6b953a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Tabel products: price Float -> Numeric(19,4)
    op.alter_column(
        'products', 'price',
        existing_type=sa.Float(),
        type_=sa.Numeric(19, 4),
        existing_nullable=False,
        postgresql_using='price::numeric'
    )

    # 2. Tabel orders: total_price Float -> Numeric(19,4)
    op.alter_column(
        'orders', 'total_price',
        existing_type=sa.Float(),
        type_=sa.Numeric(19, 4),
        existing_nullable=False,
        postgresql_using='total_price::numeric'
    )

    # 3. Tabel orders: discount_amount Float -> Numeric(19,4)
    op.alter_column(
        'orders', 'discount_amount',
        existing_type=sa.Float(),
        type_=sa.Numeric(19, 4),
        existing_nullable=False,
        postgresql_using='discount_amount::numeric'
    )

    # 4. Tabel orders_items: price_at_purchase Float -> Numeric(19,4)
    op.alter_column(
        'orders_items', 'price_at_purchase',
        existing_type=sa.Float(),
        type_=sa.Numeric(19, 4),
        existing_nullable=False,
        postgresql_using='price_at_purchase::numeric'
    )

    # 5. Tabel payments: amount Float -> Numeric(19,4)
    op.alter_column(
        'payments', 'amount',
        existing_type=sa.Float(),
        type_=sa.Numeric(19, 4),
        existing_nullable=False,
        postgresql_using='amount::numeric'
    )

    # 6. Tabel vouchers: discount_value Float -> Numeric(19,4)
    op.alter_column(
        'vouchers', 'discount_value',
        existing_type=sa.Float(),
        type_=sa.Numeric(19, 4),
        existing_nullable=False,
        postgresql_using='discount_value::numeric'
    )

    # 7. Tabel vouchers: min_purchase Float -> Numeric(19,4)
    op.alter_column(
        'vouchers', 'min_purchase',
        existing_type=sa.Float(),
        type_=sa.Numeric(19, 4),
        existing_nullable=False,
        postgresql_using='min_purchase::numeric'
    )

    # 8. Tabel vouchers: max_discount Float -> Numeric(19,4)
    op.alter_column(
        'vouchers', 'max_discount',
        existing_type=sa.Float(),
        type_=sa.Numeric(19, 4),
        existing_nullable=True,
        postgresql_using='max_discount::numeric'
    )

    # 9. Tabel voucher_usages: discount_amount Float -> Numeric(19,4)
    op.alter_column(
        'voucher_usages', 'discount_amount',
        existing_type=sa.Float(),
        type_=sa.Numeric(19, 4),
        existing_nullable=False,
        postgresql_using='discount_amount::numeric'
    )

    # 10. Tabel wishlists: tambah UniqueConstraint (user_id, product_id)
    op.create_unique_constraint(
        'uq_user_product_wishlist',
        'wishlists',
        ['user_id', 'product_id']
    )

def downgrade() -> None:
    # Hapus unique constraint terlebih dahulu
    op.drop_constraint('uq_user_product_wishlist', 'wishlists', type_='unique')

    # Kembalikan semua kolom Numeric ke Float
    op.alter_column(
        'voucher_usages', 'discount_amount',
        existing_type=sa.Numeric(19, 4),
        type_=sa.Float(),
        existing_nullable=False,
        postgresql_using='discount_amount::float'
    )

    op.alter_column(
        'vouchers', 'max_discount',
        existing_type=sa.Numeric(19, 4),
        type_=sa.Float(),
        existing_nullable=True,
        postgresql_using='max_discount::float'
    )

    op.alter_column(
        'vouchers', 'min_purchase',
        existing_type=sa.Numeric(19, 4),
        type_=sa.Float(),
        existing_nullable=False,
        postgresql_using='min_purchase::float'
    )

    op.alter_column(
        'vouchers', 'discount_value',
        existing_type=sa.Numeric(19, 4),
        type_=sa.Float(),
        existing_nullable=False,
        postgresql_using='discount_value::float'
    )

    op.alter_column(
        'payments', 'amount',
        existing_type=sa.Numeric(19, 4),
        type_=sa.Float(),
        existing_nullable=False,
        postgresql_using='amount::float'
    )

    op.alter_column(
        'orders_items', 'price_at_purchase',
        existing_type=sa.Numeric(19, 4),
        type_=sa.Float(),
        existing_nullable=False,
        postgresql_using='price_at_purchase::float'
    )

    op.alter_column(
        'orders', 'discount_amount',
        existing_type=sa.Numeric(19, 4),
        type_=sa.Float(),
        existing_nullable=False,
        postgresql_using='discount_amount::float'
    )

    op.alter_column(
        'orders', 'total_price',
        existing_type=sa.Numeric(19, 4),
        type_=sa.Float(),
        existing_nullable=False,
        postgresql_using='total_price::float'
    )

    op.alter_column(
        'products', 'price',
        existing_type=sa.Numeric(19, 4),
        type_=sa.Float(),
        existing_nullable=False,
        postgresql_using='price::float'
    )