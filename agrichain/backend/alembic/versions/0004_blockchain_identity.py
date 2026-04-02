"""add blockchain wallet identity and mined block metadata

Revision ID: 0004_blockchain_identity
Revises: 0003_order_dispatch
Create Date: 2026-04-02 14:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0004_blockchain_identity"
down_revision = "0003_order_dispatch"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("wallet_address", sa.String(length=48), nullable=True))
    op.add_column("users", sa.Column("wallet_public_key", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("wallet_private_key_encrypted", sa.Text(), nullable=True))
    op.create_index("ix_users_wallet_address", "users", ["wallet_address"], unique=True)

    op.add_column("transactions", sa.Column("transaction_hash", sa.String(length=255), nullable=True))
    op.add_column("transactions", sa.Column("previous_hash", sa.String(length=255), nullable=True))
    op.add_column("transactions", sa.Column("merkle_root", sa.String(length=255), nullable=True))
    op.add_column("transactions", sa.Column("signature", sa.Text(), nullable=True))
    op.add_column("transactions", sa.Column("signer_public_key", sa.Text(), nullable=True))
    op.add_column("transactions", sa.Column("signer_address", sa.String(length=48), nullable=True))
    op.add_column("transactions", sa.Column("block_height", sa.Integer(), nullable=True))
    op.add_column("transactions", sa.Column("difficulty", sa.Integer(), nullable=True))
    op.add_column("transactions", sa.Column("nonce", sa.Integer(), nullable=True))
    op.add_column("transactions", sa.Column("hash_rate_hps", sa.Float(), nullable=True))
    op.add_column("transactions", sa.Column("hash_attempts", sa.Integer(), nullable=True))
    op.add_column("transactions", sa.Column("mining_duration_ms", sa.Integer(), nullable=True))
    op.create_index("ix_transactions_transaction_hash", "transactions", ["transaction_hash"], unique=True)
    op.create_index("ix_transactions_block_height", "transactions", ["block_height"], unique=True)
    op.create_index("ix_transactions_signer_address", "transactions", ["signer_address"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_transactions_signer_address", table_name="transactions")
    op.drop_index("ix_transactions_block_height", table_name="transactions")
    op.drop_index("ix_transactions_transaction_hash", table_name="transactions")
    op.drop_column("transactions", "mining_duration_ms")
    op.drop_column("transactions", "hash_attempts")
    op.drop_column("transactions", "hash_rate_hps")
    op.drop_column("transactions", "nonce")
    op.drop_column("transactions", "difficulty")
    op.drop_column("transactions", "block_height")
    op.drop_column("transactions", "signer_address")
    op.drop_column("transactions", "signer_public_key")
    op.drop_column("transactions", "signature")
    op.drop_column("transactions", "merkle_root")
    op.drop_column("transactions", "previous_hash")
    op.drop_column("transactions", "transaction_hash")

    op.drop_index("ix_users_wallet_address", table_name="users")
    op.drop_column("users", "wallet_private_key_encrypted")
    op.drop_column("users", "wallet_public_key")
    op.drop_column("users", "wallet_address")
