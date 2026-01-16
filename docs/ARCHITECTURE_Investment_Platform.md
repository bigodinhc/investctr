# Arquitetura Técnica
# Plataforma de Gestão de Investimentos Pessoais

**Versão:** 1.0  
**Data:** Janeiro 2026

---

## 1. Visão Arquitetural

### 1.1 Diagrama de Alto Nível

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENTE (Browser)                              │
│                           Next.js 14 (App Router)                           │
│                         React + TypeScript + Tailwind                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ HTTPS
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              VERCEL (Edge)                                  │
│                    CDN + SSR + API Routes (BFF layer)                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ HTTPS
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RAILWAY (Backend)                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      FastAPI Application                             │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │   │
│  │  │  Auth   │ │Portfolio│ │  Risk   │ │ Parser  │ │ Market  │       │   │
│  │  │ Module  │ │ Module  │ │ Module  │ │ Module  │ │ Module  │       │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      Celery Workers                                  │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                   │   │
│  │  │ PDF Parser  │ │ Quote Sync  │ │ NAV Calc    │                   │   │
│  │  │   Worker    │ │   Worker    │ │   Worker    │                   │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────┐                                                           │
│  │    Redis    │  (Queue + Cache)                                          │
│  └─────────────┘                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
          │                    │                    │
          ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│    SUPABASE     │  │   CLAUDE API    │  │  MARKET DATA    │
│  ┌───────────┐  │  │                 │  │  ┌───────────┐  │
│  │ PostgreSQL│  │  │  PDF Parsing    │  │  │   LSEG    │  │
│  │   + RLS   │  │  │  & Extraction   │  │  │  (Prem)   │  │
│  └───────────┘  │  │                 │  │  └───────────┘  │
│  ┌───────────┐  │  └─────────────────┘  │  ┌───────────┐  │
│  │  Storage  │  │                       │  │ yfinance  │  │
│  │  (PDFs)   │  │                       │  │  (Free)   │  │
│  └───────────┘  │                       │  └───────────┘  │
│  ┌───────────┐  │                       └─────────────────┘
│  │   Auth    │  │
│  └───────────┘  │
└─────────────────┘
```

### 1.2 Princípios Arquiteturais

1. **Separação de Responsabilidades**: Frontend (apresentação), Backend (lógica), Database (persistência)
2. **Processamento Assíncrono**: Tarefas pesadas via Celery workers
3. **Cache Inteligente**: Redis para cotações e dados frequentes
4. **Segurança por Design**: RLS, autenticação em todas camadas
5. **Fallback Graceful**: Alternativas quando serviços premium indisponíveis

---

## 2. Stack Tecnológica Detalhada

### 2.1 Frontend

| Tecnologia | Versão | Propósito |
|------------|--------|-----------|
| Next.js | 14.x | Framework React com App Router |
| TypeScript | 5.x | Tipagem estática |
| TailwindCSS | 3.x | Estilização utility-first |
| shadcn/ui | latest | Componentes UI (Radix-based) |
| Recharts | 2.x | Gráficos customizáveis |
| TradingView Lightweight | 4.x | Gráficos financeiros |
| TanStack Query | 5.x | Data fetching + cache |
| Zustand | 4.x | State management |
| React Hook Form | 7.x | Formulários |
| Zod | 3.x | Validação de schemas |

### 2.2 Backend

| Tecnologia | Versão | Propósito |
|------------|--------|-----------|
| Python | 3.12 | Runtime |
| FastAPI | 0.110+ | Framework web assíncrono |
| Pydantic | 2.x | Validação e serialização |
| SQLAlchemy | 2.x | ORM |
| Alembic | 1.x | Migrations |
| Celery | 5.x | Task queue |
| Redis | 7.x | Cache + message broker |
| httpx | 0.27+ | HTTP client assíncrono |
| anthropic | latest | Claude API SDK |
| yfinance | 0.2+ | Market data gratuito |

### 2.3 Infraestrutura

| Serviço | Propósito | Tier |
|---------|-----------|------|
| Vercel | Frontend hosting | Pro |
| Railway | Backend + Redis | Pro |
| Supabase | Database + Auth + Storage | Pro |

---

## 3. Modelagem de Dados

### 3.1 Diagrama ER Simplificado

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   accounts  │       │   assets    │       │   quotes    │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id (PK)     │       │ id (PK)     │       │ id (PK)     │
│ user_id     │       │ ticker      │◄──────│ asset_id    │
│ name        │       │ name        │       │ date        │
│ type        │       │ asset_type  │       │ open        │
│ currency    │       │ currency    │       │ high        │
│ created_at  │       │ exchange    │       │ low         │
└──────┬──────┘       │ lseg_ric    │       │ close       │
       │              └──────┬──────┘       │ volume      │
       │                     │              └─────────────┘
       │                     │
       ▼                     ▼
┌─────────────┐       ┌─────────────┐
│transactions │       │  positions  │
├─────────────┤       ├─────────────┤
│ id (PK)     │       │ id (PK)     │
│ account_id  │───┐   │ account_id  │
│ asset_id    │───┼──►│ asset_id    │
│ type        │   │   │ quantity    │
│ quantity    │   │   │ avg_price   │
│ price       │   │   │ position_type│
│ fees        │   │   │ updated_at  │
│ executed_at │   │   └─────────────┘
│ document_id │   │
└─────────────┘   │   ┌─────────────┐
                  │   │ cash_flows  │
                  │   ├─────────────┤
                  └──►│ id (PK)     │
                      │ account_id  │
                      │ type        │
                      │ amount      │
                      │ currency    │
                      │ executed_at │
                      └─────────────┘

┌─────────────┐       ┌─────────────┐
│  documents  │       │fund_shares  │
├─────────────┤       ├─────────────┤
│ id (PK)     │       │ id (PK)     │
│ account_id  │       │ date        │
│ doc_type    │       │ nav         │
│ file_path   │       │ shares_out  │
│ parsed_at   │       │ share_value │
│ raw_data    │       │ created_at  │
└─────────────┘       └─────────────┘

┌──────────────────┐
│portfolio_snapshots│
├──────────────────┤
│ id (PK)          │
│ date             │
│ account_id       │
│ nav              │
│ total_cost       │
│ realized_pnl     │
│ unrealized_pnl   │
└──────────────────┘
```

