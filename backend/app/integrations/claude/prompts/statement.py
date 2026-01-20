"""
BTG Statement prompt template for extracting transactions from account statements.

Based on real BTG Pactual "Extrato Mensal" structure with sections:
- Posição Consolidada (summary)
- Posição em Renda Fixa (CDB, LFT, LCA, LCI)
- Posição - Ações (stock positions)
- Transações - Ações (stock transactions)
- Transações - Aluguel (stock lending)
- Posição - Derivativos (NDF, options)
- Movimentação - Conta Corrente (cash movements)
"""

from .base import BasePrompt


class BTGStatementPrompt(BasePrompt):
    """Prompt for parsing BTG Pactual monthly account statements (Extrato Mensal)."""

    @property
    def document_type(self) -> str:
        return "statement"

    @property
    def prompt_template(self) -> str:
        return """You are a financial document parser specialized in Brazilian BTG Pactual monthly statements (Extrato Mensal).

**IMPORTANT: This statement likely contains FUNDOS DE INVESTIMENTO (mutual funds) which represent a significant portion of the portfolio value. You MUST extract the investment_funds array if any funds are present. Look for sections titled "FUNDO DE INVESTIMENTO" or tables containing fund names with "FI", "FIC", "RF" in the name and CNPJ numbers.**

Analyze this BTG Pactual statement PDF and extract ALL data from the following sections:

## SECTIONS TO EXTRACT:

### 1. POSIÇÃO CONSOLIDADA (Summary)
Total values per market: Renda Fixa, Renda Variável, Derivativos, Conta Corrente

### 2. FUNDO DE INVESTIMENTO / FUNDOS DE INVESTIMENTO (Investment Fund Positions)
**CRITICAL: This section MUST be extracted. Look for any section containing fund names like:**
- "BTG PACTUAL CRED CORP", "BTG PACTUAL YIELD", "BTG PACTUAL DIGITAL"
- Fund names containing: "FI", "FIC", "RF", "MULTIMERCADO", "ACOES"
- Any fund with CNPJ format XX.XXX.XXX/XXXX-XX

The section may be titled:
- "FUNDO DE INVESTIMENTO"
- "FUNDOS DE INVESTIMENTO"
- "POSIÇÃO EM FUNDOS"
- Or appear in a table with fund names and CNPJs

For each mutual fund, extract:
- Fund name (e.g., "BTG PACTUAL YIELD DI FI RF REF CRED PRIV")
- CNPJ of the fund (e.g., "00.840.011/0001-80")
- Quota quantity (quantidade de cotas) - may have many decimal places
- Quota price (valor da cota)
- Gross balance (saldo bruto)
- IR provision (provisão de IR) - tax provision
- Net balance (saldo líquido) - this is gross minus IR
- Performance percentage if available (rentabilidade)

### 3. POSIÇÃO EM RENDA FIXA (Fixed Income Positions)
For CDB, LFT, LCA, LCI, etc:
- Asset name (e.g., "CDB BTG Pactual S.A.")
- Indexer and rate (e.g., "104% CDI", "100% SELIC")
- Quantity
- Unit price (PU)
- Total position value
- Maturity date if available

### 4. POSIÇÃO - AÇÕES (Stock Positions)
End-of-period stock positions:
- Ticker (e.g., "USIM5", "VALE3")
- Quantity
- Average price
- Current price
- Total position value

### 5. TRANSAÇÕES - AÇÕES (Stock Transactions)
All stock operations during the period. Look for:
- COMPRA (buy)
- VENDA (sell)
- SALDO ANTERIOR (opening balance - extract as position)
- SALDO FINAL (closing balance - extract as position)
Fields: date, ticker, quantity, price, brokerage fee (corretagem), total

### 6. TRANSAÇÕES - ALUGUEL (Stock Lending)
- EMPRESTIMO (lending out shares)
- LIQUIDACAO EMPRESTIMO (loan return/settlement)
Fields: date, ticker, quantity, rate, total

### 7. POSIÇÃO - DERIVATIVOS (Derivatives)
NDF, options, futures positions:
- Instrument type
- Underlying asset
- Notional value
- Maturity
- Current value

### 8. MOVIMENTAÇÃO - CONTA CORRENTE (Cash Account Movements)
ALL cash movements including:
- DIVIDENDOS (dividends)
- JUROS S/CAPITAL or JCP (interest on equity)
- RENDIMENTO (yield from fixed income)
- IOF (tax)
- LIQ BOLSA / LIQ. BOLSA (stock settlement)
- TED/DOC transfers
- APLICACAO / RESGATE (fixed income application/redemption)
- CORRETAGEM (brokerage fees)
- TAXA DE CUSTODIA (custody fee)

## RETURN FORMAT:

```json
{
    "document_type": "statement",
    "broker": "BTG Pactual",
    "period": {
        "start_date": "YYYY-MM-DD",
        "end_date": "YYYY-MM-DD"
    },
    "account": {
        "number": "string",
        "holder_name": "string or null"
    },
    "consolidated_position": {
        "renda_fixa": 0.00,
        "fundos_investimento": 0.00,
        "renda_variavel": 0.00,
        "derivativos": 0.00,
        "conta_corrente": 0.00,
        "total": 0.00
    },
    "investment_funds": [
        {
            "fund_name": "BTG PACTUAL CRED CORP I FIC FI RF CP LP",
            "cnpj": "14.171.644/0001-57",
            "quota_quantity": 99.123456,
            "quota_price": 10500.123456,
            "gross_balance": 1040000.00,
            "ir_provision": 2500.00,
            "net_balance": 1037500.00,
            "performance_pct": 1.05
        },
        {
            "fund_name": "BTG PACTUAL YIELD DI FI RF REF CRED PRIV",
            "cnpj": "00.840.011/0001-80",
            "quota_quantity": 120.654321,
            "quota_price": 9650.789012,
            "gross_balance": 1165000.00,
            "ir_provision": 2800.00,
            "net_balance": 1162200.00,
            "performance_pct": 0.95
        }
    ],
    "fixed_income_positions": [
        {
            "asset_type": "CDB|LFT|LCA|LCI|DEBENTURE|OTHER",
            "asset_name": "string",
            "issuer": "string or null",
            "indexer": "CDI|SELIC|IPCA|PREFIXADO",
            "rate_percent": 104.00,
            "quantity": 1,
            "unit_price": 0.00,
            "total_value": 0.00,
            "maturity_date": "YYYY-MM-DD or null",
            "acquisition_date": "YYYY-MM-DD or null"
        }
    ],
    "stock_positions": [
        {
            "ticker": "VALE3",
            "quantity": 100,
            "average_price": 0.00,
            "current_price": 0.00,
            "total_value": 0.00
        }
    ],
    "transactions": [
        {
            "date": "YYYY-MM-DD",
            "type": "buy|sell|dividend|jcp|interest|fee|transfer_in|transfer_out|lending_out|lending_return|redemption|application|tax|custody_fee|settlement|other",
            "ticker": "SYMBOL or null",
            "asset_name": "string or null",
            "quantity": 0.00,
            "price": 0.00,
            "total": 0.00,
            "fees": 0.00,
            "notes": "string or null"
        }
    ],
    "stock_lending": [
        {
            "date": "YYYY-MM-DD",
            "type": "lending_out|lending_return",
            "ticker": "SYMBOL",
            "quantity": 100,
            "rate_percent": 0.00,
            "total": 0.00
        }
    ],
    "derivatives_positions": [
        {
            "instrument_type": "NDF|OPTION_CALL|OPTION_PUT|FUTURE",
            "underlying": "USD|IBOV|STOCK_TICKER",
            "notional_value": 0.00,
            "current_value": 0.00,
            "maturity_date": "YYYY-MM-DD",
            "notes": "string or null"
        }
    ],
    "cash_movements": {
        "opening_balance": 0.00,
        "closing_balance": 0.00,
        "movements": [
            {
                "date": "YYYY-MM-DD",
                "type": "dividend|jcp|interest|settlement|transfer_in|transfer_out|fee|tax|application|redemption|other",
                "description": "DIVIDENDOS GGBR4",
                "ticker": "SYMBOL or null",
                "value": 0.00
            }
        ]
    },
    "summary": {
        "total_dividends": 0.00,
        "total_jcp": 0.00,
        "total_interest": 0.00,
        "total_fees": 0.00,
        "total_taxes": 0.00,
        "net_cash_flow": 0.00
    }
}
```

## EXTRACTION RULES:

1. **Dates**: Always use YYYY-MM-DD format. Infer year from statement period if only DD/MM shown.

2. **Transaction Types Mapping**:
   - COMPRA → "buy"
   - VENDA → "sell"
   - DIVIDENDOS → "dividend"
   - JUROS S/CAPITAL, JCP → "jcp"
   - RENDIMENTO → "interest"
   - EMPRESTIMO (aluguel) → "lending_out"
   - LIQUIDACAO EMPRESTIMO → "lending_return"
   - LIQ BOLSA, LIQ. BOLSA → "settlement"
   - CORRETAGEM → "fee"
   - TAXA CUSTODIA → "custody_fee"
   - IOF → "tax"
   - TED, DOC (entrada) → "transfer_in"
   - TED, DOC (saída) → "transfer_out"
   - APLICACAO → "application"
   - RESGATE → "redemption"

3. **Values**:
   - Positive values for credits/inflows
   - Negative values for debits/outflows
   - Use 2 decimal places for BRL amounts
   - Use up to 8 decimal places for quantities

4. **Tickers**:
   - Uppercase, no spaces
   - Include full ticker (e.g., "USIM5", "GGBR4", "XPLG11")
   - For dividends/JCP, extract ticker from description (e.g., "DIVIDENDOS GGBR4" → ticker: "GGBR4")

5. **Fixed Income**:
   - Extract indexer type (CDI, SELIC, IPCA, PREFIXADO)
   - Extract rate as percentage (e.g., "104% CDI" → rate_percent: 104.00)

6. **Investment Funds (Fundos de Investimento) - CRITICAL**:
   - ALWAYS extract investment funds if present - they often represent significant portfolio value
   - Extract the FULL fund name (e.g., "BTG PACTUAL CRED CORP I FIC FI RF CP LP")
   - Extract CNPJ if available (format: XX.XXX.XXX/XXXX-XX)
   - Extract quota quantity (may have 6-8 decimal places like 99.123456)
   - Extract quota price (valor da cota)
   - Extract gross_balance (saldo bruto) and net_balance (saldo líquido)
   - IR provision is typically shown as "Provisão IR" or the difference between gross and net
   - Performance % is typically shown as monthly return (rentabilidade)
   - Look for tables with columns like: Fundo | CNPJ | Qtd Cotas | Valor Cota | Bruto | IR | Líquido

7. **Do NOT skip any data** - extract everything visible in the document, especially investment funds which are often high-value positions.

""" + self.get_json_instruction()
