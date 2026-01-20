"""Add investment_fund_positions table for mutual funds

Revision ID: 004_add_investment_fund_positions
Revises: 003_add_fixed_income_and_expand_cash_flows
Create Date: 2026-01-20

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "004_add_investment_fund_positions"
down_revision: Union[str, None] = "003_add_fixed_income_and_expand_cash_flows"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add investment_fund_positions table."""
    # Create investment_fund_positions table
    op.create_table(
        "investment_fund_positions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            primary_key=True,
        ),
        sa.Column(
            "account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Fund identification
        sa.Column("fund_name", sa.String(500), nullable=False),
        sa.Column("cnpj", sa.String(20), nullable=True),  # CNPJ of the fund
        # Position values
        sa.Column("quota_quantity", sa.Numeric(18, 8), nullable=False),
        sa.Column("quota_price", sa.Numeric(18, 8), nullable=True),
        sa.Column("gross_balance", sa.Numeric(18, 2), nullable=False),
        sa.Column("ir_provision", sa.Numeric(18, 2), nullable=True),  # IR tax provision
        sa.Column("net_balance", sa.Numeric(18, 2), nullable=True),
        # Performance
        sa.Column("performance_pct", sa.Numeric(10, 4), nullable=True),  # Monthly performance %
        # Reference date
        sa.Column("reference_date", sa.Date, nullable=False),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=True,
        ),
    )

    # Create indexes
    op.create_index(
        "ix_investment_fund_positions_account_id",
        "investment_fund_positions",
        ["account_id"],
    )
    op.create_index(
        "ix_investment_fund_positions_reference_date",
        "investment_fund_positions",
        ["reference_date"],
    )
    op.create_index(
        "ix_investment_fund_positions_cnpj",
        "investment_fund_positions",
        ["cnpj"],
    )

    # Enable RLS on investment_fund_positions
    op.execute("ALTER TABLE investment_fund_positions ENABLE ROW LEVEL SECURITY")

    # Create RLS policies for investment_fund_positions
    op.execute("""
        CREATE POLICY investment_fund_positions_user_policy ON investment_fund_positions
        FOR ALL
        USING (account_id IN (SELECT id FROM accounts WHERE user_id = auth.uid()))
        WITH CHECK (account_id IN (SELECT id FROM accounts WHERE user_id = auth.uid()))
    """)


def downgrade() -> None:
    """Remove investment_fund_positions table."""
    # Drop RLS policy
    op.execute(
        "DROP POLICY IF EXISTS investment_fund_positions_user_policy ON investment_fund_positions"
    )

    # Drop indexes
    op.drop_index(
        "ix_investment_fund_positions_cnpj", table_name="investment_fund_positions"
    )
    op.drop_index(
        "ix_investment_fund_positions_reference_date",
        table_name="investment_fund_positions",
    )
    op.drop_index(
        "ix_investment_fund_positions_account_id",
        table_name="investment_fund_positions",
    )

    # Drop table
    op.drop_table("investment_fund_positions")
