"""
FixedIncomePosition model for CDB, LCA, LCI, Treasury bonds, etc.
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, Numeric, String, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import UUIDMixin, TimestampMixin
from app.schemas.enums import FixedIncomeType, IndexerType


class FixedIncomePosition(Base, UUIDMixin, TimestampMixin):
    """FixedIncomePosition model for fixed income investments."""

    __tablename__ = "fixed_income_positions"

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

    # Identification
    asset_name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_type: Mapped[FixedIncomeType] = mapped_column(
        SAEnum(
            FixedIncomeType,
            name="fixed_income_type",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    issuer: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Values
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    total_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    # Rates
    indexer: Mapped[IndexerType | None] = mapped_column(
        SAEnum(
            IndexerType,
            name="indexer_type",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=True,
    )
    rate_percent: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)

    # Dates
    acquisition_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    maturity_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    reference_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Relationships
    account: Mapped["Account"] = relationship("Account", back_populates="fixed_income_positions")
    document: Mapped["Document | None"] = relationship(
        "Document", back_populates="fixed_income_positions"
    )
