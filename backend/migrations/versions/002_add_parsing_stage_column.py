"""Add parsing_stage column to documents table

Revision ID: 002_add_parsing_stage_column
Revises: 001_add_missing_enum_values
Create Date: 2026-01-19

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002_add_parsing_stage_column"
down_revision: Union[str, None] = "001_add_missing_enum_values"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add parsing_stage column to documents table."""
    op.add_column(
        "documents",
        sa.Column("parsing_stage", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    """Remove parsing_stage column from documents table."""
    op.drop_column("documents", "parsing_stage")
