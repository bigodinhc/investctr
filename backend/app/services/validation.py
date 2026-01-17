"""
Validation and normalization service for parsed document data.

Validates the structure and content of JSON data extracted by Claude,
normalizes values, and ensures data quality before storing.
"""

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.core.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Pydantic Models for Validation
# =============================================================================


class PeriodData(BaseModel):
    """Statement period validation."""

    start_date: str | None = None
    end_date: str | None = None

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def validate_date(cls, v: Any) -> str | None:
        if v is None:
            return None
        return normalize_date(v)


class AccountData(BaseModel):
    """Account information validation."""

    number: str | None = None
    holder_name: str | None = None


class ConsolidatedPosition(BaseModel):
    """Consolidated position validation."""

    renda_fixa: Decimal = Decimal("0")
    renda_variavel: Decimal = Decimal("0")
    derivativos: Decimal = Decimal("0")
    conta_corrente: Decimal = Decimal("0")
    total: Decimal = Decimal("0")

    @field_validator("*", mode="before")
    @classmethod
    def validate_decimal(cls, v: Any) -> Decimal:
        return normalize_decimal(v)


class FixedIncomePosition(BaseModel):
    """Fixed income position validation."""

    asset_type: str
    asset_name: str
    issuer: str | None = None
    indexer: str | None = None
    rate_percent: Decimal | None = None
    quantity: int | None = None
    unit_price: Decimal | None = None
    total_value: Decimal | None = None
    maturity_date: str | None = None
    acquisition_date: str | None = None

    @field_validator("rate_percent", "unit_price", "total_value", mode="before")
    @classmethod
    def validate_decimal(cls, v: Any) -> Decimal | None:
        if v is None:
            return None
        return normalize_decimal(v)

    @field_validator("maturity_date", "acquisition_date", mode="before")
    @classmethod
    def validate_date(cls, v: Any) -> str | None:
        if v is None:
            return None
        return normalize_date(v)

    @field_validator("asset_type", mode="before")
    @classmethod
    def validate_asset_type(cls, v: Any) -> str:
        valid_types = {"CDB", "LFT", "LCA", "LCI", "DEBENTURE", "OTHER"}
        v_upper = str(v).upper() if v else "OTHER"
        return v_upper if v_upper in valid_types else "OTHER"


class StockPosition(BaseModel):
    """Stock position validation."""

    ticker: str
    quantity: Decimal
    average_price: Decimal | None = None
    current_price: Decimal | None = None
    total_value: Decimal | None = None

    @field_validator("ticker", mode="before")
    @classmethod
    def validate_ticker(cls, v: Any) -> str:
        return normalize_ticker(v)

    @field_validator("quantity", "average_price", "current_price", "total_value", mode="before")
    @classmethod
    def validate_decimal(cls, v: Any) -> Decimal | None:
        if v is None:
            return None
        return normalize_decimal(v)


class TransactionData(BaseModel):
    """Transaction validation."""

    date: str
    type: str
    ticker: str | None = None
    asset_name: str | None = None
    quantity: Decimal | None = None
    price: Decimal | None = None
    total: Decimal | None = None
    fees: Decimal | None = None
    notes: str | None = None

    @field_validator("date", mode="before")
    @classmethod
    def validate_date(cls, v: Any) -> str:
        result = normalize_date(v)
        if not result:
            raise ValueError(f"Invalid date: {v}")
        return result

    @field_validator("type", mode="before")
    @classmethod
    def validate_type(cls, v: Any) -> str:
        return normalize_transaction_type(str(v) if v else "other")

    @field_validator("ticker", mode="before")
    @classmethod
    def validate_ticker(cls, v: Any) -> str | None:
        if v is None:
            return None
        return normalize_ticker(v)

    @field_validator("quantity", "price", "total", "fees", mode="before")
    @classmethod
    def validate_decimal(cls, v: Any) -> Decimal | None:
        if v is None:
            return None
        return normalize_decimal(v)