### 3.2 Schema SQL Completo

```sql
-- Extensões
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enum Types
CREATE TYPE account_type AS ENUM ('btg_br', 'xp', 'btg_cayman', 'tesouro_direto');
CREATE TYPE asset_type AS ENUM ('stock', 'etf', 'fii', 'option', 'future', 'bond', 'treasury', 'crypto', 'fund');
CREATE TYPE transaction_type AS ENUM ('buy', 'sell', 'dividend', 'jcp', 'split', 'reverse_split', 'bonus', 'subscription', 'fee');
CREATE TYPE position_type AS ENUM ('long', 'short', 'day_trade');
CREATE TYPE cash_flow_type AS ENUM ('deposit', 'withdrawal');
CREATE TYPE document_type AS ENUM ('statement', 'trade_note', 'income_report', 'other');

-- Accounts
CREATE TABLE accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    type account_type NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'BRL',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Assets
CREATE TABLE assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticker VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    asset_type asset_type NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'BRL',
    exchange VARCHAR(20),
    lseg_ric VARCHAR(30),
    sector VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Quotes (Cotações)
CREATE TABLE quotes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    open DECIMAL(18,6),
    high DECIMAL(18,6),
    low DECIMAL(18,6),
    close DECIMAL(18,6) NOT NULL,
    adjusted_close DECIMAL(18,6),
    volume BIGINT,
    source VARCHAR(20) DEFAULT 'yfinance',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(asset_id, date)
);

-- Documents
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    account_id UUID REFERENCES accounts(id) ON DELETE SET NULL,
    doc_type document_type NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER,
    parsed_at TIMESTAMPTZ,
    raw_extracted_data JSONB,
    parsing_status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Transactions
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE RESTRICT,
    document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    type transaction_type NOT NULL,
    quantity DECIMAL(18,8) NOT NULL,
    price DECIMAL(18,6) NOT NULL,
    total_value DECIMAL(18,2) GENERATED ALWAYS AS (quantity * price) STORED,
    fees DECIMAL(18,2) DEFAULT 0,
    currency CHAR(3) NOT NULL DEFAULT 'BRL',
    exchange_rate DECIMAL(10,6) DEFAULT 1,
    executed_at TIMESTAMPTZ NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Positions
CREATE TABLE positions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE RESTRICT,
    quantity DECIMAL(18,8) NOT NULL DEFAULT 0,
    avg_price DECIMAL(18,6) NOT NULL DEFAULT 0,
    total_cost DECIMAL(18,2) NOT NULL DEFAULT 0,
    position_type position_type NOT NULL DEFAULT 'long',
    opened_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(account_id, asset_id, position_type)
);

-- Cash Flows
CREATE TABLE cash_flows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    type cash_flow_type NOT NULL,
    amount DECIMAL(18,2) NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'BRL',
    exchange_rate DECIMAL(10,6) DEFAULT 1,
    amount_brl DECIMAL(18,2) GENERATED ALWAYS AS (amount * exchange_rate) STORED,
    executed_at TIMESTAMPTZ NOT NULL,
    shares_affected DECIMAL(18,8),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Fund Shares (Sistema de Cotas)
CREATE TABLE fund_shares (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date DATE NOT NULL UNIQUE,
    nav DECIMAL(18,2) NOT NULL,
    shares_outstanding DECIMAL(18,8) NOT NULL,
    share_value DECIMAL(18,8) NOT NULL,
    daily_return DECIMAL(10,6),
    cumulative_return DECIMAL(10,6),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Portfolio Snapshots
CREATE TABLE portfolio_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date DATE NOT NULL,
    account_id UUID REFERENCES accounts(id) ON DELETE CASCADE,
    nav DECIMAL(18,2) NOT NULL,
    total_cost DECIMAL(18,2) NOT NULL,
    realized_pnl DECIMAL(18,2) DEFAULT 0,
    unrealized_pnl DECIMAL(18,2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(date, account_id)
);

-- Exchange Rates
CREATE TABLE exchange_rates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    from_currency CHAR(3) NOT NULL,
    to_currency CHAR(3) NOT NULL,
    date DATE NOT NULL,
    rate DECIMAL(10,6) NOT NULL,
    source VARCHAR(20) DEFAULT 'bcb',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(from_currency, to_currency, date)
);

-- Índices
CREATE INDEX idx_transactions_account ON transactions(account_id);
CREATE INDEX idx_transactions_asset ON transactions(asset_id);
CREATE INDEX idx_transactions_date ON transactions(executed_at);
CREATE INDEX idx_quotes_asset_date ON quotes(asset_id, date);
CREATE INDEX idx_positions_account ON positions(account_id);
CREATE INDEX idx_fund_shares_date ON fund_shares(date);
CREATE INDEX idx_snapshots_date ON portfolio_snapshots(date);

-- Row Level Security
ALTER TABLE accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE cash_flows ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Users can only see own accounts"
    ON accounts FOR ALL
    USING (auth.uid() = user_id);

CREATE POLICY "Users can only see own transactions"
    ON transactions FOR ALL
    USING (account_id IN (SELECT id FROM accounts WHERE user_id = auth.uid()));

CREATE POLICY "Users can only see own positions"
    ON positions FOR ALL
    USING (account_id IN (SELECT id FROM accounts WHERE user_id = auth.uid()));

CREATE POLICY "Users can only see own cash flows"
    ON cash_flows FOR ALL
    USING (account_id IN (SELECT id FROM accounts WHERE user_id = auth.uid()));

CREATE POLICY "Users can only see own documents"
    ON documents FOR ALL
    USING (auth.uid() = user_id);
```

