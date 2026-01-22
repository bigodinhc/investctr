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
    FIAGRO = "fiagro"
    BDR = "bdr"
    REIT = "reit"


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
    INCOME = "income"
    AMORTIZATION = "amortization"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"
    RENTAL = "rental"
    OTHER = "other"


class PositionType(str, Enum):
    """Types of positions."""

    LONG = "long"
    SHORT = "short"
    DAY_TRADE = "day_trade"


class CashFlowType(str, Enum):
    """Types of cash flows."""

    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    DIVIDEND = "dividend"
    JCP = "jcp"
    INTEREST = "interest"
    FEE = "fee"
    TAX = "tax"
    SETTLEMENT = "settlement"
    RENTAL_INCOME = "rental_income"
    OTHER = "other"


class FixedIncomeType(str, Enum):
    """Types of fixed income investments."""

    CDB = "cdb"
    LCA = "lca"
    LCI = "lci"
    LFT = "lft"
    NTNB = "ntnb"
    NTNF = "ntnf"
    LF = "lf"
    DEBENTURE = "debenture"
    CRI = "cri"
    CRA = "cra"
    OTHER = "other"


class IndexerType(str, Enum):
    """Types of indexers for fixed income."""

    CDI = "cdi"
    SELIC = "selic"
    IPCA = "ipca"
    IGPM = "igpm"
    PREFIXADO = "prefixado"
    OTHER = "other"


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


class PositionSource(str, Enum):
    """Source of position data."""

    CALCULATED = "calculated"  # Calculated from transactions
    STATEMENT = "statement"  # Imported from brokerage statement (source of truth)
