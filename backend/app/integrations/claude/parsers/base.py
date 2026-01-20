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


# Sections that should always exist in BTG statements
# Used to detect and retry missing sections
REQUIRED_SECTIONS = {
    "investment_funds": "Fundos de Investimento",
    "fixed_income_positions": "Renda Fixa",
    "transactions": "Transações de Ações",
    "stock_lending": "Aluguel de Ações",
    "cash_movements": "Movimentações",
}

# Sections that have focused retry prompts implemented
# Only these sections will trigger automatic retry
RECOVERABLE_SECTIONS = {"investment_funds", "fixed_income_positions"}


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

    def detect_missing_sections(self, raw_data: dict[str, Any]) -> list[str]:
        """
        Detect required sections that are missing or empty.

        Args:
            raw_data: Parsed data from Claude

        Returns:
            List of section names that are missing or empty
        """
        missing = []

        for section, name in REQUIRED_SECTIONS.items():
            value = raw_data.get(section)
            # Consider missing if: doesn't exist, is None, or is empty list/dict
            if not value or (isinstance(value, (list, dict)) and len(value) == 0):
                # Special case for cash_movements which is a dict with movements
                if section == "cash_movements" and isinstance(value, dict):
                    movements = value.get("movements", [])
                    if movements:
                        continue  # Has movements, not missing
                missing.append(section)

        return missing

    async def retry_for_missing_section(
        self,
        pdf_content: bytes,
        section: str,
    ) -> dict[str, Any]:
        """
        Make a focused Claude call to extract a specific missing section.

        Args:
            pdf_content: PDF file content as bytes
            section: Name of the section to extract

        Returns:
            Dict containing the extracted section data
        """
        focused_prompt = self.prompt.get_focused_prompt([section])
        if not focused_prompt:
            logger.warning(
                "no_focused_prompt_available",
                section=section,
            )
            return {}

        logger.info(
            "retry_for_section_start",
            section=section,
            prompt_length=len(focused_prompt),
        )

        try:
            focused_data = await parse_pdf_with_claude(
                pdf_content=pdf_content,
                prompt=focused_prompt,
                max_tokens=8000,  # Smaller - focused extraction
                is_retry=True,
                retry_section=section,
            )
            return focused_data
        except Exception as e:
            logger.error(
                "retry_for_section_failed",
                section=section,
                error=str(e),
            )
            return {}

    def merge_results(
        self,
        original: dict[str, Any],
        focused: dict[str, Any],
        section: str,
    ) -> dict[str, Any]:
        """
        Merge focused extraction results into original data.

        Args:
            original: Original parsed data
            focused: Data from focused retry call
            section: Section name that was retried

        Returns:
            Merged data dictionary
        """
        merged = original.copy()

        # Only merge if the section was empty and now has data
        original_value = original.get(section)
        focused_value = focused.get(section)

        original_empty = not original_value or (
            isinstance(original_value, (list, dict)) and len(original_value) == 0
        )
        focused_has_data = focused_value and (
            not isinstance(focused_value, (list, dict)) or len(focused_value) > 0
        )

        if original_empty and focused_has_data:
            merged[section] = focused_value
            logger.info(
                "section_recovered",
                section=section,
                items_count=len(focused_value) if isinstance(focused_value, list) else 1,
            )
        elif original_empty:
            logger.warning(
                "section_recovery_failed",
                section=section,
                reason="focused extraction returned empty",
            )

        return merged

    async def parse(self, pdf_content: bytes) -> ParseResult:
        """
        Parse a PDF document with intelligent retry for missing sections.

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
            # 1. Initial parse - full document extraction
            raw_data = await parse_pdf_with_claude(
                pdf_content=pdf_content,
                prompt=self.prompt.get_prompt(),
            )

            # 2. Detect missing sections
            missing = self.detect_missing_sections(raw_data)

            # 3. Log all missing sections (for analysis)
            if missing:
                logger.warning(
                    "parsing_sections_missing",
                    document_type=self.prompt.document_type,
                    missing_sections=missing,
                    all_keys=list(raw_data.keys()),
                )

            # 4. Retry for recoverable sections that have focused prompts
            recoverable = [s for s in missing if s in RECOVERABLE_SECTIONS]
            if recoverable:
                logger.info(
                    "parsing_retry_needed",
                    sections_to_recover=recoverable,
                )

                recovered_sections = []
                for section in recoverable:
                    focused_data = await self.retry_for_missing_section(
                        pdf_content, section
                    )
                    if focused_data:
                        raw_data = self.merge_results(raw_data, focused_data, section)
                        # Check if section was actually recovered
                        if raw_data.get(section):
                            recovered_sections.append(section)

                logger.info(
                    "parsing_retry_completed",
                    recovered=recovered_sections,
                    still_missing=[s for s in recoverable if s not in recovered_sections],
                )

            # 5. Validate structure
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

            # 6. Extract transactions
            transactions = self.extract_transactions(raw_data)

            logger.info(
                "parser_success",
                document_type=self.prompt.document_type,
                transaction_count=len(transactions),
                sections_present=list(raw_data.keys()),
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
