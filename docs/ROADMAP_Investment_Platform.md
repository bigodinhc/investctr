# Roadmap de Implementação
# Plataforma de Gestão de Investimentos

**Versão:** 1.0  
**Início:** Janeiro 2026  
**Duração MVP:** 6 semanas

---

## Legenda

```
[P] = Pode ser paralelizado com outras tarefas [P]
[S] = Sequencial (depende de tarefas anteriores)
[B] = Bloqueante (outras tarefas dependem desta)
⏱️  = Estimativa de tempo
🔗  = Dependência
```

---

## Visão Geral das Fases

```
Semana 1    Semana 2    Semana 3    Semana 4    Semana 5    Semana 6
┌─────────┬─────────┬─────────┬─────────┬─────────┬─────────┐
│ FOUND-  │   PDF   │  TRANS  │ QUOTES  │ COTAS + │ POLISH  │
│ ATION   │  PARSER │   +     │   +     │ DASH-   │    +    │
│         │         │  POS    │  MTM    │ BOARD   │ DEPLOY  │
└─────────┴─────────┴─────────┴─────────┴─────────┴─────────┘
```

---

## FASE 1: FOUNDATION (Semana 1)

### 1.1 Infraestrutura [B]

| # | Tarefa | Tipo | Tempo | Dep. | Status |
|---|--------|------|-------|------|--------|
| 1.1.1 | Criar projeto Supabase | [B] | 30min | - | ✅ |
| 1.1.2 | Configurar Auth (email/senha) | [S] | 30min | 1.1.1 | ✅ |
| 1.1.3 | Criar Storage bucket `documents` | [S] | 15min | 1.1.1 | ✅ |
| 1.1.4 | Executar SQL inicial (enums + tabelas base) | [S] | 1h | 1.1.1 | ✅ |
| 1.1.5 | Configurar RLS policies | [S] | 30min | 1.1.4 | ✅ |
| 1.1.6 | Setup projeto Railway | [P] | 30min | - | ✅ |
| 1.1.7 | Provisionar Redis no Railway | [S] | 15min | 1.1.6 | ✅ |
| 1.1.8 | Setup projeto Vercel | [P] | 15min | - | ✅ |

```
Paralelismo Fase 1.1:
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Supabase     │     │     Railway     │     │     Vercel      │
│   1.1.1 → 1.1.5 │     │   1.1.6 → 1.1.7 │     │      1.1.8      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        ▼                       ▼                       ▼
        └───────────────────────┴───────────────────────┘
                        Tudo pronto para código
```

---

### 1.2 Backend Setup [B]

| # | Tarefa | Tipo | Tempo | Dep. | Status |
|---|--------|------|-------|------|--------|
| 1.2.1 | Criar estrutura FastAPI (pastas, config) | [B] | 1h | - | ✅ |
| 1.2.2 | Configurar SQLAlchemy + conexão Supabase | [S] | 1h | 1.1.1, 1.2.1 | ✅ |
| 1.2.3 | Configurar Alembic (migrations) | [S] | 30min | 1.2.2 | ✅ |
| 1.2.4 | Middleware de Auth (JWT Supabase) | [S] | 2h | 1.1.2, 1.2.1 | ✅ |
| 1.2.5 | Setup Celery + Redis connection | [S] | 1h | 1.1.7, 1.2.1 | ✅ |
| 1.2.6 | Criar modelos: Account, Asset | [S] | 1h | 1.2.2 | ✅ |
| 1.2.7 | Criar schemas Pydantic: Account, Asset | [P] | 30min | 1.2.1 | ✅ |
| 1.2.8 | Implementar CRUD accounts | [S] | 2h | 1.2.6, 1.2.7 | ✅ |
| 1.2.9 | Implementar CRUD assets | [S] | 1h | 1.2.6, 1.2.7 | ✅ |
| 1.2.10 | Dockerfile + docker-compose.yml | [P] | 1h | 1.2.1 | ✅ |
| 1.2.11 | Deploy backend Railway (inicial) | [S] | 30min | 1.2.10 | ✅ |

