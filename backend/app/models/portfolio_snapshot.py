"""
PortfolioSnapshot model for daily portfolio state.

Stores portfolio value breakdown by category, extracted from brokerage statements.
The consolidated_position from BTG statements is the source of truth for these values.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, DateTime, Index, Numeric, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import UUIDMixin


class PortfolioSnapshot(Base, UUIDMixin):
    """PortfolioSnapshot model for storing daily portfolio state.

    This model stores the official portfolio breakdown from brokerage statements.
    The 'nav' field comes directly from the statement's consolidated_position.total,
    making the statement the source of truth rather than our own calculations.
    """

    __tablename__ = "portfolio_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "date", "account_id", name="uq_snapshots_user_date_account"
        ),
        Index("idx_snapshots_user_date", "user_id", "date"),
        Index("idx_snapshots_account_date", "account_id", "date"),
    )

    # Note: FK constraint to auth.users exists in DB but not in SQLAlchemy
    # because auth.users is in a different schema managed by Supabase
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    account_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Total NAV from statement's consolidated_position.total
    nav: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), default="BRL", nullable=False, server_default="BRL"
    )
    total_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    unrealized_pnl: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0")
    )

    # Category breakdown from statement's consolidated_position
    renda_fixa: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    fundos_investimento: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2), nullable=True
    )
    renda_variavel: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2), nullable=True
    )
    derivativos: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    conta_corrente: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2), nullable=True
    )
    coe: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)

    # Reference to the source document
    document_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    # Relationship to document
    document: Mapped["Document | None"] = relationship("Document")
