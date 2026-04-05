"""add lookup indexes for list-heavy queries

Revision ID: 0002_lookup_indexes
Revises: 0001_initial
Create Date: 2026-04-01 22:15:00
"""

from __future__ import annotations

from alembic import op


revision = "0002_lookup_indexes"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_listings_status", "listings", ["status"], unique=False)
    op.create_index("ix_listings_market_type", "listings", ["market_type"], unique=False)
    op.create_index("ix_listings_expires_at", "listings", ["expires_at"], unique=False)
    op.create_index("ix_listings_created_at", "listings", ["created_at"], unique=False)
    op.create_index("ix_orders_status", "orders", ["status"], unique=False)
    op.create_index("ix_orders_created_at", "orders", ["created_at"], unique=False)
    op.create_index("ix_transactions_reference_id", "transactions", ["reference_id"], unique=False)
    op.create_index("ix_transactions_created_at", "transactions", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_transactions_created_at", table_name="transactions")
    op.drop_index("ix_transactions_reference_id", table_name="transactions")
    op.drop_index("ix_orders_created_at", table_name="orders")
    op.drop_index("ix_orders_status", table_name="orders")
    op.drop_index("ix_listings_created_at", table_name="listings")
    op.drop_index("ix_listings_expires_at", table_name="listings")
    op.drop_index("ix_listings_market_type", table_name="listings")
    op.drop_index("ix_listings_status", table_name="listings")
