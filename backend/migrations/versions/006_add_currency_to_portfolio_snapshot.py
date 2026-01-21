"""Add currency field to portfolio_snapshots

Revision ID: 006_add_currency_to_portfolio_snapshot
Revises: 005_expand_portfolio_snapshot
Create Date: 2026-01-21

Adds currency field to support multi-currency portfolios (BRL, USD).
This is needed for consolidating NAV across accounts with different currencies
(e.g., BTG Brasil in BRL, BTG Cayman in USD).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "006_add_currency_to_portfolio_snapshot"
down_revision: Union[str, None] = "005_expand_portfolio_snapshot"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add currency column to portfolio_snapshots."""
    op.add_column(
        "portfolio_snapshots",
        sa.Column("currency", sa.String(3), nullable=False, server_default="BRL"),
    )


def downgrade() -> None:
    """Remove currency column from portfolio_snapshots."""
    op.drop_column("portfolio_snapshots", "currency")
