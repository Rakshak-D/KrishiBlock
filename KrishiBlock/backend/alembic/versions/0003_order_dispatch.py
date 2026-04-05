"""add dispatched_at to orders

Revision ID: 0003_order_dispatch
Revises: 0002_lookup_indexes
Create Date: 2026-04-02 10:15:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003_order_dispatch"
down_revision = "0002_lookup_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "dispatched_at")