```
Paralelismo Fase 1.2:
                    ┌─────────────────┐
                    │  1.2.1 FastAPI  │
                    │    estrutura    │
                    └────────┬────────┘
           ┌─────────────────┼─────────────────┐
           ▼                 ▼                 ▼
    ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
    │ 1.2.2 SQLAl │   │ 1.2.7 Pyd.  │   │ 1.2.10 Dock │
    └──────┬──────┘   └──────┬──────┘   └──────┬──────┘
           ▼                 │                 ▼
    ┌─────────────┐          │          ┌─────────────┐
    │ 1.2.6 Models│◄─────────┘          │ 1.2.11 Depl │
    └──────┬──────┘                     └─────────────┘
           ▼
    ┌─────────────┐
    │ 1.2.8/9 CRUD│
    └─────────────┘
```

---

### 1.3 Frontend Setup [B]

| # | Tarefa | Tipo | Tempo | Dep. | Status |
|---|--------|------|-------|------|--------|
| 1.3.1 | Criar projeto Next.js 14 (App Router) | [B] | 30min | - | ✅ |
| 1.3.2 | Configurar TailwindCSS | [S] | 15min | 1.3.1 | ✅ |
| 1.3.3 | Instalar + configurar shadcn/ui | [S] | 30min | 1.3.2 | ✅ |
| 1.3.4 | Configurar Supabase client | [S] | 30min | 1.1.1, 1.3.1 | ✅ |
| 1.3.5 | Criar layout base (Sidebar + Header) | [S] | 2h | 1.3.3 | ✅ |
| 1.3.6 | Implementar AuthContext + proteção de rotas | [S] | 2h | 1.3.4 | ✅ |
| 1.3.7 | Página de Login | [S] | 1h | 1.3.6 | ✅ |
| 1.3.8 | Página de Registro | [P] | 1h | 1.3.6 | ✅ |
| 1.3.9 | Configurar API client (axios/fetch) | [P] | 30min | 1.3.1 | ✅ |
| 1.3.10 | Página de Contas (CRUD) | [S] | 2h | 1.3.5, 1.2.8 | ✅ |
| 1.3.11 | Deploy frontend Vercel (inicial) | [S] | 30min | 1.1.8, 1.3.7 | ✅ |

```
Paralelismo Fase 1.3:
                    ┌─────────────────┐
                    │  1.3.1 Next.js  │
                    └────────┬────────┘
                             ▼
                    ┌─────────────────┐
                    │  1.3.2 Tailwind │
                    └────────┬────────┘
           ┌─────────────────┼─────────────────┐
           ▼                 ▼                 ▼
    ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
    │ 1.3.3 shadcn│   │ 1.3.4 Supa  │   │ 1.3.9 API   │
    └──────┬──────┘   └──────┬──────┘   └─────────────┘
           ▼                 ▼
    ┌─────────────┐   ┌─────────────┐
    │ 1.3.5 Layout│   │ 1.3.6 Auth  │
    └──────┬──────┘   └──────┬──────┘
           │          ┌──────┴──────┐
           │          ▼             ▼
           │   ┌───────────┐ ┌───────────┐
           │   │1.3.7 Login│ │1.3.8 Reg. │ [Paralelo]
           │   └───────────┘ └───────────┘
           ▼
    ┌─────────────┐
    │1.3.10 Contas│
    └─────────────┘
```

---

### Checkpoint Semana 1 ✅

```
□ Supabase operacional (DB, Auth, Storage)
□ Backend rodando no Railway
□ Frontend rodando na Vercel
□ Login/Registro funcionando
□ CRUD de Contas funcionando
□ Comunicação Front ↔ Back ↔ DB validada
```

---

## FASE 2: PDF PARSER (Semana 2)

### 2.1 Backend Parser [B]

