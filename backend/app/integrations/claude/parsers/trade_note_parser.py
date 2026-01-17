"""
Parser for BTG B3 trade notes.
"""

from typing import Any

from app.integrations.claude.prompts.trade_note import BTGTradeNotePrompt

from .base import BaseParser, ParsedTransaction


class TradeNoteParser(BaseParser):
    """Parser for BTG Pactual B3 trade notes."""

    def __init__(self):
        super().__init__(BTGTradeNotePrompt())

    def validate_data(self, raw_data: dict[str, Any]) -> tuple[bool, str | None]:
        """Validate the parsed trade note data."""
        if not isinstance(raw_data, dict):
            return False, "Response is not a valid JSON object"

        if "trades" not in raw_data:
            return False, "Missing 'trades' field"

        if not isinstance(raw_data["trades"], list):
            return False, "'trades' must be a list"

        if not raw_data.get("trade_date"):
            return False, "Missing 'trade_date' field"

        return True, None

    def extract_transactions(self, raw_data: dict[str, Any]) -> list[ParsedTransaction]:
        """Extract transactions from parsed trade note data."""
        transactions = []

        # Get common fields
        trade_date = self.parse_date(raw_data.get("trade_date"))
        settlement_date = self.parse_date(raw_data.get("settlement_date"))

        if not trade_date:
            return []  # Cannot process without trade date

        # Get fees to distribute across trades
        fees_data = raw_data.get("fees", {})
        total_fees = self.parse_decimal(fees_data.get("total_fees", 0))
        trades_list = raw_data.get("trades", [])
        num_trades = len(trades_list)

        # Calculate per-trade fees (proportional distribution)
        fee_per_trade = None
        if total_fees and num_trades > 0:
            fee_per_trade = total_fees / num_trades

        for trade in trades_list:
            if not isinstance(trade, dict):
                continue

            ticker = trade.get("ticker", "")
            if not ticker:
                continue  # Skip trades without ticker

            txn_type = trade.get("type", "buy")
            txn_type = "buy" if txn_type.lower() in ("buy", "c", "compra") else "sell"

            market = trade.get("market", "BOVESPA")

            transaction = ParsedTransaction(
                date=trade_date,
                type=txn_type,
                ticker=ticker.upper(),
                asset_name=trade.get("asset_name"),
                quantity=self.parse_decimal(trade.get("quantity")),
                price=self.parse_decimal(trade.get("price")),
                total=self.parse_decimal(trade.get("total")),
                fees=fee_per_trade,
                notes=trade.get("observation"),
                settlement_date=settlement_date,
                market=market,
            )
            transactions.append(transaction)

        return transactions