class StockLending(BaseModel):
    """Stock lending transaction validation."""

    date: str
    type: str
    ticker: str
    quantity: Decimal
    rate_percent: Decimal | None = None
    total: Decimal | None = None

    @field_validator("date", mode="before")
    @classmethod
    def validate_date(cls, v: Any) -> str:
        result = normalize_date(v)
        if not result:
            raise ValueError(f"Invalid date: {v}")
        return result

    @field_validator("type", mode="before")
    @classmethod
    def validate_type(cls, v: Any) -> str:
        t = str(v).lower().strip() if v else "other"
        if t in ("lending_out", "emprestimo"):
            return "lending_out"
        elif t in ("lending_return", "liquidacao emprestimo"):
            return "lending_return"
        return t

    @field_validator("ticker", mode="before")
    @classmethod
    def validate_ticker(cls, v: Any) -> str:
        return normalize_ticker(v)

    @field_validator("quantity", "rate_percent", "total", mode="before")
    @classmethod
    def validate_decimal(cls, v: Any) -> Decimal | None:
        if v is None:
            return None
        return normalize_decimal(v)


class CashMovement(BaseModel):
    """Cash movement validation."""

    date: str
    type: str
    description: str | None = None
    ticker: str | None = None
    value: Decimal

    @field_validator("date", mode="before")
    @classmethod
    def validate_date(cls, v: Any) -> str:
        result = normalize_date(v)
        if not result:
            raise ValueError(f"Invalid date: {v}")
        return result

    @field_validator("type", mode="before")
    @classmethod
    def validate_type(cls, v: Any) -> str:
        return normalize_transaction_type(str(v) if v else "other")

    @field_validator("ticker", mode="before")
    @classmethod
    def validate_ticker(cls, v: Any) -> str | None:
        if v is None:
            return None
        return normalize_ticker(v)

    @field_validator("value", mode="before")
    @classmethod
    def validate_decimal(cls, v: Any) -> Decimal:
        return normalize_decimal(v)


class CashMovements(BaseModel):
    """Cash movements section validation."""

    opening_balance: Decimal = Decimal("0")
    closing_balance: Decimal = Decimal("0")
    movements: list[CashMovement] = Field(default_factory=list)

    @field_validator("opening_balance", "closing_balance", mode="before")
    @classmethod
    def validate_decimal(cls, v: Any) -> Decimal:
        return normalize_decimal(v)


class DerivativePosition(BaseModel):
    """Derivative position validation."""

    instrument_type: str
    underlying: str | None = None
    notional_value: Decimal | None = None
    current_value: Decimal | None = None
    maturity_date: str | None = None
    notes: str | None = None

    @field_validator("notional_value", "current_value", mode="before")
    @classmethod
    def validate_decimal(cls, v: Any) -> Decimal | None:
        if v is None:
            return None
        return normalize_decimal(v)

    @field_validator("maturity_date", mode="before")
    @classmethod
    def validate_date(cls, v: Any) -> str | None:
        if v is None:
            return None
        return normalize_date(v)


class SummaryData(BaseModel):
    """Summary data validation."""

    total_dividends: Decimal = Decimal("0")
    total_jcp: Decimal = Decimal("0")
    total_interest: Decimal = Decimal("0")
    total_fees: Decimal = Decimal("0")
    total_taxes: Decimal = Decimal("0")
    net_cash_flow: Decimal = Decimal("0")

    @field_validator("*", mode="before")
    @classmethod
    def validate_decimal(cls, v: Any) -> Decimal:
        return normalize_decimal(v)