| # | Tarefa | Tipo | Tempo | Dep. | Status |
|---|--------|------|-------|------|--------|
| 2.1.1 | Criar modelo Document | [S] | 30min | 1.2.2 | ✅ |
| 2.1.2 | Criar schema Pydantic Document | [P] | 15min | - | ✅ |
| 2.1.3 | Endpoint POST /documents/upload | [S] | 2h | 2.1.1, 1.1.3 | ✅ |
| 2.1.4 | Integração Anthropic SDK (Claude) | [B] | 1h | - | ✅ |
| 2.1.5 | Criar prompt template BTG Statement | [S] | 2h | 2.1.4 | ✅ |
| 2.1.6 | Criar prompt template BTG Trade Note | [P] | 2h | 2.1.4 | ✅ |
| 2.1.7 | Celery task: parse_document | [S] | 3h | 2.1.4, 1.2.5 | ✅ |
| 2.1.8 | Endpoint POST /documents/{id}/parse | [S] | 1h | 2.1.7 | ✅ |
| 2.1.9 | Endpoint GET /documents/{id} (status + result) | [S] | 1h | 2.1.1 | ✅ |
| 2.1.10 | Validação e normalização do JSON extraído | [S] | 2h | 2.1.7 | ✅ |

```
Paralelismo Fase 2.1:
    ┌─────────────┐               ┌─────────────┐
    │ 2.1.1 Model │               │ 2.1.4 Claude│
    └──────┬──────┘               └──────┬──────┘
           │                      ┌──────┴──────┐
           ▼                      ▼             ▼
    ┌─────────────┐        ┌───────────┐ ┌───────────┐
    │ 2.1.3 Uploa │        │2.1.5 Prom1│ │2.1.6 Prom2│ [Paralelo]
    └──────┬──────┘        └─────┬─────┘ └───────────┘
           │                     ▼
           │              ┌─────────────┐
           └─────────────▶│ 2.1.7 Task  │
                          └──────┬──────┘
                                 ▼
                          ┌─────────────┐
                          │ 2.1.8 Endpt │
                          └─────────────┘
```

---

### 2.2 Frontend Upload [S]

| # | Tarefa | Tipo | Tempo | Dep. | Status |
|---|--------|------|-------|------|--------|
| 2.2.1 | Componente UploadZone (drag & drop) | [P] | 2h | 1.3.3 | ✅ |
| 2.2.2 | Página /documents (listagem) | [S] | 2h | 2.2.1 | ✅ |
| 2.2.3 | Integração upload com API | [S] | 1h | 2.1.3, 2.2.1 | ✅ |
| 2.2.4 | Polling de status do parsing | [S] | 1h | 2.1.9 | ✅ |
| 2.2.5 | Componente ParsePreview (tabela editável) | [S] | 3h | 2.2.4 | ✅ |
| 2.2.6 | Indicador de progresso / loading | [P] | 1h | 1.3.3 | ✅ |
| 2.2.7 | Toast de sucesso/erro | [P] | 30min | 1.3.3 | ✅ |

```
Paralelismo Fase 2.2:
    ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
    │ 2.2.1 Upload│   │ 2.2.6 Load. │   │ 2.2.7 Toast │
    └──────┬──────┘   └─────────────┘   └─────────────┘
           │              [Paralelo]       [Paralelo]
           ▼
    ┌─────────────┐
    │ 2.2.2 Page  │
    └──────┬──────┘
           ▼
    ┌─────────────┐
    │ 2.2.3 Integ │
    └──────┬──────┘
           ▼
    ┌─────────────┐
    │ 2.2.5 Prevw │
    └─────────────┘
```

---

### Checkpoint Semana 2 ✅

```
□ Upload de PDF funcionando
□ Claude extraindo transações
□ Preview exibindo dados extraídos
□ Usuário consegue editar antes de confirmar
```

---

## FASE 3: TRANSACTIONS & POSITIONS (Semana 3)

### 3.1 Backend Transactions [B]

