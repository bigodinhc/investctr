"""
BTG Cayman Statement prompt template for extracting data from offshore account statements.

Based on BTG Pactual Cayman "Monthly Statement" structure (English, USD):
- Summary (Total Net Worth)
- Cash Accounts
- Equities (LONG and SHORT positions)
- Derivatives (Futures)
- Structured Products (Notes, Bonds)
"""

from .base import BasePrompt


class BTGCaymanStatementPrompt(BasePrompt):
    """Prompt for parsing BTG Pactual Cayman monthly account statements (English, USD)."""

    # Version for tracking deployment
    PROMPT_VERSION = "v1.0-cayman"

    # Focused prompts for retry when sections are missing
    FOCUSED_PROMPTS = {
        "equities": """RETRY: Initial extraction missed EQUITIES section.

Look VERY CAREFULLY for sections containing:
- "EQUITIES" or "EQUITY POSITIONS"
- Stock tickers (US stocks: 1-5 letters, often followed by exchange like "NYSE")
- Tables with: Symbol, Quantity, Average Cost, Market Price, Market Value
- IMPORTANT: Look for both LONG and SHORT positions

Return ONLY this JSON (no additional text, no markdown):
{
    "equities": [
        {
            "ticker": "AAPL",
            "name": "Apple Inc",
            "quantity": 100,
            "position_type": "LONG",
            "average_cost": 150.00,
            "current_price": 175.00,
            "market_value": 17500.00,
            "currency": "USD"
        }
    ]
}

If NO equities found, return: {"equities": []}
""",
        "derivatives": """RETRY: Initial extraction missed DERIVATIVES section.

Look VERY CAREFULLY for sections containing:
- "DERIVATIVES" or "FUTURES" or "OPTIONS"
- Contract names with expiration dates
- Notional values, contract sizes
- Margin requirements

Return ONLY this JSON (no additional text, no markdown):
{
    "derivatives": [
        {
            "instrument_type": "FUTURE",
            "contract_name": "ES Mar 2024",
            "underlying": "S&P 500",
            "quantity": 1,
            "notional_value": 250000.00,
            "current_value": 5000.00,
            "maturity_date": "2024-03-15"
        }
    ]
}

If NO derivatives found, return: {"derivatives": []}
""",
    }

    def get_focused_prompt(self, sections: list[str]) -> str | None:
        """
        Return a focused prompt for extracting specific sections.

        Args:
            sections: List of section names to extract

        Returns:
            Focused prompt string or None if not available
        """
        for section in sections:
            if section in self.FOCUSED_PROMPTS:
                return self.FOCUSED_PROMPTS[section]
        return None

    @property
    def document_type(self) -> str:
        return "statement"

    @property
    def prompt_template(self) -> str:
        return """You are a financial document parser specialized in BTG Pactual Cayman (offshore) monthly statements.

**IMPORTANT: This is an ENGLISH language statement with USD amounts. Dates are in MM/DD/YYYY format.**

Analyze this BTG Pactual Cayman statement PDF and extract ALL data from the following sections:

## SECTIONS TO EXTRACT:

### 1. SUMMARY / TOTAL NET WORTH
Look for "Summary", "Account Summary", "Total Net Worth" or similar sections showing:
- Total account value (Net Worth)
- Cash balance
- Securities value
- Any category breakdown

### 2. CASH ACCOUNTS
Cash positions and movements:
- Cash balances by currency (USD, other currencies)
- Interest earned
- Deposits and withdrawals (TED, Wire transfers)
- Any cash transactions

### 3. EQUITIES (IMPORTANT - includes LONG AND SHORT)
**CRITICAL: Extract BOTH long AND short positions separately.**

For each stock position:
- Ticker symbol (e.g., "AAPL", "MSFT", "NVDA")
- Company name
- Quantity (positive for LONG, negative for SHORT or marked as SHORT)
- Position type: "LONG" or "SHORT"
- Average cost/price
- Current market price
- Market value (may be negative for shorts)
- Unrealized P&L if available

### 4. DERIVATIVES (Futures, Options)
For each derivative position:
- Instrument type (FUTURE, OPTION_CALL, OPTION_PUT)
- Contract name/description
- Underlying asset
- Quantity/contracts
- Notional value
- Current value
- Maturity/expiration date
- Strike price (for options)

### 5. STRUCTURED PRODUCTS (Notes, Bonds)
- Product name/description
- Issuer
- Notional amount
- Current value
- Maturity date
- Interest rate/coupon if applicable

### 6. TRANSACTIONS (CRITICAL - Trading transactions go in "transactions" array)
**IMPORTANT: Trading transactions are listed inside the "Cash Accounts > Transactions" table, NOT in a separate section.**

**YOU MUST extract trading transactions and put them in the "transactions" array, NOT in "cash_movements"!**

Look for these patterns in the Cash Accounts transactions table:
- `Purchase: Trade ID XXXXX - TICKER` → Extract as type "buy" in transactions array
- `Sale: Trade ID XXXXX - TICKER` → Extract as type "sell" in transactions array
- `Futures: Trade ID XXXXX - CONTRACT` → Extract as type "buy" or "sell" in transactions array
- `Dividends: Trade ID XXXXX - TICKER` → Extract as type "dividend" in transactions array

Also check the "Derivatives > Transactions" section for futures/options trades with columns:
- Trade Date, Settlement Date, Description, Trade Id, Transaction (Purchase/Sale), Quantity, Price, Notional

For each trading transaction, extract:
- **date**: Trade Date (convert to YYYY-MM-DD)
- **type**: "buy" for Purchase, "sell" for Sale, "dividend" for Dividends
- **ticker**: Extract from description (e.g., "TKA GR" from "Purchase: Trade ID 78035610 - TKA GR")
- **quantity**: Number of shares/contracts (may be in a Quantity column)
- **price**: Price per share/contract
- **total**: Total settlement amount (from Credit/Debit column)
- **fees**: Any commissions (usually 0 or included in price)

**REMEMBER**:
- Trading transactions (buy, sell, dividend) → "transactions" array
- Cash movements (wire in, wire out, interest, fees) → "cash_movements" array

## RETURN FORMAT:

**IMPORTANT: ALL fields shown below are REQUIRED in your response. If a section has no data, use an empty array [] or null as appropriate.**

```json
{
    "document_type": "statement",
    "broker": "BTG Pactual Cayman",
    "period": {
        "start_date": "YYYY-MM-DD",
        "end_date": "YYYY-MM-DD"
    },
    "account": {
        "number": "string",
        "holder_name": "string or null"
    },
    "consolidated_position": {
        "cash": 0.00,
        "equities_long": 0.00,
        "equities_short": 0.00,
        "derivatives": 0.00,
        "structured_products": 0.00,
        "total": 0.00
    },
    "cash_accounts": [
        {
            "currency": "USD",
            "balance": 0.00
        }
    ],
    "equities": [
        {
            "ticker": "AAPL",
            "name": "Apple Inc",
            "quantity": 100,
            "position_type": "LONG|SHORT",
            "average_cost": 0.00,
            "current_price": 0.00,
            "market_value": 0.00,
            "unrealized_pnl": 0.00,
            "currency": "USD"
        }
    ],
    "derivatives": [
        {
            "instrument_type": "FUTURE|OPTION_CALL|OPTION_PUT",
            "contract_name": "string",
            "underlying": "string",
            "quantity": 0,
            "strike_price": 0.00,
            "notional_value": 0.00,
            "current_value": 0.00,
            "maturity_date": "YYYY-MM-DD",
            "notes": "string or null"
        }
    ],
    "structured_products": [
        {
            "name": "string",
            "issuer": "string or null",
            "notional_amount": 0.00,
            "current_value": 0.00,
            "maturity_date": "YYYY-MM-DD or null",
            "interest_rate": 0.00,
            "currency": "USD"
        }
    ],
    "transactions": [
        {
            "date": "YYYY-MM-DD",
            "type": "buy|sell|dividend",
            "ticker": "AAPL",
            "description": "Purchase: Trade ID 12345 - AAPL",
            "quantity": 100.00,
            "price": 150.00,
            "total": 15000.00,
            "fees": 0.00,
            "currency": "USD",
            "notes": "Example: Extracted from Cash Accounts table"
        }
    ],
    "cash_movements": {
        "opening_balance": 0.00,
        "closing_balance": 0.00,
        "movements": [
            {
                "date": "YYYY-MM-DD",
                "type": "deposit|withdrawal|interest|fee|other",
                "description": "Wire transfer or interest payment",
                "value": 0.00,
                "currency": "USD"
            }
        ]
    },
    "summary": {
        "total_dividends": 0.00,
        "total_interest": 0.00,
        "total_fees": 0.00,
        "net_cash_flow": 0.00
    }
}
```

## EXTRACTION RULES:

1. **Dates**: Convert from MM/DD/YYYY to YYYY-MM-DD format. Be careful with American date format!

2. **Currency**: Default currency is USD unless explicitly stated otherwise.

3. **SHORT positions**:
   - Quantity should be positive, but position_type should be "SHORT"
   - Market value for shorts may be shown as negative (debt to return shares)
   - Common indicators: "SHORT", "SHT", negative quantity, "(SHORT)" annotation

4. **CRITICAL: transactions vs cash_movements separation**:
   - **transactions array**: Trading activity (buy, sell, dividends)
     - "Purchase: Trade ID..." → type "buy" in transactions
     - "Sale: Trade ID..." → type "sell" in transactions
     - "Futures: Trade ID..." → type "buy" or "sell" in transactions
     - "Dividends: Trade ID..." → type "dividend" in transactions
   - **cash_movements array**: Cash flow activity (deposits, withdrawals, interest, fees)
     - "Wire In", "TED In" → type "deposit" in cash_movements
     - "Wire Out", "TED Out" → type "withdrawal" in cash_movements
     - "Interest" → type "interest" in cash_movements
     - "Fee", "Commission" → type "fee" in cash_movements

5. **Transaction Types Mapping**:
   - BUY, PURCHASE → "buy"
   - SELL, SALE → "sell"
   - DIVIDEND → "dividend"
   - INTEREST → "interest"
   - FEE, COMMISSION → "fee"
   - WIRE IN, DEPOSIT, TRANSFER IN → "transfer_in"
   - WIRE OUT, WITHDRAWAL, TRANSFER OUT → "transfer_out"

6. **Values**:
   - Positive values for credits/inflows
   - Negative values for debits/outflows
   - Use 2 decimal places for USD amounts
   - Use up to 8 decimal places for quantities

7. **Tickers**:
   - US stock tickers: Uppercase, typically 1-5 letters (AAPL, MSFT, NVDA, etc.)
   - May include exchange suffix (e.g., "AAPL.US") - remove the suffix

8. **Total Net Worth Calculation**:
   - total = cash + equities_long - equities_short + derivatives + structured_products
   - For shorts: the value shown may be negative (liability)

9. **Do NOT skip any data** - extract everything visible in the document.

10. **MANDATORY fields**: equities, derivatives, cash_movements, transactions - ALWAYS include these keys (use empty arrays if no data).

""" + self.get_json_instruction()
