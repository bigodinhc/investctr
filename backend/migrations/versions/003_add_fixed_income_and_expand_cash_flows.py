"""Add fixed_income_positions table and expand cash_flow_type enum

Revision ID: 003_add_fixed_income_and_expand_cash_flows
Revises: 002_add_parsing_stage_column
Create Date: 2026-01-19

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003_add_fixed_income_and_expand_cash_flows"
down_revision: Union[str, None] = "002_add_parsing_stage_column"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add fixed_income_positions table and expand cash_flow_type enum."""
    # Expand cash_flow_type enum with new values
    op.execute("ALTER TYPE cash_flow_type ADD VALUE IF NOT EXISTS 'dividend'")
    op.execute("ALTER TYPE cash_flow_type ADD VALUE IF NOT EXISTS 'jcp'")
    op.execute("ALTER TYPE cash_flow_type ADD VALUE IF NOT EXISTS 'interest'")
    op.execute("ALTER TYPE cash_flow_type ADD VALUE IF NOT EXISTS 'fee'")
    op.execute("ALTER TYPE cash_flow_type ADD VALUE IF NOT EXISTS 'tax'")
    op.execute("ALTER TYPE cash_flow_type ADD VALUE IF NOT EXISTS 'settlement'")
    op.execute("ALTER TYPE cash_flow_type ADD VALUE IF NOT EXISTS 'rental_income'")
    op.execute("ALTER TYPE cash_flow_type ADD VALUE IF NOT EXISTS 'other'")

    # Create fixed_income_type enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE fixed_income_type AS ENUM (
                'cdb', 'lca', 'lci', 'lft', 'ntnb', 'ntnf', 'lf', 'debenture', 'cri', 'cra', 'other'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create indexer_type enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE indexer_type AS ENUM (
                'cdi', 'selic', 'ipca', 'igpm', 'prefixado', 'other'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create fixed_income_positions table
    op.create_table(
        "fixed_income_positions",
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
        # Identification
        sa.Column("asset_name", sa.String(255), nullable=False),
        sa.Column(
            "asset_type",
            postgresql.ENUM(
                "cdb",
                "lca",
                "lci",
                "lft",
                "ntnb",
                "ntnf",
                "lf",
                "debenture",
                "cri",
                "cra",
                "other",
                name="fixed_income_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("issuer", sa.String(255), nullable=True),
        # Values
        sa.Column("quantity", sa.Numeric(18, 8), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 8), nullable=True),
        sa.Column("total_value", sa.Numeric(18, 2), nullable=False),
        # Rates
        sa.Column(
            "indexer",
            postgresql.ENUM(
                "cdi",
                "selic",
                "ipca",
                "igpm",
                "prefixado",
                "other",
                name="indexer_type",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("rate_percent", sa.Numeric(8, 4), nullable=True),
        # Dates
        sa.Column("acquisition_date", sa.Date, nullable=True),
        sa.Column("maturity_date", sa.Date, nullable=True),
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
        "ix_fixed_income_positions_account_id", "fixed_income_positions", ["account_id"]
    )
    op.create_index(
        "ix_fixed_income_positions_reference_date",
        "fixed_income_positions",
        ["reference_date"],
    )
    op.create_index(
        "ix_fixed_income_positions_asset_type", "fixed_income_positions", ["asset_type"]
    )

    # Enable RLS on fixed_income_positions
    op.execute("ALTER TABLE fixed_income_positions ENABLE ROW LEVEL SECURITY")

    # Create RLS policies for fixed_income_positions
    op.execute("""
        CREATE POLICY fixed_income_positions_user_policy ON fixed_income_positions
        FOR ALL
        USING (account_id IN (SELECT id FROM accounts WHERE user_id = auth.uid()))
        WITH CHECK (account_id IN (SELECT id FROM accounts WHERE user_id = auth.uid()))
    """)


def downgrade() -> None:
    """Remove fixed_income_positions table and related objects."""
    # Drop RLS policy
    op.execute(
        "DROP POLICY IF EXISTS fixed_income_positions_user_policy ON fixed_income_positions"
    )

    # Drop indexes
    op.drop_index(
        "ix_fixed_income_positions_asset_type", table_name="fixed_income_positions"
    )
    op.drop_index(
        "ix_fixed_income_positions_reference_date", table_name="fixed_income_positions"
    )
    op.drop_index(
        "ix_fixed_income_positions_account_id", table_name="fixed_income_positions"
    )

    # Drop table
    op.drop_table("fixed_income_positions")

    # Drop enums (only if not used elsewhere)
    op.execute("DROP TYPE IF EXISTS indexer_type")
    op.execute("DROP TYPE IF EXISTS fixed_income_type")

    # Note: Cannot remove enum values from cash_flow_type in PostgreSQL
