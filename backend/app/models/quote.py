"""
Quote model for price history.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, Numeric, String, BigInteger, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import UUIDMixin


class Quote(Base, UUIDMixin):
    """Quote model for storing historical prices."""

    __tablename__ = "quotes"
    __table_args__ = (
        UniqueConstraint("asset_id", "date", name="uq_quotes_asset_date"),
    )

    asset_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    high: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    low: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    close: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    adjusted_close: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 6), nullable=True
    )
    volume: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="yfinance")
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    asset: Mapped["Asset"] = relationship("Asset", back_populates="quotes")