---

## 4. Arquitetura do Backend

### 4.1 Estrutura de Diretórios

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app
│   ├── config.py               # Settings
│   ├── dependencies.py         # DI
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── router.py           # Main router
│   │   ├── v1/
│   │   │   ├── accounts.py
│   │   │   ├── assets.py
│   │   │   ├── transactions.py
│   │   │   ├── positions.py
│   │   │   ├── cash_flows.py
│   │   │   ├── documents.py
│   │   │   ├── quotes.py
│   │   │   ├── portfolio.py
│   │   │   ├── risk.py
│   │   │   └── fund_shares.py
│   │   └── deps.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py
│   │   ├── exceptions.py
│   │   └── logging.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── account.py
│   │   ├── asset.py
│   │   ├── transaction.py
│   │   ├── position.py
│   │   ├── cash_flow.py
│   │   ├── document.py
│   │   ├── quote.py
│   │   └── fund_share.py
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── account.py
│   │   ├── asset.py
│   │   ├── transaction.py
│   │   ├── position.py
│   │   ├── portfolio.py
│   │   └── risk.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── portfolio_service.py
│   │   ├── position_service.py
│   │   ├── pnl_service.py
│   │   ├── risk_service.py
│   │   ├── quota_service.py
│   │   └── market_data_service.py
│   │
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── claude/
│   │   │   ├── __init__.py
│   │   │   ├── client.py
│   │   │   └── parsers/
│   │   │       ├── btg_statement.py
│   │   │       ├── btg_trade_note.py
│   │   │       └── xp_statement.py
│   │   ├── lseg/
│   │   │   ├── __init__.py
│   │   │   └── client.py
│   │   └── yfinance/
│   │       ├── __init__.py
│   │       └── client.py
│   │
│   └── workers/
│       ├── __init__.py
│       ├── celery_app.py
│       ├── tasks/
│       │   ├── pdf_parser.py
│       │   ├── quote_sync.py
│       │   ├── nav_calculator.py
│       │   └── snapshot_generator.py
│       └── schedules.py
│
├── migrations/
│   └── versions/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── alembic.ini
├── pyproject.toml
├── Dockerfile
└── docker-compose.yml
```

### 4.2 Endpoints da API

```yaml
# Accounts
GET    /api/v1/accounts              # Lista contas
POST   /api/v1/accounts              # Cria conta
GET    /api/v1/accounts/{id}         # Detalhe conta
PUT    /api/v1/accounts/{id}         # Atualiza conta
DELETE /api/v1/accounts/{id}         # Remove conta

