"""
Position model.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, Numeric, ForeignKey, UniqueConstraint, Enum as SAEnum, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import UUIDMixin
from app.schemas.enums import PositionType, PositionSource


class Position(Base, UUIDMixin):
    """Position model for open positions."""

    __tablename__ = "positions"
    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "asset_id",
            "position_type",
            name="uq_positions_account_asset_type",
        ),
    )

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
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), default=Decimal("0"))
    avg_price: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0"))
    total_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    position_type: Mapped[PositionType] = mapped_column(
        SAEnum(
            PositionType,
            name="position_type",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=PositionType.LONG,
    )
    opened_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    source: Mapped[str] = mapped_column(
        String(20),
        default=PositionSource.CALCULATED.value,
    )

    # Relationships
    account: Mapped["Account"] = relationship("Account", back_populates="positions")
    asset: Mapped["Asset"] = relationship("Asset", back_populates="positions")
