"""
Asset model.
"""

from sqlalchemy import Boolean, String, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import UUIDMixin, TimestampMixin
from app.schemas.enums import AssetType


class Asset(Base, UUIDMixin, TimestampMixin):
    """Asset model representing a tradeable asset."""

    __tablename__ = "assets"

    ticker: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    asset_type: Mapped[AssetType] = mapped_column(
        SAEnum(
            AssetType,
            name="asset_type",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(String(3), default="BRL", nullable=False)
    exchange: Mapped[str | None] = mapped_column(String(20), nullable=True)
    lseg_ric: Mapped[str | None] = mapped_column(String(30), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    quotes: Mapped[list["Quote"]] = relationship(
        "Quote", back_populates="asset", cascade="all, delete-orphan"
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="asset"
    )
    positions: Mapped[list["Position"]] = relationship(
        "Position", back_populates="asset"
    )
    realized_trades: Mapped[list["RealizedTrade"]] = relationship(
        "RealizedTrade", back_populates="asset"
    )
