"""
Document schemas for request/response validation.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, IDMixin
from app.schemas.enums import DocumentType, ParsingStatus


class DocumentBase(BaseSchema):
    """Base document schema with common fields."""

    doc_type: DocumentType = Field(..., description="Type of document")
    account_id: UUID | None = Field(None, description="Associated account ID")


class DocumentUpload(BaseSchema):
    """Schema for document upload request."""

    doc_type: DocumentType = Field(..., description="Type of document")
    account_id: UUID | None = Field(None, description="Associated account ID")


class DocumentCreate(DocumentBase):
    """Schema for creating a document record."""

    file_name: str = Field(..., min_length=1, max_length=255)
    file_path: str = Field(..., min_length=1, max_length=500)
    file_size: int | None = Field(None, ge=0)


class DocumentResponse(DocumentBase, IDMixin):
    """Document response schema."""

    file_name: str
    file_path: str
    file_size: int | None
    parsing_status: ParsingStatus
    parsing_error: str | None = None
    parsing_stage: str | None = None
    parsed_at: datetime | None = None
    created_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "doc_type": "statement",
                "account_id": "123e4567-e89b-12d3-a456-426614174001",
                "file_name": "extrato_jan_2026.pdf",
                "file_path": "documents/user123/extrato_jan_2026.pdf",
                "file_size": 245678,
                "parsing_status": "pending",
                "parsing_error": None,
                "parsed_at": None,
                "created_at": "2026-01-16T10:30:00Z",
            }
        }


class DocumentWithData(DocumentResponse):
    """Document response with parsed data."""

    raw_extracted_data: dict[str, Any] | None = None


class DocumentsListResponse(BaseSchema):
    """Response for listing documents."""

    items: list[DocumentResponse]
    total: int


class ParsedTransaction(BaseSchema):
    """Schema for a transaction extracted from a document."""

    date: str = Field(..., description="Transaction date (YYYY-MM-DD)")
    type: str = Field(..., description="Transaction type (buy, sell, dividend, etc)")
    ticker: str = Field(..., description="Asset ticker symbol")
    quantity: float | str | None = Field(None, description="Quantity traded")
    price: float | str | None = Field(None, description="Unit price")
    total: float | str | None = Field(None, description="Total value")
    fees: float | str | None = Field(None, description="Fees/costs")
    notes: str | None = Field(None, description="Additional notes")


class ParsedFixedIncome(BaseSchema):
    """Schema for fixed income position extracted from a document."""

    asset_name: str
    asset_type: str
    issuer: str | None = None
    quantity: float | str
    unit_price: float | str | None = None
    total_value: float | str
    indexer: str | None = None
    rate_percent: float | str | None = None
    acquisition_date: str | None = None
    maturity_date: str | None = None


class ParsedStockLending(BaseSchema):
    """Schema for stock lending extracted from a document."""

    date: str
    type: str  # lending_out, lending_return, rental_income
    ticker: str
    quantity: float | str
    rate_percent: float | str | None = None
    total: float | str


class ParsedCashMovement(BaseSchema):
    """Schema for cash movement extracted from a document."""

    date: str
    type: str  # dividend, jcp, interest, fee, tax, etc
    description: str | None = None
    ticker: str | None = None
    value: float | str


class ParsedDocumentData(BaseSchema):
    """Schema for parsed document data from Claude."""

    document_type: str
    period: dict[str, Any] | None = None
    account_number: str | None = None
    transactions: list[dict[str, Any]] = []
    summary: dict[str, Any] | None = None
    fixed_income_positions: list[dict[str, Any]] | None = None
    stock_lending: list[dict[str, Any]] | None = None
    cash_movements: list[dict[str, Any]] | None = None
    consolidated_position: dict[str, Any] | None = None


class DocumentParseResponse(BaseSchema):
    """Response after parsing a document."""

    document_id: UUID
    status: ParsingStatus
    stage: str | None = None
    transactions_count: int = 0
    data: ParsedDocumentData | None = None
    error: str | None = None


class DocumentParseRequest(BaseSchema):
    """Request to parse a document."""

    async_mode: bool = Field(
        default=True,
        description="If True, parsing runs in background via Celery. If False, waits for completion.",
    )


class ParseTaskResponse(BaseSchema):
    """Response when parsing is triggered asynchronously."""

    document_id: UUID
    task_id: str
    status: ParsingStatus
    message: str
