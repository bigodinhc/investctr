# InvestCTR - Plataforma de Gestão de Investimentos Pessoais

Plataforma web privada para consolidação e gestão de investimentos pessoais com múltiplas corretoras, sistema de cotas e análise de risco.

## Visão Geral

InvestCTR resolve o problema de investidores com portfólios diversificados em múltiplas corretoras (BTG, XP, BTG Cayman) que enfrentam dificuldades para:

- Consolidar informações fragmentadas em diferentes plataformas
- Acompanhar performance real descontando aportes e saques
- Calcular métricas de risco de forma integrada
- Extrair e organizar dados de extratos em PDF

## Stack Tecnológica

### Frontend
- **Next.js 14** (App Router)
- **TypeScript**
- **TailwindCSS** + **shadcn/ui**
- **Recharts** / **TradingView Lightweight**
- **TanStack Query** + **Zustand**

### Backend
- **Python 3.12**
- **FastAPI**
- **SQLAlchemy** + **Alembic**
- **Celery** + **Redis**

### Infraestrutura
- **Vercel** - Frontend hosting
- **Railway** - Backend + Redis
- **Supabase** - Database (PostgreSQL) + Auth + Storage

### Integrações
- **Claude API** - Parsing inteligente de PDFs
- **yfinance** - Cotações de mercado (gratuito)
- **LSEG** - Cotações premium (futuro)

## Funcionalidades Principais

### MVP (6 semanas)
- [x] Autenticação via Supabase
- [ ] Upload e parsing de extratos BTG via Claude
- [ ] Gestão de transações e posições
- [ ] Sistema de cotas (NAV diário)
- [ ] Dashboard com evolução patrimonial
- [ ] Cotações automáticas via yfinance

### Versão Completa (pós-MVP)
- [ ] Suporte a XP e BTG Cayman
- [ ] Integração LSEG
- [ ] Análise de risco (VaR, Sharpe, Sortino)
- [ ] Multi-moeda (BRL/USD)
- [ ] Migração de 5 anos de histórico

## Estrutura do Projeto

```
investctr/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # Endpoints REST
│   │   ├── core/            # Segurança, config
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # Lógica de negócio
│   │   ├── integrations/    # Claude, yfinance, LSEG
│   │   └── workers/         # Celery tasks
│   ├── migrations/
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── app/             # Next.js App Router
│   │   ├── components/      # React components
│   │   ├── hooks/           # Custom hooks
│   │   ├── lib/             # Utilities
│   │   ├── stores/          # Zustand stores
│   │   └── types/           # TypeScript types
│   └── public/
└── docs/
    ├── ARCHITECTURE_Investment_Platform.md
    ├── MVP_Investment_Platform.md
    ├── PRD_Investment_Platform.md
    └── ROADMAP_Investment_Platform.md
```

## Documentação

| Documento | Descrição |
|-----------|-----------|
| [PRD](docs/PRD_Investment_Platform.md) | Requisitos funcionais e não-funcionais |
| [ARCHITECTURE](docs/ARCHITECTURE_Investment_Platform.md) | Stack técnica e modelagem de dados |
| [MVP](docs/MVP_Investment_Platform.md) | Escopo do MVP e user stories |
| [ROADMAP](docs/ROADMAP_Investment_Platform.md) | Cronograma detalhado de implementação |

## Configuração do Ambiente

### Pré-requisitos
- Node.js 20+
- Python 3.12+
- Docker (opcional)

### Variáveis de Ambiente

**Backend (.env)**
```bash
DATABASE_URL=postgresql://...
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=xxx
REDIS_URL=redis://...
ANTHROPIC_API_KEY=xxx
```

**Frontend (.env.local)**
```bash
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=xxx
NEXT_PUBLIC_API_URL=https://api.domain.com
```

### Instalação

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

### Execução

```bash
# Backend
cd backend
uvicorn app.main:app --reload

# Celery Worker
celery -A app.workers.celery_app worker --loglevel=info

# Frontend
cd frontend
npm run dev
```

## Contribuição

Este é um projeto pessoal. Consulte a documentação em `/docs` para entender a arquitetura e o roadmap de desenvolvimento.

## Licença

Projeto privado - todos os direitos reservados.