class ParsedStatementData(BaseModel):
    """Complete parsed statement data validation."""

    document_type: str = "statement"
    broker: str = "BTG Pactual"
    period: PeriodData | None = None
    account: AccountData | None = None
    consolidated_position: ConsolidatedPosition | None = None
    fixed_income_positions: list[FixedIncomePosition] = Field(default_factory=list)
    stock_positions: list[StockPosition] = Field(default_factory=list)
    transactions: list[TransactionData] = Field(default_factory=list)
    stock_lending: list[StockLending] = Field(default_factory=list)
    derivatives_positions: list[DerivativePosition] = Field(default_factory=list)
    cash_movements: CashMovements | None = None
    summary: SummaryData | None = None


# =============================================================================
# Normalization Functions
# =============================================================================


def normalize_date(value: Any) -> str | None:
    """
    Normalize date to YYYY-MM-DD format.

    Accepts:
    - YYYY-MM-DD (returns as-is)
    - DD/MM/YYYY (Brazilian format)
    - DD-MM-YYYY
    - datetime objects
    - date objects
    """
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")

    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")

    value_str = str(value).strip()

    # Already in correct format
    if re.match(r"^\d{4}-\d{2}-\d{2}$", value_str):
        return value_str

    # Brazilian format DD/MM/YYYY
    match = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", value_str)
    if match:
        day, month, year = match.groups()
        return f"{year}-{month}-{day}"

    # Alternative DD-MM-YYYY
    match = re.match(r"^(\d{2})-(\d{2})-(\d{4})$", value_str)
    if match:
        day, month, year = match.groups()
        return f"{year}-{month}-{day}"

    # Try parsing as ISO format
    try:
        dt = datetime.fromisoformat(value_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        pass

    logger.warning("date_normalization_failed", value=value_str)
    return None


def normalize_decimal(value: Any) -> Decimal:
    """
    Normalize value to Decimal.

    Handles:
    - Numbers (int, float)
    - String numbers with . or , as decimal separator
    - Brazilian format with thousand separators (1.234,56)
    - None -> Decimal("0")
    """
    if value is None:
        return Decimal("0")

    if isinstance(value, Decimal):
        return value

    if isinstance(value, (int, float)):
        return Decimal(str(value))

    value_str = str(value).strip()

    # Empty string
    if not value_str:
        return Decimal("0")

    # Handle Brazilian format: 1.234,56 -> 1234.56
    # First, check if it has both . and , (likely Brazilian format)
    if "." in value_str and "," in value_str:
        # Brazilian: dots are thousand separators, comma is decimal
        value_str = value_str.replace(".", "").replace(",", ".")
    elif "," in value_str:
        # Comma as decimal separator (no dots)
        value_str = value_str.replace(",", ".")

    # Remove any remaining non-numeric characters except . and -
    value_str = re.sub(r"[^\d.\-]", "", value_str)

    try:
        return Decimal(value_str)
    except InvalidOperation:
        logger.warning("decimal_normalization_failed", value=value)
        return Decimal("0")


def normalize_ticker(value: Any) -> str:
    """
    Normalize ticker symbol.

    - Uppercase
    - Remove spaces
    - Keep only alphanumeric characters
    """
    if value is None:
        return ""

    ticker = str(value).upper().strip()
    ticker = re.sub(r"[^A-Z0-9]", "", ticker)
    return ticker


def normalize_transaction_type(value: str) -> str:
    """Normalize transaction type to standard values."""
    if not value:
        return "other"

    value = value.lower().strip()

    type_mapping = {
        # Buy
        "compra": "buy",
        "c": "buy",
        "buy": "buy",
        # Sell
        "venda": "sell",
        "v": "sell",
        "sell": "sell",
        # Dividends
        "dividendo": "dividend",
        "dividendos": "dividend",
        "dividend": "dividend",
        "provento": "dividend",
        # JCP
        "juros": "jcp",
        "jcp": "jcp",
        "jscp": "jcp",
        "juros s/capital": "jcp",
        # Interest
        "rendimento": "interest",
        "interest": "interest",
        # Fees
        "taxa": "fee",
        "tarifa": "fee",
        "fee": "fee",
        "corretagem": "fee",
        "custody_fee": "custody_fee",
        "taxa custodia": "custody_fee",
        # Tax
        "tax": "tax",
        "iof": "tax",
        "ir": "tax",
        "irrf": "tax",
        # Transfers
        "transfer_in": "transfer_in",
        "transferencia": "transfer_in",
        "aporte": "transfer_in",
        "ted": "transfer_in",
        "transfer_out": "transfer_out",
        "saque": "transfer_out",
        # Fixed income
        "application": "application",
        "aplicacao": "application",
        "redemption": "redemption",
        "resgate": "redemption",
        # Settlement
        "settlement": "settlement",
        "liq bolsa": "settlement",
        "liq. bolsa": "settlement",
        # Stock lending
        "lending_out": "lending_out",
        "emprestimo": "lending_out",
        "lending_return": "lending_return",
        "liquidacao emprestimo": "lending_return",
        # Corporate actions
        "desdobramento": "split",
        "grupamento": "split",
        "split": "split",
        "bonificacao": "subscription",
        "subscricao": "subscription",
        "subscription": "subscription",
    }

    return type_mapping.get(value, value)


# =============================================================================
# Main Validation Service
# =============================================================================


class ValidationService:
    """Service for validating and normalizing parsed document data."""

    def validate_statement_data(self, raw_data: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        """
        Validate and normalize statement data.

        Args:
            raw_data: Raw data extracted by Claude

        Returns:
            Tuple of (validated_data, errors)
            - validated_data: Normalized data (empty dict if validation fails)
            - errors: List of validation error messages
        """
        errors = []

        try:
            validated = ParsedStatementData.model_validate(raw_data)
            return validated.model_dump(mode="json"), errors
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
            logger.error("statement_validation_failed", error=str(e), raw_data=raw_data)
            return {}, errors

    def validate_and_count_transactions(self, raw_data: dict[str, Any]) -> tuple[int, list[str]]:
        """
        Count valid transactions in the data.

        Returns:
            Tuple of (transaction_count, warnings)
        """
        warnings = []
        count = 0

        # Count main transactions
        transactions = raw_data.get("transactions", [])
        if isinstance(transactions, list):
            count += len(transactions)

        # Count cash movements
        cash_movements = raw_data.get("cash_movements", {})
        if isinstance(cash_movements, dict):
            movements = cash_movements.get("movements", [])
            if isinstance(movements, list):
                count += len(movements)

        # Count stock lending
        stock_lending = raw_data.get("stock_lending", [])
        if isinstance(stock_lending, list):
            count += len(stock_lending)

        if count == 0:
            warnings.append("No transactions found in the parsed data")

        return count, warnings

    def extract_summary(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Extract summary statistics from parsed data."""
        summary = {
            "total_transactions": 0,
            "total_positions": 0,
            "total_dividends": Decimal("0"),
            "total_jcp": Decimal("0"),
            "total_fees": Decimal("0"),
        }

        # Count transactions
        transactions = raw_data.get("transactions", [])
        cash_movements = raw_data.get("cash_movements", {}).get("movements", [])
        stock_lending = raw_data.get("stock_lending", [])

        summary["total_transactions"] = (
            len(transactions) + len(cash_movements) + len(stock_lending)
        )

        # Count positions
        summary["total_positions"] = (
            len(raw_data.get("fixed_income_positions", []))
            + len(raw_data.get("stock_positions", []))
            + len(raw_data.get("derivatives_positions", []))
        )

        # Sum dividends and JCP from transactions
        for txn in transactions + cash_movements:
            txn_type = txn.get("type", "").lower()
            total = normalize_decimal(txn.get("total") or txn.get("value"))

            if txn_type == "dividend":
                summary["total_dividends"] += total
            elif txn_type == "jcp":
                summary["total_jcp"] += total
            elif txn_type in ("fee", "custody_fee"):
                summary["total_fees"] += abs(total)

        return {k: str(v) if isinstance(v, Decimal) else v for k, v in summary.items()}