# Assets
GET    /api/v1/assets                # Lista ativos
POST   /api/v1/assets                # Cria ativo
GET    /api/v1/assets/{id}           # Detalhe ativo
GET    /api/v1/assets/search         # Busca ativo

# Transactions
GET    /api/v1/transactions          # Lista transações (filtros)
POST   /api/v1/transactions          # Cria transação
GET    /api/v1/transactions/{id}     # Detalhe transação
PUT    /api/v1/transactions/{id}     # Atualiza transação
DELETE /api/v1/transactions/{id}     # Remove transação

# Positions
GET    /api/v1/positions             # Lista posições abertas
GET    /api/v1/positions/consolidated # Posições consolidadas

# Cash Flows
GET    /api/v1/cash-flows            # Lista aportes/saques
POST   /api/v1/cash-flows            # Registra aporte/saque
DELETE /api/v1/cash-flows/{id}       # Remove

# Documents
GET    /api/v1/documents             # Lista documentos
POST   /api/v1/documents/upload      # Upload PDF
GET    /api/v1/documents/{id}        # Detalhe documento
POST   /api/v1/documents/{id}/parse  # Processa documento
POST   /api/v1/documents/{id}/commit # Confirma importação

# Quotes
GET    /api/v1/quotes/{asset_id}     # Histórico de preços
POST   /api/v1/quotes/sync           # Força sincronização

