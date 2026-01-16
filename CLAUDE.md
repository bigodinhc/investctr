# CLAUDE.md - Instruções para Claude Code

Este arquivo contém instruções específicas para o Claude Code ao trabalhar neste projeto.

## Sobre o Projeto

InvestCTR é uma plataforma de gestão de investimentos pessoais. Consulte a documentação em `/docs` para contexto completo:

- `docs/PRD_Investment_Platform.md` - Requisitos do produto
- `docs/ARCHITECTURE_Investment_Platform.md` - Arquitetura técnica
- `docs/MVP_Investment_Platform.md` - Escopo do MVP
- `docs/ROADMAP_Investment_Platform.md` - Cronograma de tarefas

## Regra Crítica: Atualização do Roadmap

**IMPORTANTE**: Sempre que completar uma tarefa do projeto, você DEVE atualizar o arquivo `docs/ROADMAP_Investment_Platform.md`:

1. Localize a tarefa completada na tabela correspondente
2. Altere o status de `⬜` para `✅`
3. Exemplo:
   ```markdown
   # Antes
   | 1.1.1 | Criar projeto Supabase | [B] | 30min | - | ⬜ |

   # Depois
   | 1.1.1 | Criar projeto Supabase | [B] | 30min | - | ✅ |
   ```

Isso mantém o roadmap sempre atualizado e permite acompanhar o progresso real do projeto.

## Stack Tecnológica

### Backend (Python)
- **Framework**: FastAPI 0.110+
- **ORM**: SQLAlchemy 2.x
- **Migrations**: Alembic
- **Task Queue**: Celery 5.x + Redis
- **Validação**: Pydantic 2.x

### Frontend (TypeScript)
- **Framework**: Next.js 14 (App Router)
- **Estilização**: TailwindCSS + shadcn/ui
- **State**: Zustand + TanStack Query
- **Forms**: React Hook Form + Zod

### Infraestrutura
- **Database**: Supabase (PostgreSQL + RLS)
- **Auth**: Supabase Auth
- **Storage**: Supabase Storage (PDFs)
- **Backend Hosting**: Railway
- **Frontend Hosting**: Vercel

## Convenções de Código

### Python (Backend)
```python
# Use type hints sempre
def calculate_nav(positions: list[Position]) -> Decimal:
    ...

# Async para endpoints
@router.get("/positions")
async def get_positions(db: AsyncSession = Depends(get_db)):
    ...

# Pydantic para validação
class TransactionCreate(BaseModel):
    asset_id: UUID
    quantity: Decimal
    price: Decimal
```

### TypeScript (Frontend)
```typescript
// Componentes funcionais com tipos
interface PositionCardProps {
  position: Position;
  onSelect?: (id: string) => void;
}

export function PositionCard({ position, onSelect }: PositionCardProps) {
  // ...
}

// Use path aliases
import { Button } from "@/components/ui/button";
import { usePositions } from "@/hooks/usePositions";
```

## Estrutura de Diretórios

### Backend
```
backend/
├── app/
│   ├── api/v1/           # Endpoints por domínio
│   ├── core/             # Config, security, exceptions
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic
│   ├── integrations/     # Claude, yfinance, LSEG
│   └── workers/tasks/    # Celery tasks
```

### Frontend
```
frontend/src/
├── app/                  # Next.js App Router pages
├── components/
│   ├── ui/              # shadcn/ui components
│   ├── layout/          # Sidebar, Header
│   ├── dashboard/       # Dashboard-specific
│   └── shared/          # Reusable components
├── hooks/               # Custom React hooks
├── lib/                 # Utils, API client
├── stores/              # Zustand stores
└── types/               # TypeScript types
```

## Padrões de API

### Endpoints REST
```
GET    /api/v1/accounts              # Lista
POST   /api/v1/accounts              # Cria
GET    /api/v1/accounts/{id}         # Detalhe
PUT    /api/v1/accounts/{id}         # Atualiza
DELETE /api/v1/accounts/{id}         # Remove
```

### Respostas
```json
// Sucesso
{ "data": {...}, "message": "Success" }

// Erro
{ "detail": "Error message", "code": "ERROR_CODE" }
```

## Segurança

- **RLS obrigatório** em todas as tabelas com dados de usuário
- **JWT validation** em todos endpoints protegidos
- **Supabase service key** apenas no backend
- **PDFs** armazenados em bucket privado com signed URLs

## Tarefas Celery

```python
# Agendamento diário
'sync-quotes': 10:30, 14:00, 18:30 BRT
'calculate-nav': 19:00 BRT
'generate-snapshot': 19:30 BRT
```

## Comandos Úteis

```bash
# Backend
uvicorn app.main:app --reload
celery -A app.workers.celery_app worker -l info
alembic upgrade head
alembic revision --autogenerate -m "description"

# Frontend
npm run dev
npm run build
npm run lint

# Testes
pytest backend/tests/
npm run test
```

## Checklist ao Completar Tarefas

- [ ] Código implementado e funcionando
- [ ] Tipos/validações corretos
- [ ] RLS aplicado (se tabela nova)
- [ ] Endpoint documentado (OpenAPI)
- [ ] Testado manualmente
- [ ] **ROADMAP atualizado** (⬜ → ✅)