| # | Tarefa | Tipo | Tempo | Dep. | Status |
|---|--------|------|-------|------|--------|
| 3.1.1 | Criar modelo Transaction | [S] | 30min | 1.2.2 | ✅ |
| 3.1.2 | Criar modelo Position | [S] | 30min | 1.2.2 | ✅ |
| 3.1.3 | Schemas Pydantic Transaction | [P] | 30min | - | ✅ |
| 3.1.4 | Schemas Pydantic Position | [P] | 30min | - | ✅ |
| 3.1.5 | Endpoint POST /documents/{id}/commit | [S] | 2h | 3.1.1, 2.1.10 | ✅ |
| 3.1.6 | Service: calculate_positions() | [B] | 3h | 3.1.1, 3.1.2 | ✅ |
| 3.1.7 | Trigger recálculo após insert/update/delete txn | [S] | 1h | 3.1.6 | ✅ |
| 3.1.8 | CRUD endpoints /transactions | [S] | 2h | 3.1.1 | ✅ |
| 3.1.9 | Endpoint GET /positions | [S] | 1h | 3.1.2, 3.1.6 | ✅ |
| 3.1.10 | Endpoint GET /positions/consolidated | [S] | 1h | 3.1.9 | ✅ |

```
Paralelismo Fase 3.1:
    ┌─────────────┐   ┌─────────────┐
    │ 3.1.1 TxnMod│   │ 3.1.2 PosMod│
    └──────┬──────┘   └──────┬──────┘
           │                 │
           ▼                 ▼
    ┌─────────────┐   ┌─────────────┐
    │ 3.1.3 TxnSch│   │ 3.1.4 PosSch│  [Paralelo]
    └──────┬──────┘   └──────┬──────┘
           └────────┬────────┘
                    ▼
             ┌─────────────┐
             │ 3.1.6 Calc  │
             └──────┬──────┘
                    │
           ┌────────┴────────┐
           ▼                 ▼
    ┌─────────────┐   ┌─────────────┐
    │ 3.1.5 Commit│   │ 3.1.8 CRUD  │  [Paralelo]
    └─────────────┘   └─────────────┘
```

---

### 3.2 Frontend Transactions [S]

| # | Tarefa | Tipo | Tempo | Dep. | Status |
|---|--------|------|-------|------|--------|
| 3.2.1 | Botão "Confirmar Importação" no Preview | [S] | 1h | 2.2.5, 3.1.5 | ✅ |
| 3.2.2 | Página /transactions (DataTable) | [S] | 3h | 3.1.8 | ✅ |
| 3.2.3 | Filtros: período, conta, ativo | [S] | 2h | 3.2.2 | ✅ |
| 3.2.4 | Modal de edição de transação | [S] | 2h | 3.2.2 | ✅ |
| 3.2.5 | Página /positions | [S] | 2h | 3.1.9 | ✅ |
| 3.2.6 | Card de resumo por posição | [S] | 1h | 3.2.5 | ✅ |

---

### Checkpoint Semana 3 ✅

```
□ Fluxo completo: Upload → Parse → Confirm → Salvar
□ Transações persistidas no banco
□ Posições calculadas automaticamente
□ CRUD manual de transações funcionando
□ Tela de posições exibindo dados
```

---

## FASE 4: QUOTES & MARK-TO-MARKET (Semana 4)

### 4.1 Backend Quotes [B]

| # | Tarefa | Tipo | Tempo | Dep. | Status |
|---|--------|------|-------|------|--------|
| 4.1.1 | Criar modelo Quote | [S] | 30min | 1.2.2 | ✅ |
| 4.1.2 | Integração yfinance (client) | [B] | 2h | - | ✅ |
| 4.1.3 | Service: fetch_quotes(tickers) | [S] | 2h | 4.1.2 | ✅ |
| 4.1.4 | Service: get_latest_prices() | [S] | 1h | 4.1.1 | ✅ |
| 4.1.5 | Celery task: sync_all_quotes | [S] | 2h | 4.1.3, 1.2.5 | ✅ |
| 4.1.6 | Celery Beat schedule (3x dia) | [S] | 30min | 4.1.5 | ✅ |
| 4.1.7 | Cache Redis para cotações recentes | [S] | 1h | 1.1.7 | ✅ |
| 4.1.8 | Endpoint GET /quotes/{asset_id} | [S] | 1h | 4.1.1 | ✅ |
| 4.1.9 | Endpoint POST /quotes/sync (manual) | [S] | 30min | 4.1.5 | ✅ |