# Portfolio
GET    /api/v1/portfolio/summary     # Resumo consolidado
GET    /api/v1/portfolio/performance # Performance por período
GET    /api/v1/portfolio/allocation  # Alocação por classe

# Fund Shares
GET    /api/v1/fund/shares           # Histórico de cotas
GET    /api/v1/fund/nav              # NAV atual
GET    /api/v1/fund/performance      # Rentabilidade

# Risk
GET    /api/v1/risk/var              # Value at Risk
GET    /api/v1/risk/metrics          # Sharpe, Sortino, etc
GET    /api/v1/risk/correlation      # Matriz de correlação
GET    /api/v1/risk/exposure         # Exposição por categoria
```

### 4.3 Celery Tasks

```python
# Tarefas agendadas
CELERYBEAT_SCHEDULE = {
    'sync-quotes-morning': {
        'task': 'workers.tasks.quote_sync.sync_all_quotes',
        'schedule': crontab(hour=10, minute=30),  # 10:30 BRT
    },
    'sync-quotes-afternoon': {
        'task': 'workers.tasks.quote_sync.sync_all_quotes',
        'schedule': crontab(hour=14, minute=0),   # 14:00 BRT
    },
    'sync-quotes-close': {
        'task': 'workers.tasks.quote_sync.sync_all_quotes',
        'schedule': crontab(hour=18, minute=30),  # 18:30 BRT
    },
    'calculate-daily-nav': {
        'task': 'workers.tasks.nav_calculator.calculate_nav',
        'schedule': crontab(hour=19, minute=0),   # 19:00 BRT
    },
    'generate-daily-snapshot': {
        'task': 'workers.tasks.snapshot_generator.generate_snapshot',
        'schedule': crontab(hour=19, minute=30),  # 19:30 BRT
    },
    'sync-exchange-rates': {
        'task': 'workers.tasks.quote_sync.sync_exchange_rates',
        'schedule': crontab(hour=18, minute=0),   # 18:00 BRT
    },
}
```

---

## 5. Arquitetura do Frontend

### 5.1 Estrutura de Diretórios

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── globals.css
│   │   ├── (auth)/
│   │   │   ├── login/page.tsx
│   │   │   └── layout.tsx
│   │   ├── (dashboard)/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx              # Dashboard home
│   │   │   ├── positions/page.tsx
│   │   │   ├── transactions/page.tsx
│   │   │   ├── documents/
│   │   │   │   ├── page.tsx
│   │   │   │   └── [id]/page.tsx
│   │   │   ├── cash-flows/page.tsx
│   │   │   ├── performance/page.tsx
│   │   │   ├── risk/page.tsx
│   │   │   └── settings/page.tsx
│   │   └── api/                      # Route handlers (BFF)
│   │       └── [...path]/route.ts
│   │
│   ├── components/
│   │   ├── ui/                       # shadcn components
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Header.tsx
│   │   │   └── Footer.tsx
│   │   ├── dashboard/
│   │   │   ├── SummaryCards.tsx
│   │   │   ├── EquityChart.tsx
│   │   │   ├── AllocationChart.tsx
│   │   │   └── PositionsTable.tsx
│   │   ├── documents/
│   │   │   ├── UploadZone.tsx
│   │   │   ├── ParsePreview.tsx
│   │   │   └── TransactionDiff.tsx
│   │   ├── charts/
│   │   │   ├── LineChart.tsx
│   │   │   ├── DonutChart.tsx
│   │   │   ├── BarChart.tsx
│   │   │   └── TradingViewChart.tsx
│   │   └── shared/
│   │       ├── DataTable.tsx
│   │       ├── LoadingSpinner.tsx
│   │       └── ErrorBoundary.tsx
│   │
│   ├── hooks/
│   │   ├── usePortfolio.ts
│   │   ├── usePositions.ts
│   │   ├── useTransactions.ts
│   │   ├── useQuotes.ts
│   │   └── useRisk.ts
│   │
│   ├── lib/
│   │   ├── api.ts                    # API client
│   │   ├── supabase.ts               # Supabase client
│   │   ├── utils.ts
│   │   └── formatters.ts
│   │
│   ├── stores/
│   │   ├── authStore.ts
│   │   └── portfolioStore.ts
│   │
│   └── types/
│       ├── account.ts
│       ├── asset.ts
│       ├── transaction.ts
│       ├── position.ts
│       └── portfolio.ts
│
├── public/
├── next.config.js
├── tailwind.config.js
├── tsconfig.json
└── package.json
```

