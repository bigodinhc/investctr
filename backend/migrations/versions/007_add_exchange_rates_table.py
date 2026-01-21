"""Add exchange_rates table

Revision ID: 007_add_exchange_rates_table
Revises: 006_add_currency_to_portfolio_snapshot
Create Date: 2026-01-21

Adds exchange_rates table for storing historical currency conversion rates
(e.g., PTAX USD/BRL rates from BCB).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "007_add_exchange_rates_table"
down_revision: Union[str, None] = "006_add_currency_to_portfolio_snapshot"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create exchange_rates table."""
    op.create_table(
        "exchange_rates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("from_currency", sa.String(3), nullable=False),
        sa.Column("to_currency", sa.String(3), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("rate", sa.Numeric(10, 6), nullable=False),
        sa.Column("source", sa.String(20), server_default="bcb"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("from_currency", "to_currency", "date", name="uq_exchange_rates_currencies_date"),
    )

    # Create index for faster lookups
    op.create_index("idx_exchange_rates_currencies_date", "exchange_rates", ["from_currency", "to_currency", "date"])


def downgrade() -> None:
    """Drop exchange_rates table."""
    op.drop_index("idx_exchange_rates_currencies_date", table_name="exchange_rates")
    op.drop_table("exchange_rates")