---

### 4.2 Backend P&L [S]

| # | Tarefa | Tipo | Tempo | Dep. | Status |
|---|--------|------|-------|------|--------|
| 4.2.1 | Service: calculate_unrealized_pnl() | [S] | 2h | 3.1.6, 4.1.4 | ✅ |
| 4.2.2 | Service: calculate_realized_pnl() | [P] | 2h | 3.1.1 | ✅ |
| 4.2.3 | Atualizar GET /positions com P&L | [S] | 1h | 4.2.1 | ✅ |
| 4.2.4 | Endpoint GET /portfolio/summary | [S] | 2h | 4.2.1, 4.2.2 | ✅ |

```
Paralelismo Fase 4:
    ┌─────────────┐               ┌─────────────┐
    │ 4.1.2 yfin  │               │ 4.2.2 RealPL│
    └──────┬──────┘               └─────────────┘
           ▼                         [Paralelo]
    ┌─────────────┐
    │ 4.1.3 Fetch │
    └──────┬──────┘
           ▼
    ┌─────────────┐
    │ 4.1.5 Task  │
    └──────┬──────┘
           │
    ┌──────┴──────┐
    ▼             ▼
┌───────┐   ┌───────────┐
│4.1.6  │   │ 4.2.1 UnPL│
│Sched. │   └─────┬─────┘
└───────┘         ▼
            ┌───────────┐
            │ 4.2.4 Sum │
            └───────────┘
```

---

### 4.3 Frontend Quotes [S]

| # | Tarefa | Tipo | Tempo | Dep. | Status |
|---|--------|------|-------|------|--------|
| 4.3.1 | Exibir preço atual em /positions | [S] | 1h | 4.1.4 | ✅ |
| 4.3.2 | Exibir P&L (valor + %) em /positions | [S] | 1h | 4.2.3 | ✅ |
| 4.3.3 | Indicador "última atualização" | [S] | 30min | 4.3.1 | ✅ |
| 4.3.4 | Botão "Atualizar cotações" | [S] | 30min | 4.1.9 | ✅ |
| 4.3.5 | Coloração verde/vermelho P&L | [P] | 30min | 4.3.2 | ✅ |

---

### Checkpoint Semana 4 ✅

```
□ Cotações sendo buscadas automaticamente 3x/dia
□ Posições marcadas a mercado
□ P&L realizado e não-realizado calculados
□ UI exibindo preços e P&L
```

---

## FASE 5: SISTEMA DE COTAS + DASHBOARD (Semana 5)

### 5.1 Backend Cotas [B]

| # | Tarefa | Tipo | Tempo | Dep. | Status |
|---|--------|------|-------|------|--------|
| 5.1.1 | Criar modelo CashFlow | [S] | 30min | 1.2.2 | ✅ |
| 5.1.2 | Criar modelo FundShares | [S] | 30min | 1.2.2 | ✅ |
| 5.1.3 | CRUD endpoints /cash-flows | [S] | 2h | 5.1.1 | ✅ |
| 5.1.4 | Service: calculate_nav() | [B] | 2h | 4.2.1 | ✅ |
| 5.1.5 | Service: issue_shares() (aporte) | [S] | 2h | 5.1.4 | ✅ |
| 5.1.6 | Service: redeem_shares() (saque) | [S] | 1h | 5.1.4 | ✅ |
| 5.1.7 | Celery task: daily_nav_calculation | [S] | 2h | 5.1.4 | ✅ |
| 5.1.8 | Celery Beat schedule (19:00 BRT) | [S] | 30min | 5.1.7 | ✅ |
| 5.1.9 | Endpoint GET /fund/nav | [S] | 1h | 5.1.4 | ✅ |
| 5.1.10 | Endpoint GET /fund/shares (histórico) | [S] | 1h | 5.1.2 | ✅ |
| 5.1.11 | Endpoint GET /fund/performance | [S] | 1h | 5.1.10 | ✅ |

---

### 5.2 Backend Portfolio [S]