### 5.2 Componentes Principais

```tsx
// Dashboard Layout
┌─────────────────────────────────────────────────────────────┐
│  Sidebar  │              Main Content                       │
│  ───────  │  ┌─────────────────────────────────────────┐   │
│  Dashboard│  │            Header + Breadcrumbs          │   │
│  Posições │  ├─────────────────────────────────────────┤   │
│  Transaç. │  │                                         │   │
│  Docs     │  │            Page Content                 │   │
│  CashFlow │  │                                         │   │
│  Perform. │  │                                         │   │
│  Risco    │  │                                         │   │
│  Config   │  │                                         │   │
│           │  └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Fluxo de Parsing de PDFs

### 6.1 Arquitetura do Parser

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Upload  │───▶│ Supabase │───▶│  Celery  │───▶│  Claude  │
│   PDF    │    │ Storage  │    │  Worker  │    │   API    │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
                                      │               │
                                      │               ▼
                                      │         ┌──────────┐
                                      │         │ Extracted│
                                      │         │   JSON   │
                                      │         └────┬─────┘
                                      │              │
                                      ▼              ▼
                               ┌─────────────────────────┐
                               │   Validation + Review   │
                               │      (Frontend UI)      │
                               └───────────┬─────────────┘
                                           │ Confirm
                                           ▼
                               ┌─────────────────────────┐
                               │   Persist to Database   │
                               │   Recalculate Positions │
                               └─────────────────────────┘
```

### 6.2 Prompt Template para Claude

```python
PARSE_BTG_STATEMENT_PROMPT = """
Você é um especialista em extração de dados de extratos bancários.
Analise o extrato BTG Pactual anexado e extraia TODAS as transações.

Para cada transação, identifique:
- data (formato: YYYY-MM-DD)
- tipo (buy, sell, dividend, jcp, fee)
- ticker (código do ativo)
- quantidade (número)
- preço unitário (número)
- valor total (número)
- taxas/custos (número, se houver)

Retorne APENAS um JSON válido no seguinte formato:
{
  "document_type": "btg_statement",
  "period": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"},
  "account_number": "string",
  "transactions": [
    {
      "date": "YYYY-MM-DD",
      "type": "buy|sell|dividend|jcp|fee",
      "ticker": "VALE3",
      "quantity": 100,
      "price": 58.50,
      "total": 5850.00,
      "fees": 4.90,
      "notes": "string opcional"
    }
  ],
  "summary": {
    "total_buys": 0.00,
    "total_sells": 0.00,
    "total_dividends": 0.00,
    "total_fees": 0.00
  }
}

IMPORTANTE:
- Extraia TODAS as transações, não apenas um resumo
- Valores monetários sem símbolo de moeda
- Datas no formato ISO (YYYY-MM-DD)
- Se não conseguir identificar algum campo, use null
"""
```

---

## 7. Sistema de Cotas

### 7.1 Fórmulas

```python
# NAV (Net Asset Value)
NAV = sum(position.quantity * position.current_price for position in positions) + cash_balance

# Valor da Cota
share_value = NAV / shares_outstanding

# Emissão de Cotas (Aporte)
new_shares = deposit_amount / previous_day_share_value
shares_outstanding += new_shares

# Resgate de Cotas (Saque)
redeemed_shares = withdrawal_amount / previous_day_share_value
shares_outstanding -= redeemed_shares

# Rentabilidade
daily_return = (current_share_value / previous_share_value) - 1
cumulative_return = (current_share_value / initial_share_value) - 1
```

