# Cálculo de Posições e P&L - Modelo de Netting

Este documento explica como o sistema calcula posições e P&L (Profit & Loss) realizado utilizando o modelo de **posição líquida (netting)**.

## Conceito: Modelo de Netting

O modelo de netting estabelece que **apenas UMA posição por ativo pode existir** em cada conta - seja LONG (comprado) ou SHORT (vendido a descoberto), nunca ambas simultaneamente.

### Tipos de Posição

| Tipo | Descrição | Como Abre | Como Fecha |
|------|-----------|-----------|------------|
| **LONG** | Apostando na alta do ativo | Compra (BUY) | Venda (SELL) |
| **SHORT** | Apostando na queda do ativo | Venda sem posição LONG | Compra (BUY) |

---

## Fluxo de Transações

### Transação de COMPRA (BUY)

```
┌─────────────────────────────────────────────────────────────┐
│                      COMPRA (BUY)                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Posição Atual = NONE?                                      │
│  └─► Abre posição LONG (sem P&L)                           │
│                                                             │
│  Posição Atual = LONG?                                      │
│  └─► Aumenta posição LONG (sem P&L)                        │
│      Recalcula preço médio ponderado                        │
│                                                             │
│  Posição Atual = SHORT?                                     │
│  ├─► Se qty_compra <= qty_short:                           │
│  │   └─► Fecha SHORT parcial/total (GERA P&L)              │
│  └─► Se qty_compra > qty_short:                            │
│      └─► Fecha TODO o SHORT (GERA P&L)                     │
│          + Abre LONG com excesso (sem P&L)                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Transação de VENDA (SELL)

```
┌─────────────────────────────────────────────────────────────┐
│                      VENDA (SELL)                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Posição Atual = NONE?                                      │
│  └─► Abre posição SHORT (sem P&L)                          │
│                                                             │
│  Posição Atual = SHORT?                                     │
│  └─► Aumenta posição SHORT (sem P&L)                       │
│      Recalcula preço médio de abertura                      │
│                                                             │
│  Posição Atual = LONG?                                      │
│  ├─► Se qty_venda <= qty_long:                             │
│  │   └─► Fecha LONG parcial/total (GERA P&L)               │
│  └─► Se qty_venda > qty_long:                              │
│      └─► Fecha TODO o LONG (GERA P&L)                      │
│          + Abre SHORT com excesso (sem P&L)                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Cálculo de P&L Realizado

### P&L de Fechamento LONG (venda de posição comprada)

```
P&L = (preço_venda - preço_médio_compra) × quantidade - taxas
```

**Exemplo:**
- Comprou 100 ações a R$ 20,00 (custo total: R$ 2.000)
- Vendeu 100 ações a R$ 25,00 (receita bruta: R$ 2.500)
- Taxas: R$ 10,00
- **P&L = (25 - 20) × 100 - 10 = R$ 490,00** ✅

### P&L de Fechamento SHORT (compra para cobrir posição vendida)

```
P&L = (preço_médio_venda - preço_compra) × quantidade - taxas
```

**Exemplo:**
- Vendeu a descoberto 100 ações a R$ 30,00 (abriu SHORT)
- Comprou para cobrir 100 ações a R$ 25,00 (fechou SHORT)
- Taxas: R$ 10,00
- **P&L = (30 - 25) × 100 - 10 = R$ 490,00** ✅

---

## Preço Médio Ponderado

### Para Posição LONG

Quando múltiplas compras são feitas, o preço médio é calculado:

```
preço_médio = custo_total / quantidade_total

onde:
  custo_total = Σ (quantidade × preço + taxas) de cada compra
```

**Exemplo:**
1. Compra 100 ações a R$ 10,00 + R$ 5 taxas = R$ 1.005
2. Compra 50 ações a R$ 12,00 + R$ 3 taxas = R$ 603
3. Custo total = R$ 1.608
4. Quantidade total = 150
5. **Preço médio = R$ 1.608 / 150 = R$ 10,72**

### Para Posição SHORT

O preço médio de abertura do SHORT é o preço médio de venda:

```
preço_médio_short = valor_total_vendas / quantidade_total

onde:
  valor_total_vendas = Σ (quantidade × preço) de cada venda a descoberto
```

---

## Casos Especiais

### Flip de Posição (LONG → SHORT ou SHORT → LONG)

Quando uma transação excede a posição atual, ocorre um "flip":