| # | Tarefa | Tipo | Tempo | Dep. | Status |
|---|--------|------|-------|------|--------|
| 5.2.1 | Criar modelo PortfolioSnapshot | [S] | 30min | 1.2.2 | ✅ |
| 5.2.2 | Celery task: generate_daily_snapshot | [S] | 2h | 5.1.4 | ✅ |
| 5.2.3 | Endpoint GET /portfolio/history | [S] | 1h | 5.2.1 | ✅ |
| 5.2.4 | Endpoint GET /portfolio/allocation | [S] | 1h | 3.1.10 | ✅ |

```
Fluxo diário automatizado:
18:30 ──▶ sync_quotes ──▶ 19:00 ──▶ calculate_nav ──▶ 19:30 ──▶ generate_snapshot
```

---

### 5.3 Frontend Dashboard [S]

| # | Tarefa | Tipo | Tempo | Dep. | Status |
|---|--------|------|-------|------|--------|
| 5.3.1 | Página /cash-flows | [S] | 2h | 5.1.3 | ✅ |
| 5.3.2 | Formulário novo aporte/saque | [S] | 2h | 5.3.1 | ✅ |
| 5.3.3 | Exibir cotas emitidas/resgatadas | [S] | 1h | 5.1.5 | ✅ |
| 5.3.4 | Dashboard: Card NAV | [S] | 1h | 5.1.9 | ✅ |
| 5.3.5 | Dashboard: Card Valor Cota | [S] | 1h | 5.1.10 | ✅ |
| 5.3.6 | Dashboard: Card Rentabilidade | [S] | 1h | 5.1.11 | ✅ |
| 5.3.7 | Dashboard: Card P&L Total | [S] | 1h | 4.2.4 | ✅ |
| 5.3.8 | Dashboard: Gráfico Evolução NAV | [S] | 3h | 5.2.3 | ✅ |
| 5.3.9 | Dashboard: Donut Alocação | [S] | 2h | 5.2.4 | ✅ |
| 5.3.10 | Dashboard: Tabela Posições resumida | [S] | 2h | 3.1.10 | ✅ |
| 5.3.11 | Filtro de período (MTD, YTD, 1Y) | [S] | 2h | 5.3.8 | ✅ |

```
Layout Dashboard:
┌─────────────────────────────────────────────────────────┐
│  [5.3.4]  [5.3.5]  [5.3.6]  [5.3.7]                    │
│   NAV      Cota    Rent.    P&L                        │
├─────────────────────────────────────────────────────────┤
│  [5.3.8 Gráfico Evolução]     │  [5.3.9 Alocação]      │
│                               │                        │
├─────────────────────────────────────────────────────────┤
│  [5.3.10 Tabela Posições]                              │
└─────────────────────────────────────────────────────────┘
```

---

### Checkpoint Semana 5 ✅

```
□ Registro de aportes/saques funcionando
□ Cotas sendo emitidas/resgatadas corretamente
□ NAV calculado automaticamente todo dia
□ Dashboard exibindo todas métricas
□ Gráfico de evolução funcionando
```

---

## FASE 6: POLISH & DEPLOY (Semana 6)

### 6.1 Backend Polish [P]

| # | Tarefa | Tipo | Tempo | Dep. | Status |
|---|--------|------|-------|------|--------|
| 6.1.1 | Error handling global | [P] | 2h | - | ✅ |
| 6.1.2 | Logging estruturado (structlog) | [P] | 2h | - | ✅ |
| 6.1.3 | Rate limiting | [P] | 1h | - | ⬜ |
| 6.1.4 | Documentação OpenAPI completa | [P] | 2h | - | ⬜ |
| 6.1.5 | Testes de integração (críticos) | [P] | 4h | - | ⬜ |
| 6.1.6 | Health check endpoint | [P] | 30min | - | ✅ |

---

### 6.2 Frontend Polish [P]

