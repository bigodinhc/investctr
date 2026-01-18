"""
Transaction model.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, Numeric, String, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import UUIDMixin, TimestampMixin
from app.schemas.enums import TransactionType


class Transaction(Base, UUIDMixin, TimestampMixin):
    """Transaction model for trades, dividends, etc."""

    __tablename__ = "transactions"

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
    document_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    type: Mapped[TransactionType] = mapped_column(
        SAEnum(
            TransactionType,
            name="transaction_type",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    # total_value is a generated column in the database
    fees: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(3), default="BRL", nullable=False)
    exchange_rate: Mapped[Decimal] = mapped_column(Numeric(10, 6), default=Decimal("1"))
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    account: Mapped["Account"] = relationship("Account", back_populates="transactions")
    asset: Mapped["Asset"] = relationship("Asset", back_populates="transactions")
    document: Mapped["Document | None"] = relationship("Document", back_populates="transactions")
