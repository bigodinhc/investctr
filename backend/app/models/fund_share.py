"""
FundShare model for the quota system.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, DateTime, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import UUIDMixin


class FundShare(Base, UUIDMixin):
    """FundShare model for tracking NAV and share values."""

    __tablename__ = "fund_shares"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_fund_shares_user_date"),
    )

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    nav: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    shares_outstanding: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    share_value: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    daily_return: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    cumulative_return: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
