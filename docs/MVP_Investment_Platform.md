# MVP - Minimum Viable Product
# Plataforma de Gestão de Investimentos Pessoais

**Versão:** 1.0  
**Data:** Janeiro 2026  
**Duração Estimada:** 6 semanas

---

## 1. Objetivo do MVP

Entregar uma versão funcional que permita:

1. **Upload e parsing** de extratos BTG (PDF → transações)
2. **Visualização** de posições consolidadas
3. **Registro** de aportes e saques
4. **Cálculo** automático de cotas e NAV
5. **Dashboard** básico com evolução patrimonial

---

## 2. Escopo do MVP

### 2.1 Incluído

| Módulo | Funcionalidades |
|--------|-----------------|
| **Autenticação** | Login via Supabase Auth (email/senha) |
| **Contas** | CRUD de contas (BTG BR apenas) |
| **Documentos** | Upload PDF + parsing via Claude |
| **Transações** | Visualização e edição manual |
| **Posições** | Cálculo automático a partir de transações |
| **Cash Flow** | Registro de aportes/saques |
| **Cotas** | NAV diário + valor da cota |
| **Market Data** | yfinance apenas (sem LSEG) |
| **Dashboard** | Cards resumo + gráfico de evolução |

### 2.2 Excluído do MVP

- XP, BTG Cayman, Tesouro Direto
- Análise de risco (VaR, Sharpe, etc.)
- Integração LSEG
- Day trade / posições short
- Múltiplas moedas
- Benchmarks comparativos
- Exportação de relatórios
- Migração de 5 anos (apenas dados novos)

---

## 3. User Stories do MVP

### Sprint 1: Foundation

| ID | User Story | Critério de Aceite |
|----|------------|-------------------|
| US01 | Como usuário, quero fazer login na plataforma | Autenticação via Supabase funcional |
| US02 | Como usuário, quero cadastrar minha conta BTG | CRUD de contas implementado |
| US03 | Como usuário, quero ver lista de ativos cadastrados | Listagem de assets funcional |

### Sprint 2: PDF Parser

| ID | User Story | Critério de Aceite |
|----|------------|-------------------|
| US04 | Como usuário, quero fazer upload de extrato BTG | Upload para Supabase Storage |
| US05 | Como usuário, quero que o sistema extraia transações do PDF | Claude API extrai dados |
| US06 | Como usuário, quero validar transações antes de importar | Preview editável exibido |
| US07 | Como usuário, quero confirmar importação | Transações salvas no banco |

### Sprint 3: Portfolio Engine

| ID | User Story | Critério de Aceite |
|----|------------|-------------------|
| US08 | Como usuário, quero ver minhas posições atuais | Posições calculadas corretamente |
| US09 | Como usuário, quero ver preço atual dos ativos | Cotações via yfinance |
| US10 | Como usuário, quero ver P&L de cada posição | P&L calculado (realizado + não-realizado) |

### Sprint 4: Sistema de Cotas

| ID | User Story | Critério de Aceite |
|----|------------|-------------------|
| US11 | Como usuário, quero registrar um aporte | Cash flow registrado |
| US12 | Como usuário, quero ver cotas emitidas no aporte | Cotas calculadas corretamente |
| US13 | Como usuário, quero ver valor da cota atual | NAV / cotas exibido |
| US14 | Como usuário, quero ver rentabilidade da cota | % de retorno calculado |

### Sprint 5: Dashboard

| ID | User Story | Critério de Aceite |
|----|------------|-------------------|
| US15 | Como usuário, quero ver resumo do patrimônio | Cards com NAV, P&L, etc. |
| US16 | Como usuário, quero ver gráfico de evolução | Chart com histórico de NAV |
| US17 | Como usuário, quero ver alocação por ativo | Donut chart funcional |

### Sprint 6: Polish & Deploy

| ID | User Story | Critério de Aceite |
|----|------------|-------------------|
| US18 | Como usuário, quero acessar via URL pública | Deploy em produção |
| US19 | Como usuário, quero dados atualizados automaticamente | Scheduler de cotações ativo |