### 7.2 Fluxo de Cálculo Diário

```
18:30 - Sincronização de cotações de fechamento
        ↓
19:00 - Cálculo do NAV
        ↓
      - Processamento de aportes/saques do dia
        ↓
      - Emissão/resgate de cotas
        ↓
      - Cálculo do valor da cota
        ↓
      - Cálculo de rentabilidade
        ↓
19:30 - Geração de snapshot diário
        ↓
      - Atualização de métricas de risco
```

---

## 8. Cálculos de Risco

### 8.1 Value at Risk (VaR)

```python
# VaR Paramétrico (95% e 99%)
import numpy as np
from scipy import stats

def calculate_var_parametric(returns: np.array, confidence: float = 0.95) -> float:
    """
    VaR paramétrico assumindo distribuição normal
    """
    mean = np.mean(returns)
    std = np.std(returns)
    var = stats.norm.ppf(1 - confidence, mean, std)
    return abs(var)

# VaR Histórico
def calculate_var_historical(returns: np.array, confidence: float = 0.95) -> float:
    """
    VaR histórico baseado em percentis
    """
    var = np.percentile(returns, (1 - confidence) * 100)
    return abs(var)
```

### 8.2 Métricas de Performance

```python
def calculate_sharpe_ratio(returns: np.array, risk_free_rate: float = 0.0) -> float:
    """
    Sharpe Ratio = (Rp - Rf) / σp
    """
    excess_returns = returns - risk_free_rate / 252  # Ajustado para diário
    return np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)

def calculate_sortino_ratio(returns: np.array, risk_free_rate: float = 0.0) -> float:
    """
    Sortino Ratio = (Rp - Rf) / σd (downside deviation)
    """
    excess_returns = returns - risk_free_rate / 252
    downside_returns = returns[returns < 0]
    downside_std = np.std(downside_returns)
    return np.mean(excess_returns) / downside_std * np.sqrt(252)

def calculate_max_drawdown(nav_series: np.array) -> tuple[float, int]:
    """
    Maximum Drawdown e duração
    """
    peak = np.maximum.accumulate(nav_series)
    drawdown = (nav_series - peak) / peak
    max_dd = np.min(drawdown)
    
    # Duração do drawdown
    in_drawdown = drawdown < 0
    # ... cálculo de duração
    
    return max_dd, duration_days

def calculate_beta(portfolio_returns: np.array, benchmark_returns: np.array) -> float:
    """
    Beta = Cov(Rp, Rm) / Var(Rm)
    """
    covariance = np.cov(portfolio_returns, benchmark_returns)[0][1]
    variance = np.var(benchmark_returns)
    return covariance / variance
```

---

## 9. Infraestrutura e Deploy

### 9.1 Diagrama de Deploy

