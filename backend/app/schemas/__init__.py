"""
Pydantic schemas for request/response validation.
"""

from app.schemas.account import (
    AccountCreate,
    AccountInDB,
    AccountResponse,
    AccountsListResponse,
    AccountUpdate,
)
from app.schemas.asset import (
    AssetCreate,
    AssetInDB,
    AssetResponse,
    AssetsListResponse,
    AssetWithPrice,
)
from app.schemas.base import BaseSchema, IDMixin, PaginatedResponse, TimestampMixin
from app.schemas.document import (
    DocumentCreate,
    DocumentParseResponse,
    DocumentResponse,
    DocumentsListResponse,
    DocumentUpload,
    DocumentWithData,
    ParsedDocumentData,
    ParsedTransaction,
)
from app.schemas.enums import (
    AccountType,
    AssetType,
    CashFlowType,
    Currency,
    DocumentType,
    FixedIncomeType,
    IndexerType,
    ParsingStatus,
    PositionType,
    TransactionType,
)
from app.schemas.fixed_income import (
    FixedIncomePositionCreate,
    FixedIncomePositionResponse,
    FixedIncomePositionsListResponse,
)
from app.schemas.investment_fund import (
    InvestmentFundPositionCreate,
    InvestmentFundPositionResponse,
    InvestmentFundPositionsListResponse,
)
from app.schemas.position import (
    ConsolidatedPosition,
    ConsolidatedPositionsResponse,
    PortfolioSummary,
    PositionResponse,
    PositionsListResponse,
    PositionSummary,
    PositionsWithAssetListResponse,
    PositionsWithMarketDataResponse,
    PositionWithAsset,
    PositionWithMarketData,
)
from app.schemas.transaction import (
    CommitCashMovementItem,
    CommitDocumentRequest,
    CommitDocumentResponse,
    CommitFixedIncomeItem,
    CommitInvestmentFundItem,
    CommitStockLendingItem,
    CommitTransactionItem,
    TransactionCreate,
    TransactionCreateFromParsing,
    TransactionResponse,
    TransactionsListResponse,
    TransactionsWithAssetListResponse,
    TransactionUpdate,
    TransactionWithAsset,
)

__all__ = [
    # Base
    "BaseSchema",
    "IDMixin",
    "TimestampMixin",
    "PaginatedResponse",
    # Enums
    "AccountType",
    "AssetType",
    "TransactionType",
    "PositionType",
    "CashFlowType",
    "DocumentType",
    "Currency",
    "FixedIncomeType",
    "IndexerType",
    # Account
    "AccountCreate",
    "AccountUpdate",
    "AccountInDB",
    "AccountResponse",
    "AccountsListResponse",
    # Asset
    "AssetCreate",
    "AssetInDB",
    "AssetResponse",
    "AssetsListResponse",
    "AssetWithPrice",
    # Document
    "DocumentCreate",
    "DocumentUpload",
    "DocumentResponse",
    "DocumentsListResponse",
    "DocumentWithData",
    "DocumentParseResponse",
    "ParsedDocumentData",
    "ParsedTransaction",
    "ParsingStatus",
    # Transaction
    "TransactionCreate",
    "TransactionCreateFromParsing",
    "TransactionUpdate",
    "TransactionResponse",
    "TransactionWithAsset",
    "TransactionsListResponse",
    "TransactionsWithAssetListResponse",
    "CommitTransactionItem",
    "CommitFixedIncomeItem",
    "CommitInvestmentFundItem",
    "CommitStockLendingItem",
    "CommitCashMovementItem",
    "CommitDocumentRequest",
    "CommitDocumentResponse",
    # Fixed Income
    "FixedIncomePositionCreate",
    "FixedIncomePositionResponse",
    "FixedIncomePositionsListResponse",
    # Investment Fund
    "InvestmentFundPositionCreate",
    "InvestmentFundPositionResponse",
    "InvestmentFundPositionsListResponse",
    # Position
    "PositionResponse",
    "PositionWithAsset",
    "PositionWithMarketData",
    "PositionsListResponse",
    "PositionsWithAssetListResponse",
    "PositionsWithMarketDataResponse",
    "ConsolidatedPosition",
    "ConsolidatedPositionsResponse",
    "PositionSummary",
    "PortfolioSummary",
]