---

## 4. Arquitetura Simplificada do MVP

```
┌───────────────────────────────────────────────────────────┐
│                 FRONTEND (Vercel)                         │
│                   Next.js 14                              │
└───────────────────────────────────────────────────────────┘
                          │
                          ▼
┌───────────────────────────────────────────────────────────┐
│                 BACKEND (Railway)                         │
│  FastAPI + Celery Worker + Redis                          │
└───────────────────────────────────────────────────────────┘
          │                    │                    │
          ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│    SUPABASE     │  │   CLAUDE API    │  │    yfinance     │
│  DB + Storage   │  │   PDF Parser    │  │     Quotes      │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

---

## 5. Schema de Banco (MVP)

```sql
-- Apenas tabelas essenciais

CREATE TABLE accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(20) DEFAULT 'btg_br',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    asset_type VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES accounts(id),
    asset_id UUID REFERENCES assets(id),
    type VARCHAR(20) NOT NULL,
    quantity DECIMAL(18,8) NOT NULL,
    price DECIMAL(18,6) NOT NULL,
    fees DECIMAL(18,2) DEFAULT 0,
    executed_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES accounts(id),
    asset_id UUID REFERENCES assets(id),
    quantity DECIMAL(18,8) NOT NULL,
    avg_price DECIMAL(18,6) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(account_id, asset_id)
);

CREATE TABLE cash_flows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES accounts(id),
    type VARCHAR(20) NOT NULL,
    amount DECIMAL(18,2) NOT NULL,
    executed_at TIMESTAMPTZ NOT NULL,
    shares_affected DECIMAL(18,8),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE quotes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID REFERENCES assets(id),
    date DATE NOT NULL,
    close DECIMAL(18,6) NOT NULL,
    UNIQUE(asset_id, date)
);

CREATE TABLE fund_shares (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL UNIQUE,
    nav DECIMAL(18,2) NOT NULL,
    shares_outstanding DECIMAL(18,8) NOT NULL,
    share_value DECIMAL(18,8) NOT NULL
);

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    raw_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 6. Endpoints da API (MVP)

```yaml
# Auth (via Supabase)
# Gerenciado diretamente pelo Supabase Auth

# Accounts
GET    /api/v1/accounts
POST   /api/v1/accounts
GET    /api/v1/accounts/{id}

# Assets
GET    /api/v1/assets
POST   /api/v1/assets

# Documents
POST   /api/v1/documents/upload
POST   /api/v1/documents/{id}/parse
POST   /api/v1/documents/{id}/commit
GET    /api/v1/documents

# Transactions
GET    /api/v1/transactions
POST   /api/v1/transactions
PUT    /api/v1/transactions/{id}
DELETE /api/v1/transactions/{id}

# Positions
GET    /api/v1/positions

# Cash Flows
GET    /api/v1/cash-flows
POST   /api/v1/cash-flows

# Portfolio
GET    /api/v1/portfolio/summary
GET    /api/v1/portfolio/history

# Fund
GET    /api/v1/fund/nav
GET    /api/v1/fund/shares
```

---

## 7. Telas do MVP

### 7.1 Wireframes

**Dashboard**
```
┌────────────────────────────────────────────────────────┐
│  [Logo]  Dashboard                     [User Menu]     │
├────────────────────────────────────────────────────────┤
│                                                        │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐         │
│  │    NAV     │ │  Cota      │ │  Rent.     │         │
│  │ R$ 150.000 │ │ R$ 1,234   │ │  +18.5%    │         │
│  └────────────┘ └────────────┘ └────────────┘         │
│                                                        │
│  ┌────────────────────────────────────────────────┐   │
│  │         Evolução do Patrimônio                 │   │
│  │         [Line Chart - 6 meses]                 │   │
│  └────────────────────────────────────────────────┘   │
│                                                        │
│  ┌────────────────────────────────────────────────┐   │
│  │  Posições Abertas                              │   │
│  │  VALE3 │ 500 │ R$ 58.40 │ +R$ 2.300 (+8.5%)  │   │
│  │  PETR4 │ 300 │ R$ 35.20 │ -R$ 450 (-4.2%)    │   │
│  └────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────┘
```