```
┌─────────────────────────────────────────────────────────────┐
│                         VERCEL                              │
│  ┌───────────────────────────────────────────────────────┐ │
│  │                   Next.js App                         │ │
│  │  - SSR / Static Pages                                 │ │
│  │  - API Routes (proxy to backend)                      │ │
│  │  - Edge Functions                                     │ │
│  └───────────────────────────────────────────────────────┘ │
│                      vercel.json                           │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ HTTPS
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                        RAILWAY                              │
│  ┌─────────────────────┐  ┌─────────────────────┐          │
│  │   FastAPI Service   │  │   Celery Worker     │          │
│  │   (api.domain.com)  │  │   (background)      │          │
│  │                     │  │                     │          │
│  │   - REST API        │  │   - PDF parsing     │          │
│  │   - Auth middleware │  │   - Quote sync      │          │
│  │   - Business logic  │  │   - NAV calc        │          │
│  └─────────────────────┘  └─────────────────────┘          │
│                                                             │
│  ┌─────────────────────┐  ┌─────────────────────┐          │
│  │   Celery Beat       │  │      Redis          │          │
│  │   (scheduler)       │  │   (cache + queue)   │          │
│  └─────────────────────┘  └─────────────────────┘          │
│                                                             │
│  railway.toml / Procfile                                   │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ Connection pooling
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                       SUPABASE                              │
│  ┌─────────────────────┐  ┌─────────────────────┐          │
│  │    PostgreSQL       │  │      Storage        │          │
│  │    + RLS            │  │   (PDFs bucket)     │          │
│  └─────────────────────┘  └─────────────────────┘          │
│                                                             │
│  ┌─────────────────────┐                                   │
│  │       Auth          │                                   │
│  │   (JWT tokens)      │                                   │
│  └─────────────────────┘                                   │
└─────────────────────────────────────────────────────────────┘
```

### 9.2 Variáveis de Ambiente

```bash
# Backend (.env)
DATABASE_URL=postgresql://...
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=xxx
REDIS_URL=redis://...
ANTHROPIC_API_KEY=xxx
LSEG_APP_KEY=xxx
LSEG_USERNAME=xxx
LSEG_PASSWORD=xxx
JWT_SECRET=xxx
ENVIRONMENT=production

# Frontend (.env.local)
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=xxx
NEXT_PUBLIC_API_URL=https://api.domain.com
```

### 9.3 CI/CD Pipeline

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to Railway
        uses: railwayapp/railway-action@v1
        with:
          service: backend
          token: ${{ secrets.RAILWAY_TOKEN }}

  deploy-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          vercel-args: '--prod'
```

---

## 10. Segurança

### 10.1 Camadas de Segurança

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND                             │
│  - HTTPS obrigatório                                    │
│  - CSP headers                                          │
│  - Sanitização de inputs                                │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    BACKEND                              │
│  - JWT validation (Supabase)                            │
│  - Rate limiting                                        │
│  - Input validation (Pydantic)                          │
│  - SQL injection prevention (SQLAlchemy)                │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   DATABASE                              │
│  - Row Level Security (RLS)                             │
│  - Encrypted at rest                                    │
│  - Connection via SSL                                   │
│  - Service role key only in backend                     │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   STORAGE                               │
│  - Private bucket (no public access)                    │
│  - Signed URLs for download                             │
│  - RLS policies                                         │
└─────────────────────────────────────────────────────────┘
```

### 10.2 Checklist de Segurança

- [ ] Todas as rotas autenticadas
- [ ] RLS habilitado em todas tabelas sensíveis
- [ ] Secrets em variáveis de ambiente
- [ ] CORS configurado corretamente
- [ ] Rate limiting implementado
- [ ] Logs de auditoria
- [ ] Backup automatizado
- [ ] HTTPS em todos endpoints

---

## 11. Monitoramento e Observabilidade

### 11.1 Stack de Monitoramento

| Ferramenta | Propósito |
|------------|-----------|
| Railway Metrics | Infra monitoring |
| Vercel Analytics | Frontend performance |
| Supabase Dashboard | DB metrics |
| Sentry | Error tracking |
| (opcional) Grafana | Custom dashboards |

### 11.2 Logs Estruturados

```python
import structlog

logger = structlog.get_logger()

# Exemplo de uso
logger.info(
    "pdf_parsed",
    document_id=doc.id,
    transactions_count=len(transactions),
    duration_ms=elapsed_time
)
```

---

## 12. Considerações Futuras

### 12.1 Escalabilidade

- Sharding de quotes por ano (se volume crescer)
- Read replicas para queries pesadas
- CDN para assets estáticos

### 12.2 Features Futuras

- Integração com APIs de corretoras (quando disponíveis)
- Módulo tributário
- Mobile app (React Native)
- Multi-tenancy

---

*Documento de arquitetura v1.0 - Janeiro 2026*
