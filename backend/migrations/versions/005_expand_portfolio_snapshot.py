"""Expand portfolio_snapshots table with category breakdown

Revision ID: 005_expand_portfolio_snapshot
Revises: 004_add_investment_fund_positions
Create Date: 2026-01-21

Adds breakdown fields from consolidated_position extracted from BTG statements:
- renda_fixa: Fixed income total
- fundos_investimento: Investment funds total
- renda_variavel: Variable income (stocks) total
- derivativos: Derivatives total
- conta_corrente: Checking account balance
- coe: COE (Certificado de Operações Estruturadas) total
- document_id: Reference to source document

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "005_expand_portfolio_snapshot"
down_revision: Union[str, None] = "004_add_investment_fund_positions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add category breakdown columns to portfolio_snapshots."""
    # Add breakdown columns
    op.add_column(
        "portfolio_snapshots",
        sa.Column("renda_fixa", sa.Numeric(18, 2), nullable=True),
    )
    op.add_column(
        "portfolio_snapshots",
        sa.Column("fundos_investimento", sa.Numeric(18, 2), nullable=True),
    )
    op.add_column(
        "portfolio_snapshots",
        sa.Column("renda_variavel", sa.Numeric(18, 2), nullable=True),
    )
    op.add_column(
        "portfolio_snapshots",
        sa.Column("derivativos", sa.Numeric(18, 2), nullable=True),
    )
    op.add_column(
        "portfolio_snapshots",
        sa.Column("conta_corrente", sa.Numeric(18, 2), nullable=True),
    )
    op.add_column(
        "portfolio_snapshots",
        sa.Column("coe", sa.Numeric(18, 2), nullable=True),
    )

    # Add document_id foreign key
    op.add_column(
        "portfolio_snapshots",
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # Create indexes for efficient queries
    op.create_index(
        "idx_snapshots_user_date",
        "portfolio_snapshots",
        ["user_id", "date"],
    )
    op.create_index(
        "idx_snapshots_account_date",
        "portfolio_snapshots",
        ["account_id", "date"],
    )
    op.create_index(
        "idx_snapshots_document_id",
        "portfolio_snapshots",
        ["document_id"],
    )


def downgrade() -> None:
    """Remove category breakdown columns from portfolio_snapshots."""
    # Drop indexes
    op.drop_index("idx_snapshots_document_id", table_name="portfolio_snapshots")
    op.drop_index("idx_snapshots_account_date", table_name="portfolio_snapshots")
    op.drop_index("idx_snapshots_user_date", table_name="portfolio_snapshots")

    # Drop columns
    op.drop_column("portfolio_snapshots", "document_id")
    op.drop_column("portfolio_snapshots", "coe")
    op.drop_column("portfolio_snapshots", "conta_corrente")
    op.drop_column("portfolio_snapshots", "derivativos")
    op.drop_column("portfolio_snapshots", "renda_variavel")
    op.drop_column("portfolio_snapshots", "fundos_investimento")
    op.drop_column("portfolio_snapshots", "renda_fixa")
