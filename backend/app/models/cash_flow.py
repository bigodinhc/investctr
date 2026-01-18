"""
CashFlow model for deposits and withdrawals.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, Numeric, String, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import UUIDMixin
from app.schemas.enums import CashFlowType


class CashFlow(Base, UUIDMixin):
    """CashFlow model for deposits and withdrawals."""

    __tablename__ = "cash_flows"

    account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[CashFlowType] = mapped_column(
        SAEnum(
            CashFlowType,
            name="cash_flow_type",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="BRL", nullable=False)
    exchange_rate: Mapped[Decimal] = mapped_column(Numeric(10, 6), default=Decimal("1"))
    # amount_brl is a generated column in the database
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    shares_affected: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 8), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    account: Mapped["Account"] = relationship("Account", back_populates="cash_flows")
