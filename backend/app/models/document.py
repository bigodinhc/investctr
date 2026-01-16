"""
Document model for PDF storage.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Integer, String, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import UUIDMixin
from app.schemas.enums import DocumentType, ParsingStatus


class Document(Base, UUIDMixin):
    """Document model for storing uploaded PDFs."""

    __tablename__ = "documents"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    doc_type: Mapped[DocumentType] = mapped_column(
        SAEnum(DocumentType, name="document_type", create_type=False),
        nullable=False,
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    raw_extracted_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    parsing_status: Mapped[ParsingStatus] = mapped_column(
        SAEnum(ParsingStatus, name="parsing_status", create_type=False),
        default=ParsingStatus.PENDING,
    )
    parsing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    account: Mapped["Account | None"] = relationship("Account", back_populates="documents")
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="document"
    )
