"""
Base parser class for document parsing.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.core.logging import get_logger
from app.integrations.claude.client import parse_pdf_with_claude
from app.integrations.claude.prompts.base import BasePrompt

logger = get_logger(__name__)


@dataclass
class ParsedTransaction:
    """Represents a parsed transaction from a document."""

    date: str
    type: str
    ticker: str
    asset_name: str | None = None
    quantity: Decimal | None = None
    price: Decimal | None = None
    total: Decimal | None = None
    fees: Decimal | None = None
    notes: str | None = None
    settlement_date: str | None = None
    market: str | None = None


@dataclass
class ParseResult:
    """Result of document parsing."""

    success: bool
    document_type: str
    raw_data: dict[str, Any]
    transactions: list[ParsedTransaction] = field(default_factory=list)
    error: str | None = None
    parsed_at: datetime = field(default_factory=datetime.utcnow)
    _transaction_count: int | None = field(default=None, repr=False)

    @property
    def transaction_count(self) -> int:
        """Return transaction count. Uses override if set, otherwise counts transactions list."""
        if self._transaction_count is not None:
            return self._transaction_count
        return len(self.transactions)


class BaseParser(ABC):
    """Abstract base class for document parsers."""

    def __init__(self, prompt: BasePrompt):
        self.prompt = prompt

    @abstractmethod
    def extract_transactions(self, raw_data: dict[str, Any]) -> list[ParsedTransaction]:
        """Extract transactions from raw parsed data."""
        pass

    @abstractmethod
    def validate_data(self, raw_data: dict[str, Any]) -> tuple[bool, str | None]:
        """
        Validate the parsed data structure.

        Returns:
            Tuple of (is_valid, error_message)
        """
        pass

    async def parse(self, pdf_content: bytes) -> ParseResult:
        """
        Parse a PDF document.

        Args:
            pdf_content: PDF file content as bytes

        Returns:
            ParseResult with extracted data and transactions
        """
        logger.info(
            "parser_start",
            document_type=self.prompt.document_type,
            pdf_size=len(pdf_content),
        )

        try:
            # Call Claude API
            raw_data = await parse_pdf_with_claude(
                pdf_content=pdf_content,
                prompt=self.prompt.get_prompt(),
            )

            # Validate structure
            is_valid, error = self.validate_data(raw_data)
            if not is_valid:
                logger.warning(
                    "parser_validation_failed",
                    document_type=self.prompt.document_type,
                    error=error,
                )
                return ParseResult(
                    success=False,
                    document_type=self.prompt.document_type,
                    raw_data=raw_data,
                    error=f"Validation failed: {error}",
                )

            # Extract transactions
            transactions = self.extract_transactions(raw_data)

            logger.info(
                "parser_success",
                document_type=self.prompt.document_type,
                transaction_count=len(transactions),
            )

            return ParseResult(
                success=True,
                document_type=self.prompt.document_type,
                raw_data=raw_data,
                transactions=transactions,
            )

        except Exception as e:
            logger.error(
                "parser_error",
                document_type=self.prompt.document_type,
                error=str(e),
            )
            return ParseResult(
                success=False,
                document_type=self.prompt.document_type,
                raw_data={},
                error=str(e),
            )

    @staticmethod
    def parse_decimal(value: Any) -> Decimal | None:
        """Safely parse a value to Decimal."""
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except Exception:
            return None

    @staticmethod
    def parse_date(value: Any) -> str | None:
        """Validate and return a date string in YYYY-MM-DD format."""
        if not value:
            return None
        try:
            # Validate format
            datetime.strptime(str(value), "%Y-%m-%d")
            return str(value)
        except ValueError:
            return None
