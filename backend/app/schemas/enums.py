"""
Enum definitions for schemas.
"""

from enum import Enum


class AccountType(str, Enum):
    """Types of investment accounts."""

    BTG_BR = "btg_br"
    XP = "xp"
    BTG_CAYMAN = "btg_cayman"
    TESOURO_DIRETO = "tesouro_direto"


class AssetType(str, Enum):
    """Types of financial assets."""

    STOCK = "stock"
    ETF = "etf"
    FII = "fii"
    OPTION = "option"
    FUTURE = "future"
    BOND = "bond"
    TREASURY = "treasury"
    CRYPTO = "crypto"
    FUND = "fund"


class TransactionType(str, Enum):
    """Types of transactions."""

    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"
    JCP = "jcp"
    SPLIT = "split"
    REVERSE_SPLIT = "reverse_split"
    BONUS = "bonus"
    SUBSCRIPTION = "subscription"
    FEE = "fee"


class PositionType(str, Enum):
    """Types of positions."""

    LONG = "long"
    SHORT = "short"
    DAY_TRADE = "day_trade"


class CashFlowType(str, Enum):
    """Types of cash flows."""

    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"


class DocumentType(str, Enum):
    """Types of documents."""

    STATEMENT = "statement"
    TRADE_NOTE = "trade_note"
    INCOME_REPORT = "income_report"
    OTHER = "other"


class Currency(str, Enum):
    """Supported currencies."""

    BRL = "BRL"
    USD = "USD"


class ParsingStatus(str, Enum):
    """Status of document parsing."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
