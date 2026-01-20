"""
InvestmentFundPosition model for mutual funds (Fundos de Investimento).
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, Numeric, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import UUIDMixin, TimestampMixin


class InvestmentFundPosition(Base, UUIDMixin, TimestampMixin):
    """InvestmentFundPosition model for mutual fund investments."""

    __tablename__ = "investment_fund_positions"

    account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Fund identification
    fund_name: Mapped[str] = mapped_column(String(500), nullable=False)
    cnpj: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Position values
    quota_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    quota_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    gross_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    ir_provision: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    net_balance: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)

    # Performance
    performance_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True
    )

    # Reference date
    reference_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Relationships
    account: Mapped["Account"] = relationship(
        "Account", back_populates="investment_fund_positions"
    )
    document: Mapped["Document | None"] = relationship(
        "Document", back_populates="investment_fund_positions"
    )
