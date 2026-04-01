"""initial agrichain schema

Revision ID: 0001_initial
Revises: 
Create Date: 2026-04-01 18:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=20), primary_key=True),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("village", sa.String(length=100), nullable=True),
        sa.Column("user_type", sa.String(length=20), nullable=False),
        sa.Column("language", sa.String(length=5), nullable=False, server_default="en"),
        sa.Column("market_type", sa.String(length=20), nullable=False, server_default="local"),
        sa.Column("reputation_score", sa.Numeric(3, 2), nullable=False, server_default="4.00"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_users_phone", "users", ["phone"], unique=True)

    op.create_table(
        "wallets",
        sa.Column("id", sa.String(length=20), primary_key=True),
        sa.Column("user_id", sa.String(length=20), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("balance", sa.Numeric(10, 2), nullable=False, server_default="100.00"),
        sa.Column("locked_balance", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="INR"),
        sa.Column("is_frozen", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "listings",
        sa.Column("id", sa.String(length=20), primary_key=True),
        sa.Column("farmer_id", sa.String(length=20), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("crop_name", sa.String(length=100), nullable=False),
        sa.Column("quantity_kg", sa.Numeric(7, 2), nullable=False),
        sa.Column("quantity_remaining", sa.Numeric(7, 2), nullable=True),
        sa.Column("price_per_kg", sa.Numeric(8, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="INR"),
        sa.Column("market_type", sa.String(length=20), nullable=False, server_default="local"),
        sa.Column("pickup_type", sa.String(length=30), nullable=False),
        sa.Column("gi_tag", sa.String(length=100), nullable=True),
        sa.Column("organic_certified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
        sa.Column("qr_code_path", sa.String(length=255), nullable=True),
        sa.Column("blockchain_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_listings_farmer_id", "listings", ["farmer_id"], unique=False)
    op.create_index("ix_listings_crop_name", "listings", ["crop_name"], unique=False)

    op.create_table(
        "orders",
        sa.Column("id", sa.String(length=20), primary_key=True),
        sa.Column("listing_id", sa.String(length=20), sa.ForeignKey("listings.id"), nullable=False),
        sa.Column("buyer_id", sa.String(length=20), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("quantity_kg", sa.Numeric(7, 2), nullable=False),
        sa.Column("total_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("platform_fee", sa.Numeric(8, 2), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("delivery_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_orders_listing_id", "orders", ["listing_id"], unique=False)
    op.create_index("ix_orders_buyer_id", "orders", ["buyer_id"], unique=False)

    op.create_table(
        "transactions",
        sa.Column("id", sa.String(length=20), primary_key=True),
        sa.Column("user_id", sa.String(length=20), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", sa.String(length=30), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("balance_after", sa.Numeric(10, 2), nullable=False),
        sa.Column("reference_id", sa.String(length=50), nullable=True),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("hash"),
    )
    op.create_index("ix_transactions_user_id", "transactions", ["user_id"], unique=False)

    op.create_table(
        "withdrawal_requests",
        sa.Column("id", sa.String(length=20), primary_key=True),
        sa.Column("user_id", sa.String(length=20), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("upi_id", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="processing"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_withdrawal_requests_user_id", "withdrawal_requests", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_withdrawal_requests_user_id", table_name="withdrawal_requests")
    op.drop_table("withdrawal_requests")
    op.drop_index("ix_transactions_user_id", table_name="transactions")
    op.drop_table("transactions")
    op.drop_index("ix_orders_buyer_id", table_name="orders")
    op.drop_index("ix_orders_listing_id", table_name="orders")
    op.drop_table("orders")
    op.drop_index("ix_listings_crop_name", table_name="listings")
    op.drop_index("ix_listings_farmer_id", table_name="listings")
    op.drop_table("listings")
    op.drop_table("wallets")
    op.drop_index("ix_users_phone", table_name="users")
    op.drop_table("users")
