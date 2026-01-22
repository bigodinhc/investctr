"""Add realized_trades table

Revision ID: 008_add_realized_trades_table
Revises: 007_add_exchange_rates_table
Create Date: 2026-01-21

Adds realized_trades table for tracking closed positions and their P&L.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "008_add_realized_trades_table"
down_revision: Union[str, None] = "007_add_exchange_rates_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create realized_trades table if it doesn't exist."""
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'realized_trades')"
    ))
    table_exists = result.scalar()

    if not table_exists:
        op.create_table(
            "realized_trades",
            sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("account_id", UUID(as_uuid=True), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
            sa.Column("asset_id", UUID(as_uuid=True), sa.ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False),

            # Opening data
            sa.Column("open_quantity", sa.Numeric(18, 8), nullable=False),
            sa.Column("open_avg_price", sa.Numeric(18, 6), nullable=False),
            sa.Column("open_date", sa.Date(), nullable=True),

            # Closing data
            sa.Column("close_quantity", sa.Numeric(18, 8), nullable=False),
            sa.Column("close_avg_price", sa.Numeric(18, 6), nullable=False),
            sa.Column("close_date", sa.Date(), nullable=False),

            # P&L
            sa.Column("realized_pnl", sa.Numeric(18, 2), nullable=False),
            sa.Column("realized_pnl_pct", sa.Numeric(10, 4), nullable=True),

            # Reference
            sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),

            # Timestamps
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )

        # Create indexes for faster lookups
        op.create_index("idx_realized_trades_account_id", "realized_trades", ["account_id"])
        op.create_index("idx_realized_trades_asset_id", "realized_trades", ["asset_id"])
        op.create_index("idx_realized_trades_close_date", "realized_trades", ["close_date"])
    else:
        print("Table realized_trades already exists, skipping creation")


def downgrade() -> None:
    """Drop realized_trades table."""
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'realized_trades')"
    ))
    table_exists = result.scalar()

    if table_exists:
        op.drop_index("idx_realized_trades_close_date", table_name="realized_trades", if_exists=True)
        op.drop_index("idx_realized_trades_asset_id", table_name="realized_trades", if_exists=True)
        op.drop_index("idx_realized_trades_account_id", table_name="realized_trades", if_exists=True)
        op.drop_table("realized_trades")
