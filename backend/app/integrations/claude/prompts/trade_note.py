"""
BTG Trade Note prompt template for extracting trades from B3 trade confirmations.
"""

from .base import BasePrompt


class BTGTradeNotePrompt(BasePrompt):
    """Prompt for parsing BTG Pactual B3 trade notes (notas de negociacao)."""

    @property
    def document_type(self) -> str:
        return "trade_note"

    @property
    def prompt_template(self) -> str:
        return """You are a financial document parser specialized in Brazilian B3 trade notes (Notas de Negociacao).

Analyze this BTG Pactual trade note PDF and extract ALL trade operations.

For each trade, identify:
1. **date**: Trade date in YYYY-MM-DD format
2. **settlement_date**: Settlement date (D+2 typically) in YYYY-MM-DD format
3. **type**: "buy" (Compra/C) or "sell" (Venda/V)
4. **market**: "BOVESPA", "FRACIONARIO", or "OPCOES"
5. **ticker**: Asset ticker symbol (e.g., "PETR4", "VALE3")
6. **asset_name**: Full asset specification
7. **quantity**: Number of shares traded
8. **price**: Unit price in BRL
9. **total**: Total operation value (quantity * price)
10. **observation**: Any observation code (D for day trade, etc.)

Also extract the summary section:
- **clearing_fee**: Taxa de liquidacao
- **registration_fee**: Taxa de registro
- **term_fee**: Taxa de termo (if applicable)
- **ana_fee**: Taxa ANA
- **emoluments**: Emolumentos
- **brokerage**: Corretagem
- **iss**: ISS tax
- **irrf**: IRRF withholding (for day trades or specific operations)
- **other_fees**: Any other fees
- **net_total**: Valor liquido das operacoes

Return the data in this exact JSON structure:
{
    "document_type": "trade_note",
    "broker": "BTG Pactual",
    "note_number": "string",
    "trade_date": "YYYY-MM-DD",
    "settlement_date": "YYYY-MM-DD",
    "account": {
        "number": "string or null",
        "holder_name": "string or null",
        "holder_document": "string or null"
    },
    "trades": [
        {
            "type": "buy|sell",
            "market": "BOVESPA|FRACIONARIO|OPCOES",
            "ticker": "SYMBOL",
            "asset_name": "Full specification",
            "quantity": 0,
            "price": 0.00,
            "total": 0.00,
            "observation": "string or null"
        }
    ],
    "summary": {
        "total_trades": 0.00,
        "buy_total": 0.00,
        "sell_total": 0.00
    },
    "fees": {
        "clearing_fee": 0.00,
        "registration_fee": 0.00,
        "term_fee": 0.00,
        "ana_fee": 0.00,
        "emoluments": 0.00,
        "brokerage": 0.00,
        "iss": 0.00,
        "irrf": 0.00,
        "other_fees": 0.00,
        "total_fees": 0.00
    },
    "net_value": {
        "operations": 0.00,
        "fees": 0.00,
        "net_total": 0.00
    }
}

RULES:
- Extract ALL trades from the note
- Identify C (Compra) as "buy" and V (Venda) as "sell"
- Ticker symbols should be uppercase
- If the note has multiple pages, extract from all pages
- Dates MUST be in YYYY-MM-DD format
- All monetary values should be decimals with 2 decimal places
- Positive values for buy totals, positive for sell totals
- Fees are typically shown as positive values
- net_total should match: operations total +/- fees
- For day trades (D observation), there may be IRRF withheld

""" + self.get_json_instruction()
