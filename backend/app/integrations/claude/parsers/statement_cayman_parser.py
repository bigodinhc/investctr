"""
Parser for BTG Cayman account statements (English, USD).

Handles the offshore statement structure including:
- Summary (Total Net Worth)
- Cash Accounts
- Equities (LONG and SHORT positions)
- Derivatives (Futures, Options)
- Structured Products
- Cash movements
"""

from typing import Any

from app.integrations.claude.prompts.statement_cayman import BTGCaymanStatementPrompt

from .base import BaseParser, ParsedTransaction


# Sections specific to Cayman statements
CAYMAN_REQUIRED_SECTIONS = {
    "equities": "Equities",
    "derivatives": "Derivatives",
    "transactions": "Transactions",
    "cash_movements": "Cash Movements",
}

# Sections that have focused retry prompts implemented
CAYMAN_RECOVERABLE_SECTIONS = {"equities", "derivatives"}


class CaymanStatementParser(BaseParser):
    """Parser for BTG Pactual Cayman monthly account statements (English/USD)."""

    def __init__(self):
        super().__init__(BTGCaymanStatementPrompt())

    def detect_missing_sections(self, raw_data: dict[str, Any]) -> list[str]:
        """
        Detect required sections that are missing or empty for Cayman statements.

        Args:
            raw_data: Parsed data from Claude

        Returns:
            List of section names that are missing or empty
        """
        missing = []

        for section, name in CAYMAN_REQUIRED_SECTIONS.items():
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
        Override to use Cayman-specific recoverable sections.
        """
        if section not in CAYMAN_RECOVERABLE_SECTIONS:
            return {}
        return await super().retry_for_missing_section(pdf_content, section)

    def validate_data(self, raw_data: dict[str, Any]) -> tuple[bool, str | None]:
        """Validate the parsed Cayman statement data."""
        if not isinstance(raw_data, dict):
            return False, "Response is not a valid JSON object"

        # Check for at least one data section
        has_data = any(
            [
                raw_data.get("transactions"),
                raw_data.get("cash_movements", {}).get("movements"),
                raw_data.get("equities"),
                raw_data.get("derivatives"),
                raw_data.get("structured_products"),
                raw_data.get("cash_accounts"),
            ]
        )

        if not has_data:
            return False, "No data extracted from statement"

        # Validate period if present
        period = raw_data.get("period", {})
        if period and not (period.get("start_date") or period.get("end_date")):
            return False, "Invalid period data"

        return True, None

    def extract_transactions(self, raw_data: dict[str, Any]) -> list[ParsedTransaction]:
        """Extract all transactions from parsed Cayman statement data."""
        transactions = []

        # Extract from main transactions array
        transactions.extend(self._extract_from_transactions(raw_data))

        # Extract from cash movements
        transactions.extend(self._extract_from_cash_movements(raw_data))

        return transactions

    def _extract_from_transactions(
        self, raw_data: dict[str, Any]
    ) -> list[ParsedTransaction]:
        """Extract from main transactions array."""
        transactions = []

        for txn in raw_data.get("transactions", []):
            if not isinstance(txn, dict):
                continue

            date = self.parse_date(txn.get("date"))
            if not date:
                continue

            txn_type = self._normalize_transaction_type(txn.get("type", "other"))
            ticker = txn.get("ticker", "")

            transaction = ParsedTransaction(
                date=date,
                type=txn_type,
                ticker=ticker.upper() if ticker else "",
                asset_name=txn.get("description"),
                quantity=self.parse_decimal(txn.get("quantity")),
                price=self.parse_decimal(txn.get("price")),
                total=self.parse_decimal(txn.get("total")),
                fees=self.parse_decimal(txn.get("fees")),
                notes=txn.get("notes"),
            )
            transactions.append(transaction)

        return transactions

    def _extract_from_cash_movements(
        self, raw_data: dict[str, Any]
    ) -> list[ParsedTransaction]:
        """Extract from cash movements section."""
        transactions = []
        cash_movements = raw_data.get("cash_movements", {})

        for movement in cash_movements.get("movements", []):
            if not isinstance(movement, dict):
                continue

            date = self.parse_date(movement.get("date"))
            if not date:
                continue

            txn_type = self._normalize_transaction_type(movement.get("type", "other"))
            description = movement.get("description", "")

            transaction = ParsedTransaction(
                date=date,
                type=txn_type,
                ticker="",  # Cash movements typically don't have tickers
                asset_name=None,
                quantity=None,
                price=None,
                total=self.parse_decimal(movement.get("value")),
                fees=None,
                notes=description,
            )
            transactions.append(transaction)

        return transactions

    @staticmethod
    def _normalize_transaction_type(txn_type: str) -> str:
        """Normalize transaction type to standard values for English/Cayman format."""
        if not txn_type:
            return "other"

        txn_type = txn_type.lower().strip()

        type_mapping = {
            # Buy operations
            "buy": "buy",
            "purchase": "buy",
            # Sell operations
            "sell": "sell",
            "sale": "sell",
            # Short operations
            "short": "sell",  # Short sale
            "cover": "buy",  # Cover short
            "buy_to_cover": "buy",
            # Dividends
            "dividend": "dividend",
            "div": "dividend",
            # Interest
            "interest": "interest",
            "int": "interest",
            # Fees
            "fee": "fee",
            "commission": "fee",
            # Taxes
            "tax": "tax",
            "withholding": "tax",
            # Transfers
            "transfer_in": "transfer_in",
            "wire_in": "transfer_in",
            "deposit": "transfer_in",
            "transfer_out": "transfer_out",
            "wire_out": "transfer_out",
            "withdrawal": "transfer_out",
            # Corporate actions
            "split": "split",
            "stock_split": "split",
            "merger": "other",
            "spinoff": "subscription",
        }

        return type_mapping.get(txn_type, txn_type)