**Upload de Documentos**
```
┌────────────────────────────────────────────────────────┐
│  [Logo]  Documentos                    [User Menu]     │
├────────────────────────────────────────────────────────┤
│                                                        │
│  ┌────────────────────────────────────────────────┐   │
│  │                                                │   │
│  │     [  Arraste o PDF aqui ou clique  ]        │   │
│  │                                                │   │
│  └────────────────────────────────────────────────┘   │
│                                                        │
│  Documentos Recentes:                                  │
│  ┌────────────────────────────────────────────────┐   │
│  │  extrato_jan_2026.pdf │ Processado │ 15 txns  │   │
│  │  extrato_dez_2025.pdf │ Processado │ 23 txns  │   │
│  └────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────┘
```

**Preview de Parsing**
```
┌────────────────────────────────────────────────────────┐
│  Validar Transações Extraídas            [X Cancelar] │
├────────────────────────────────────────────────────────┤
│                                                        │
│  Documento: extrato_jan_2026.pdf                       │
│  Transações encontradas: 12                            │
│                                                        │
│  ┌────────────────────────────────────────────────┐   │
│  │ ✓ │ 05/01 │ COMPRA │ VALE3 │ 100 │ R$ 58.20  │   │
│  │ ✓ │ 08/01 │ VENDA  │ PETR4 │ 50  │ R$ 36.10  │   │
│  │ ⚠ │ 10/01 │ DIV    │ ITUB4 │ -   │ R$ 123.45 │   │
│  │   │       │        │       │     │ [Editar]  │   │
│  └────────────────────────────────────────────────┘   │
│                                                        │
│              [Cancelar]  [Confirmar Importação]       │
└────────────────────────────────────────────────────────┘
```

### 7.2 Navegação

```
Sidebar:
├── Dashboard (home)
├── Posições
├── Transações
├── Documentos
├── Aportes/Saques
└── Configurações
```

---

## 8. Cronograma do MVP

| Semana | Sprint | Entregas |
|--------|--------|----------|
| 1 | Foundation | Supabase setup, Next.js boilerplate, FastAPI estrutura, Auth |
| 2 | PDF Parser | Upload, integração Claude, preview de transações |
| 3 | Parser + Transactions | Commit de transações, CRUD manual, cálculo de posições |
| 4 | Portfolio + Quotes | Integração yfinance, mark-to-market, P&L |
| 5 | Cotas + Dashboard | NAV, cotas, cash flows, dashboard básico |
| 6 | Polish + Deploy | Testes, ajustes, deploy produção |

---

## 9. Tarefas Detalhadas

### Semana 1: Foundation

**Backend**
- [ ] Criar projeto FastAPI com estrutura de pastas
- [ ] Configurar conexão Supabase (SQLAlchemy)
- [ ] Criar modelos Account, Asset
- [ ] Implementar CRUD de accounts
- [ ] Configurar autenticação JWT (Supabase)
- [ ] Setup Celery + Redis

**Frontend**
- [ ] Criar projeto Next.js 14 (App Router)
- [ ] Configurar TailwindCSS + shadcn/ui
- [ ] Implementar layout base (Sidebar + Header)
- [ ] Configurar Supabase Auth
- [ ] Criar páginas de login/registro
- [ ] Criar página de contas

**Infra**
- [ ] Criar projeto Supabase
- [ ] Executar migrations iniciais
- [ ] Configurar Storage bucket para PDFs
- [ ] Setup Railway (backend + redis)
- [ ] Setup Vercel (frontend)

### Semana 2: PDF Parser

**Backend**
- [ ] Criar modelo Document
- [ ] Endpoint de upload (salvar em Supabase Storage)
- [ ] Integração Claude API
- [ ] Criar prompt template para BTG
- [ ] Implementar task Celery para parsing
- [ ] Endpoint para buscar status/resultado do parsing

