"""Add missing enum values for asset_type and transaction_type

Revision ID: 001_add_missing_enum_values
Revises:
Create Date: 2026-01-18

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_add_missing_enum_values"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add new enum values for asset_type and transaction_type."""
    # Add new asset_type values
    op.execute("ALTER TYPE asset_type ADD VALUE IF NOT EXISTS 'fiagro'")
    op.execute("ALTER TYPE asset_type ADD VALUE IF NOT EXISTS 'bdr'")
    op.execute("ALTER TYPE asset_type ADD VALUE IF NOT EXISTS 'reit'")

    # Add new transaction_type values
    op.execute("ALTER TYPE transaction_type ADD VALUE IF NOT EXISTS 'income'")
    op.execute("ALTER TYPE transaction_type ADD VALUE IF NOT EXISTS 'amortization'")
    op.execute("ALTER TYPE transaction_type ADD VALUE IF NOT EXISTS 'transfer_in'")
    op.execute("ALTER TYPE transaction_type ADD VALUE IF NOT EXISTS 'transfer_out'")
    op.execute("ALTER TYPE transaction_type ADD VALUE IF NOT EXISTS 'rental'")
    op.execute("ALTER TYPE transaction_type ADD VALUE IF NOT EXISTS 'other'")


def downgrade() -> None:
    """
    PostgreSQL does not support removing values from enums directly.
    To downgrade, you would need to:
    1. Create a new enum type without the values
    2. Migrate all columns using the old type
    3. Drop the old type and rename the new one

    This is intentionally left empty as removing enum values
    is a complex operation that requires careful data migration.
    """
    pass
