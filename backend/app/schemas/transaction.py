"""
Transaction schemas for request/response validation.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.base import BaseSchema, IDMixin
from app.schemas.enums import TransactionType, Currency


class TransactionBase(BaseSchema):
    """Base transaction schema with common fields."""

    type: TransactionType = Field(..., description="Type of transaction")
    quantity: Decimal = Field(..., description="Quantity of shares/units")
    price: Decimal = Field(..., ge=0, description="Unit price")
    fees: Decimal = Field(default=Decimal("0"), ge=0, description="Transaction fees")
    currency: Currency = Field(default=Currency.BRL, description="Transaction currency")
    exchange_rate: Decimal = Field(
        default=Decimal("1"), description="Exchange rate to BRL"
    )
    executed_at: datetime = Field(..., description="Transaction execution date/time")
    notes: str | None = Field(None, max_length=500, description="Additional notes")


class TransactionCreate(TransactionBase):
    """Schema for creating a new transaction."""

    account_id: UUID = Field(..., description="Account ID")
    asset_id: UUID = Field(..., description="Asset ID")
    document_id: UUID | None = Field(None, description="Source document ID")


class TransactionCreateFromParsing(BaseSchema):
    """Schema for creating transaction from parsed document data."""

    date: str = Field(..., description="Transaction date (YYYY-MM-DD)")
    type: str = Field(..., description="Transaction type")
    ticker: str = Field(..., description="Asset ticker symbol")
    asset_name: str | None = Field(None, description="Asset name for auto-creation")
    quantity: Decimal | None = Field(None, description="Quantity")
    price: Decimal | None = Field(None, description="Unit price")
    total: Decimal | None = Field(None, description="Total value")
    fees: Decimal | None = Field(None, description="Fees")
    notes: str | None = Field(None, description="Additional notes")

    @field_validator("type", mode="before")
    @classmethod
    def normalize_type(cls, v: str) -> str:
        """Normalize transaction type to enum values."""
        if not v:
            return "other"
        return v.lower().strip()


class TransactionUpdate(BaseSchema):
    """Schema for updating a transaction."""

    type: TransactionType | None = None
    quantity: Decimal | None = Field(None, description="Quantity of shares/units")
    price: Decimal | None = Field(None, ge=0, description="Unit price")
    fees: Decimal | None = Field(None, ge=0, description="Transaction fees")
    executed_at: datetime | None = None
    notes: str | None = None


class TransactionResponse(TransactionBase, IDMixin):
    """Transaction response schema."""

    account_id: UUID
    asset_id: UUID
    document_id: UUID | None = None
    total_value: Decimal | None = Field(
        None, description="Total transaction value (qty * price)"
    )
    created_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "account_id": "123e4567-e89b-12d3-a456-426614174001",
                "asset_id": "123e4567-e89b-12d3-a456-426614174002",
                "document_id": None,
                "type": "buy",
                "quantity": "100.00000000",
                "price": "58.500000",
                "total_value": "5850.00",
                "fees": "4.90",
                "currency": "BRL",
                "exchange_rate": "1.000000",
                "executed_at": "2026-01-15T14:30:00Z",
                "notes": "Regular purchase",
                "created_at": "2026-01-15T15:00:00Z",
            }
        }


class TransactionWithAsset(TransactionResponse):
    """Transaction response with asset details."""

    ticker: str = Field(..., description="Asset ticker")
    asset_name: str = Field(..., description="Asset name")


class TransactionsListResponse(BaseSchema):
    """Response for listing transactions."""

    items: list[TransactionResponse]
    total: int


class TransactionsWithAssetListResponse(BaseSchema):
    """Response for listing transactions with asset info."""

    items: list[TransactionWithAsset]
    total: int


# ============================================================================
# Commit-related schemas
# ============================================================================


class CommitTransactionItem(BaseSchema):
    """Single transaction item in commit request."""

    date: str = Field(..., description="Transaction date (YYYY-MM-DD)")
    type: str = Field(..., description="Transaction type")
    ticker: str = Field(..., min_length=1, description="Asset ticker")
    asset_name: str | None = Field(None, description="Asset name (for auto-creation)")
    asset_type: str | None = Field(
        None, description="Asset type (stock, fii, etf, etc.)"
    )
    quantity: Decimal | None = None
    price: Decimal | None = None
    total: Decimal | None = None
    fees: Decimal | None = None
    notes: str | None = None


class CommitStockLendingItem(BaseSchema):
    """Single stock lending item in commit request."""

    date: str = Field(..., description="Date (YYYY-MM-DD)")
    type: str = Field(..., description="lending_out or lending_return")
    ticker: str = Field(..., min_length=1, description="Asset ticker")
    quantity: Decimal = Field(..., description="Quantity of shares")
    rate_percent: Decimal | None = Field(None, description="Rental rate percentage")
    total: Decimal = Field(..., description="Total rental value")
    notes: str | None = None


class CommitCashMovementItem(BaseSchema):
    """Single cash movement item in commit request."""

    date: str = Field(..., description="Date (YYYY-MM-DD)")
    type: str = Field(
        ...,
        description="Type: deposit, withdrawal, dividend, jcp, interest, fee, tax, settlement, rental_income, other",
    )
    description: str | None = Field(None, description="Movement description")
    ticker: str | None = Field(None, description="Related asset ticker (for dividends, etc)")
    value: Decimal = Field(..., description="Movement value (positive for inflows)")


class CommitFixedIncomeItem(BaseSchema):
    """Single fixed income item in commit request."""

    asset_name: str = Field(..., max_length=255, description="Asset name/identifier")
    asset_type: str = Field(..., description="Type: cdb, lca, lci, lft, ntnb, ntnf, etc")
    issuer: str | None = Field(None, description="Issuing institution")
    quantity: Decimal = Field(..., description="Quantity/units")
    unit_price: Decimal | None = Field(None, description="Unit price")
    total_value: Decimal = Field(..., description="Total value")
    indexer: str | None = Field(None, description="Indexer: cdi, selic, ipca, etc")
    rate_percent: Decimal | None = Field(None, description="Rate percentage")
    acquisition_date: str | None = Field(None, description="YYYY-MM-DD")
    maturity_date: str | None = Field(None, description="YYYY-MM-DD")
    reference_date: str = Field(..., description="YYYY-MM-DD")


class CommitDocumentRequest(BaseSchema):
    """Request to commit parsed document data."""

    account_id: UUID = Field(..., description="Account to associate data with")
    transactions: list[CommitTransactionItem] = Field(
        default_factory=list, description="Buy/sell transactions to commit"
    )
    fixed_income: list[CommitFixedIncomeItem] = Field(
        default_factory=list, description="Fixed income positions to commit"
    )
    stock_lending: list[CommitStockLendingItem] = Field(
        default_factory=list, description="Stock lending records to commit"
    )
    cash_movements: list[CommitCashMovementItem] = Field(
        default_factory=list, description="Cash movements to commit"
    )


class CommitDocumentResponse(BaseSchema):
    """Response after committing document data."""

    document_id: UUID
    transactions_created: int
    assets_created: int
    positions_updated: int
    fixed_income_created: int = 0
    cash_flows_created: int = 0
    errors: list[str] = Field(default_factory=list)
