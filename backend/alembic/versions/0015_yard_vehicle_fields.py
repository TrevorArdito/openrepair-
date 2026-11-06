"""marketplace: yard facts on vehicle listings (stock #, arrived, keys, damage, lien sale)

Revision ID: f3b8d6e7a4c9
Revises: e2a7c5d6f3b8
Create Date: 2026-11-06 13:40:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f3b8d6e7a4c9"
down_revision: str | Sequence[str] | None = "e2a7c5d6f3b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("market_vehicle_details", schema=None) as batch_op:
        batch_op.add_column(sa.Column("stock_number", sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column("arrived_on", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("has_keys", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("damage", sa.String(length=60), nullable=True))
        batch_op.add_column(sa.Column("lien_sale_after", sa.Date(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("market_vehicle_details", schema=None) as batch_op:
        for col in ("lien_sale_after", "damage", "has_keys", "arrived_on", "stock_number"):
            batch_op.drop_column(col)
