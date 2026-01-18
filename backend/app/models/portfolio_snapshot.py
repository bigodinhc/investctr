"""
PortfolioSnapshot model for daily portfolio state.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, DateTime, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import UUIDMixin


class PortfolioSnapshot(Base, UUIDMixin):
    """PortfolioSnapshot model for storing daily portfolio state."""

    __tablename__ = "portfolio_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "date", "account_id", name="uq_snapshots_user_date_account"
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    account_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=True,
    )
    nav: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    unrealized_pnl: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