**Exemplo LONG → SHORT:**
1. Posição: LONG 100 ações, preço médio R$ 20
2. Venda: 150 ações a R$ 25
3. Resultado:
   - Fecha LONG de 100 ações → **P&L = (25-20) × 100 = R$ 500**
   - Abre SHORT de 50 ações a R$ 25

**Exemplo SHORT → LONG:**
1. Posição: SHORT 100 ações, preço médio R$ 30
2. Compra: 150 ações a R$ 25
3. Resultado:
   - Fecha SHORT de 100 ações → **P&L = (30-25) × 100 = R$ 500**
   - Abre LONG de 50 ações a R$ 25

### Stock Split

Quando ocorre um desdobramento (split):
- A quantidade é multiplicada pelo fator
- O custo total permanece igual
- O preço médio é recalculado

```
nova_quantidade = quantidade_atual × fator_split
novo_preço_médio = custo_total / nova_quantidade
```

### Transferências

| Tipo | Comportamento |
|------|---------------|
| TRANSFER_IN | Adiciona à posição LONG (como BUY sem P&L) |
| TRANSFER_OUT | Remove da posição LONG (como SELL sem P&L) |

---

## Estrutura de Dados

### Posição (Position)

| Campo | Descrição |
|-------|-----------|
| `position_type` | LONG ou SHORT |
| `quantity` | Quantidade (sempre positiva) |
| `avg_price` | Preço médio de abertura |
| `total_cost` | Custo total da posição |
| `opened_at` | Data de abertura |

### Evento de P&L Realizado (RealizedPnLEntry)

| Campo | Descrição |
|-------|-----------|
| `pnl_type` | LONG_CLOSE ou SHORT_CLOSE |
| `quantity` | Quantidade fechada |
| `close_price` | Preço de fechamento |
| `avg_open_price` | Preço médio de abertura |
| `gross_proceeds` | Receita bruta |
| `cost_basis` | Base de custo |
| `realized_pnl` | P&L realizado |
| `fees` | Taxas da transação |

---

## Serviços Relacionados

### PositionService (`app/services/position_service.py`)

Responsável por:
- Calcular posições a partir de transações
- Manter estado de LONG/SHORT por ativo
- Recalcular posições após novas transações

**Métodos principais:**
- `calculate_position(account_id, asset_id)` - Calcula posição para um ativo
- `recalculate_account_positions(account_id)` - Recalcula todas as posições de uma conta

### PnLService (`app/services/pnl_service.py`)

Responsável por:
- Calcular P&L realizado (fechamento de posições)
- Calcular P&L não-realizado (posições abertas vs preço atual)
- Classificar eventos como LONG_CLOSE ou SHORT_CLOSE

**Métodos principais:**
- `calculate_realized_pnl(account_id, ...)` - Calcula P&L realizado
- `calculate_unrealized_pnl(positions, prices)` - Calcula P&L não-realizado

---

## Script de Recálculo

Para recalcular todas as posições e ver o resumo de P&L:

```bash
cd backend
python -m scripts.recalculate_positions
```

Ou via API:

```
POST /api/v1/positions/{account_id}/recalculate
```

---

## Exemplo Completo

### Cenário: Operações em PETR4

| Data | Operação | Qty | Preço | Posição Após | P&L |
|------|----------|-----|-------|--------------|-----|
| 01/01 | BUY | 100 | R$ 30 | LONG 100 @ R$ 30 | - |
| 15/01 | BUY | 50 | R$ 32 | LONG 150 @ R$ 30,67 | - |
| 01/02 | SELL | 150 | R$ 35 | NONE | **+R$ 650** |
| 15/02 | SELL | 100 | R$ 33 | SHORT 100 @ R$ 33 | - |
| 01/03 | BUY | 100 | R$ 28 | NONE | **+R$ 500** |

**Cálculos:**

1. **01/02 - Fecha LONG:**
   - Custo médio: (100×30 + 50×32) / 150 = R$ 30,67
   - P&L = (35 - 30,67) × 150 = **R$ 650**

2. **01/03 - Fecha SHORT:**
   - Preço de abertura SHORT: R$ 33
   - P&L = (33 - 28) × 100 = **R$ 500**

**P&L Total: R$ 1.150**

---

## Considerações Importantes

1. **Ordem Cronológica**: Transações são processadas na ordem de execução
2. **Uma Posição por Ativo**: Nunca existem LONG e SHORT simultâneos
3. **Taxas**: Incluídas no custo de abertura (LONG) ou deduzidas no P&L
4. **Dividendos/JCP**: Não afetam quantidade da posição, apenas geram renda
5. **Recálculo**: Sempre processa TODAS as transações do início para garantir consistência
