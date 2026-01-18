"""
Account model.
"""

from uuid import UUID

from sqlalchemy import Boolean, String, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import UUIDMixin, TimestampMixin
from app.schemas.enums import AccountType


class Account(Base, UUIDMixin, TimestampMixin):
    """Account model representing a brokerage account."""

    __tablename__ = "accounts"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[AccountType] = mapped_column(
        SAEnum(
            AccountType,
            name="account_type",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(String(3), default="BRL", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="account", cascade="all, delete-orphan"
    )
    positions: Mapped[list["Position"]] = relationship(
        "Position", back_populates="account", cascade="all, delete-orphan"
    )
    cash_flows: Mapped[list["CashFlow"]] = relationship(
        "CashFlow", back_populates="account", cascade="all, delete-orphan"
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="account"
    )
