"""
RealizedTrade model for tracking closed positions and their P&L.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, DateTime, Numeric, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import UUIDMixin


class RealizedTrade(Base, UUIDMixin):
    """
    RealizedTrade model for tracking closed positions and their P&L.

    This table records trades that have been closed (position reduced or exited),
    tracking the realized profit/loss from the trade.
    """

    __tablename__ = "realized_trades"

    account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Opening data
    open_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    open_avg_price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    open_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Closing data
    close_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    close_avg_price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    close_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # P&L
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    realized_pnl_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)

    # Reference to the document that caused this trade to be recorded
    document_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
    )

    # Relationships
    account: Mapped["Account"] = relationship("Account", back_populates="realized_trades")
    asset: Mapped["Asset"] = relationship("Asset", back_populates="realized_trades")
    document: Mapped["Document"] = relationship("Document", back_populates="realized_trades")