**Frontend**
- [ ] Componente de upload (drag & drop)
- [ ] Página de documentos (listagem)
- [ ] Tela de preview de transações extraídas
- [ ] Componente de edição inline
- [ ] Indicador de progresso do parsing

### Semana 3: Transactions & Positions

**Backend**
- [ ] Criar modelos Transaction, Position
- [ ] Endpoint commit de transações (bulk insert)
- [ ] CRUD de transações
- [ ] Service de cálculo de posições
- [ ] Trigger para recalcular posições após transação
- [ ] Endpoint GET /positions

**Frontend**
- [ ] Fluxo completo de confirmação de parsing
- [ ] Página de transações (tabela + filtros)
- [ ] Modal de edição de transação
- [ ] Página de posições

### Semana 4: Quotes & Mark-to-Market

**Backend**
- [ ] Criar modelo Quote
- [ ] Integração yfinance
- [ ] Task Celery para sync de cotações
- [ ] Scheduler (2x ao dia)
- [ ] Service de mark-to-market
- [ ] Cálculo de P&L não-realizado

**Frontend**
- [ ] Exibir preço atual nas posições
- [ ] Exibir P&L (valor + %)
- [ ] Indicador de última atualização

### Semana 5: Cotas & Dashboard

**Backend**
- [ ] Criar modelos CashFlow, FundShares
- [ ] CRUD de cash flows
- [ ] Service de cálculo de NAV
- [ ] Service de emissão/resgate de cotas
- [ ] Task Celery para NAV diário
- [ ] Endpoints de portfolio summary

**Frontend**
- [ ] Página de aportes/saques
- [ ] Formulário de registro de cash flow
- [ ] Dashboard: cards de resumo
- [ ] Dashboard: gráfico de evolução
- [ ] Dashboard: tabela de posições

### Semana 6: Polish & Deploy

**Backend**
- [ ] Testes de integração
- [ ] Error handling robusto
- [ ] Logging estruturado
- [ ] Documentação OpenAPI
- [ ] Rate limiting

**Frontend**
- [ ] Tratamento de erros (toast, fallbacks)
- [ ] Loading states
- [ ] Responsividade básica
- [ ] Testes E2E básicos

**Infra**
- [ ] CI/CD pipeline
- [ ] Variáveis de ambiente produção
- [ ] DNS customizado
- [ ] Monitoramento básico

---

## 10. Definição de Pronto (DoD)

Uma feature está pronta quando:

- [ ] Código implementado e funcionando
- [ ] Sem erros no console (front/back)
- [ ] RLS aplicado nas tabelas
- [ ] Endpoint documentado no Swagger
- [ ] Testado manualmente (happy path)
- [ ] Deploy em produção

---

## 11. Riscos do MVP

| Risco | Mitigação |
|-------|-----------|
| Formato PDF BTG muda | Prompt adaptativo + validação manual |
| yfinance instável | Cache agressivo + retry |
| Complexidade do sistema de cotas | Simplificar: cálculo apenas em T+1 |
| Escopo creep | Seguir rigorosamente o backlog |

---

## 12. Critérios de Sucesso do MVP

| Critério | Meta |
|----------|------|
| Upload + parsing funcional | 100% dos PDFs BTG testados |
| Posições corretas | Divergência < 0.1% vs extrato |
| NAV calculado | Atualização diária automática |
| Dashboard carrega | < 3 segundos |
| Sistema estável | Zero erros críticos em 1 semana |

---

## 13. Pós-MVP (Próximos Passos)

Após validação do MVP:

1. **Fase 2**: Adicionar XP + BTG Cayman
2. **Fase 3**: Integração LSEG
3. **Fase 4**: Análise de risco
4. **Fase 5**: Migração histórico 5 anos
5. **Fase 6**: Multi-moeda completo

---

*MVP Document v1.0 - Janeiro 2026*
