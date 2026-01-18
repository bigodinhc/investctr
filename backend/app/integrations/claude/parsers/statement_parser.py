"""
Parser for BTG account statements (Extrato Mensal).

Handles the rich structure extracted from BTG statements including:
- Consolidated positions
- Fixed income positions
- Stock positions
- Stock transactions
- Stock lending
- Derivatives
- Cash movements
"""

from typing import Any

from app.integrations.claude.prompts.statement import BTGStatementPrompt

from .base import BaseParser, ParsedTransaction


class StatementParser(BaseParser):
    """Parser for BTG Pactual monthly account statements."""

    def __init__(self):
        super().__init__(BTGStatementPrompt())

    def validate_data(self, raw_data: dict[str, Any]) -> tuple[bool, str | None]:
        """Validate the parsed statement data."""
        if not isinstance(raw_data, dict):
            return False, "Response is not a valid JSON object"

        # Check for at least one data section
        has_data = any(
            [
                raw_data.get("transactions"),
                raw_data.get("cash_movements", {}).get("movements"),
                raw_data.get("stock_positions"),
                raw_data.get("fixed_income_positions"),
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
        """Extract all transactions from parsed statement data."""
        transactions = []

        # Extract from main transactions array
        transactions.extend(self._extract_from_transactions(raw_data))

        # Extract from cash movements
        transactions.extend(self._extract_from_cash_movements(raw_data))

        # Extract from stock lending
        transactions.extend(self._extract_from_stock_lending(raw_data))

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
                asset_name=txn.get("asset_name"),
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
            ticker = movement.get("ticker", "")
            description = movement.get("description", "")

            # Try to extract ticker from description if not present
            if not ticker and description:
                ticker = self._extract_ticker_from_description(description)

            transaction = ParsedTransaction(
                date=date,
                type=txn_type,
                ticker=ticker.upper() if ticker else "",
                asset_name=None,
                quantity=None,
                price=None,
                total=self.parse_decimal(movement.get("value")),
                fees=None,
                notes=description,
            )
            transactions.append(transaction)

        return transactions

    def _extract_from_stock_lending(
        self, raw_data: dict[str, Any]
    ) -> list[ParsedTransaction]:
        """Extract from stock lending section."""
        transactions = []

        for lending in raw_data.get("stock_lending", []):
            if not isinstance(lending, dict):
                continue

            date = self.parse_date(lending.get("date"))
            if not date:
                continue

            txn_type = self._normalize_transaction_type(lending.get("type", "other"))
            ticker = lending.get("ticker", "")

            transaction = ParsedTransaction(
                date=date,
                type=txn_type,
                ticker=ticker.upper() if ticker else "",
                asset_name=None,
                quantity=self.parse_decimal(lending.get("quantity")),
                price=None,
                total=self.parse_decimal(lending.get("total")),
                fees=None,
                notes=f"Rate: {lending.get('rate_percent', 0)}%",
            )
            transactions.append(transaction)

        return transactions

    @staticmethod
    def _extract_ticker_from_description(description: str) -> str:
        """Try to extract ticker from description text."""
        import re

        # Common patterns: "DIVIDENDOS GGBR4", "JCP VALE3", etc.
        # B3 tickers: 4 letters + 1-2 digits (e.g., VALE3, PETR4, XPLG11)
        pattern = r"\b([A-Z]{4}\d{1,2})\b"
        match = re.search(pattern, description.upper())
        return match.group(1) if match else ""

    @staticmethod
    def _normalize_transaction_type(txn_type: str) -> str:
        """Normalize transaction type to standard values."""
        if not txn_type:
            return "other"

        txn_type = txn_type.lower().strip()

        type_mapping = {
            # Buy operations
            "compra": "buy",
            "c": "buy",
            "buy": "buy",
            # Sell operations
            "venda": "sell",
            "v": "sell",
            "sell": "sell",
            # Dividends
            "dividendo": "dividend",
            "dividendos": "dividend",
            "dividend": "dividend",
            "provento": "dividend",
            # JCP (Interest on Equity)
            "juros": "jcp",
            "jcp": "jcp",
            "jscp": "jcp",
            "juros s/capital": "jcp",
            # Interest (fixed income yield)
            "rendimento": "interest",
            "interest": "interest",
            # Fees
            "taxa": "fee",
            "tarifa": "fee",
            "fee": "fee",
            "corretagem": "fee",
            "custody_fee": "custody_fee",
            "taxa custodia": "custody_fee",
            # Taxes
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
            # Fixed income operations
            "application": "application",
            "aplicacao": "application",
            "redemption": "redemption",
            "resgate": "redemption",
            # Stock operations
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

        return type_mapping.get(txn_type, txn_type)
