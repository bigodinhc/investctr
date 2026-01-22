"""Add source field to positions table

Revision ID: 009_add_position_source
Revises: 008_add_realized_trades_table
Create Date: 2026-01-21

Adds source field to positions table to track whether position came from
statement import (source of truth) or was calculated from transactions.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "009_add_position_source"
down_revision: Union[str, None] = "008_add_realized_trades_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add source column to positions table."""
    conn = op.get_bind()

    # Check if column already exists
    result = conn.execute(sa.text("""
        SELECT EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_name = 'positions' AND column_name = 'source'
        )
    """))
    column_exists = result.scalar()

    if not column_exists:
        # Add source column with default 'calculated'
        op.add_column(
            "positions",
            sa.Column(
                "source",
                sa.String(20),
                server_default="calculated",
                nullable=False
            )
        )
        print("Added source column to positions table")
    else:
        print("Column source already exists in positions, skipping")


def downgrade() -> None:
    """Remove source column from positions table."""
    conn = op.get_bind()

    result = conn.execute(sa.text("""
        SELECT EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_name = 'positions' AND column_name = 'source'
        )
    """))
    column_exists = result.scalar()

    if column_exists:
        op.drop_column("positions", "source")