| # | Tarefa | Tipo | Tempo | Dep. | Status |
|---|--------|------|-------|------|--------|
| 6.2.1 | Error boundaries | [P] | 1h | - | ✅ |
| 6.2.2 | Loading skeletons | [P] | 2h | - | ✅ |
| 6.2.3 | Toast de feedback (sucesso/erro) | [P] | 1h | - | ✅ |
| 6.2.4 | Empty states | [P] | 1h | - | ✅ |
| 6.2.5 | Ajustes de responsividade | [P] | 2h | - | ⬜ |
| 6.2.6 | Favicon + meta tags | [P] | 30min | - | ✅ |

---

### 6.3 Infraestrutura Final [S]

| # | Tarefa | Tipo | Tempo | Dep. | Status |
|---|--------|------|-------|------|--------|
| 6.3.1 | Configurar variáveis produção | [S] | 1h | - | ✅ |
| 6.3.2 | Setup domínio customizado | [P] | 1h | - | ⬜ |
| 6.3.3 | CI/CD pipeline (GitHub Actions) | [S] | 2h | - | ⬜ |
| 6.3.4 | Backup automático Supabase | [P] | 30min | - | ⬜ |
| 6.3.5 | Monitoramento (Sentry) | [P] | 1h | - | ⬜ |
| 6.3.6 | Deploy final produção | [S] | 1h | 6.3.1 | ⬜ |
| 6.3.7 | Smoke tests em produção | [S] | 1h | 6.3.6 | ⬜ |

```
Paralelismo Semana 6:
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ 6.1 Backend │ │ 6.2 Front   │ │ 6.3 Infra   │
│   Polish    │ │   Polish    │ │   Final     │
│  [Paralelo] │ │  [Paralelo] │ │  [Paralelo] │
└─────────────┘ └─────────────┘ └─────────────┘
       │               │               │
       └───────────────┴───────────────┘
                       ▼
                ┌─────────────┐
                │ 6.3.6 Deploy│
                └─────────────┘
```

---

### Checkpoint Final MVP ✅

```
□ Sistema estável em produção
□ Fluxo completo funcionando end-to-end
□ Cálculos validados contra extratos reais
□ Performance aceitável (<3s carregamento)
□ Erros tratados adequadamente
□ Documentação básica disponível
```

---

## Resumo de Paralelismo

### Tarefas que PODEM rodar em paralelo

| Fase | Tarefas Paralelas |
|------|-------------------|
| 1.1 | Supabase \|\| Railway \|\| Vercel |
| 1.2 | Schemas Pydantic \|\| Dockerfile |
| 1.3 | Login \|\| Registro |
| 2.1 | Prompt BTG Statement \|\| Prompt Trade Note |
| 2.2 | UploadZone \|\| LoadingSpinner \|\| Toast |
| 3.1 | Transaction Schema \|\| Position Schema |
| 4.2 | Realized P&L \|\| Unrealized P&L |
| 6.x | Backend Polish \|\| Frontend Polish \|\| Infra |

### Tarefas BLOQUEANTES (crítico)

| Tarefa | Bloqueia |
|--------|----------|
| 1.1.1 Supabase | Quase tudo |
| 1.2.1 FastAPI setup | Todo backend |
| 1.3.1 Next.js setup | Todo frontend |
| 2.1.4 Claude integration | Parser tasks |
| 3.1.6 Position calculator | P&L, NAV |
| 4.1.2 yfinance integration | Quotes, MTM |
| 5.1.4 NAV calculator | Cotas, Dashboard |

---

## Estimativa de Horas

| Fase | Backend | Frontend | Infra | Total |
|------|---------|----------|-------|-------|
| 1. Foundation | 12h | 14h | 4h | 30h |
| 2. PDF Parser | 16h | 12h | - | 28h |
| 3. Transactions | 14h | 12h | - | 26h |
| 4. Quotes & P&L | 14h | 5h | - | 19h |
| 5. Cotas + Dash | 16h | 20h | - | 36h |
| 6. Polish | 12h | 8h | 8h | 28h |
| **TOTAL** | **84h** | **71h** | **12h** | **167h** |

**Com 20h/semana dedicadas = ~8 semanas realistas**  
**Com 30h/semana dedicadas = ~6 semanas**

---

*Roadmap v1.0 - Janeiro 2026*
