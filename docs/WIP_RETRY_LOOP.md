# WIP: Retry Loop para Extração Completa de PDFs

**Data:** 2025-01-20
**Status:** ✅ RESOLVIDO (2026-01-20)
**Causa raiz:** Modelo Pydantic de validação não incluía `investment_funds`

---

## Problema

O Claude Opus 4.5 omite a seção `investment_funds` (~50% das vezes) ao processar PDFs grandes (34 páginas). Isso resulta em R$ 2.2M de fundos não sendo extraídos.

**Causa:** Diluição de atenção em documentos extensos - o modelo "esquece" de extrair certas seções mesmo com instruções explícitas no prompt.

---

## Solução Implementada

Retry loop inteligente que:
1. Detecta seções faltantes após parse inicial
2. Faz chamadas focadas com prompts específicos (8k tokens)
3. Faz merge dos resultados

### Arquitetura

```
Parse Inicial (64k tokens)
    ↓
Detectar seções faltantes
    ↓
[investment_funds ou fixed_income missing?]
    ├─ SIM → Chamada focada (8k tokens)
    │         ↓
    │         Merge dos resultados
    │
    └─ NÃO → Continuar
    ↓
Validar e Retornar
```

---

## Arquivos Modificados

### 1. `backend/app/integrations/claude/prompts/base.py`
- Adicionado método `get_focused_prompt()` com implementação padrão retornando `None`

### 2. `backend/app/integrations/claude/prompts/statement.py`
- Atualizado `PROMPT_VERSION` para `v2.3-retry-loop`
- Adicionado `FOCUSED_PROMPTS` dict com prompts para:
  - `investment_funds` (1035 chars)
  - `fixed_income_positions` (845 chars)
- Implementado `get_focused_prompt()` que retorna prompt focado

### 3. `backend/app/integrations/claude/client.py`
- Adicionados parâmetros `is_retry` e `retry_section` para logging

### 4. `backend/app/integrations/claude/parsers/base.py`
- Adicionado `REQUIRED_SECTIONS` (5 seções monitoradas)
- Adicionado `RECOVERABLE_SECTIONS` (investment_funds, fixed_income_positions)
- Adicionado `detect_missing_sections()` - detecta seções vazias/None
- Adicionado `retry_for_missing_section()` - faz chamada focada
- Adicionado `merge_results()` - combina dados
- Atualizado `parse()` com fluxo de retry

---

## Logs para Monitorar

Verificar no Railway:

```
parsing_sections_missing    # Seções detectadas como faltantes
parsing_retry_needed        # Retry sendo iniciado
retry_for_section_start     # Chamada focada iniciando
section_recovered           # Seção recuperada com sucesso
section_recovery_failed     # Retry não conseguiu recuperar
parsing_retry_completed     # Resumo do retry
```

---

## Testes Locais (Passaram)

```bash
cd backend && source .venv/bin/activate

# Teste de sintaxe
python -c "from app.integrations.claude.parsers import StatementParser; print('OK')"

# Teste de detecção
python -c "
from app.integrations.claude.parsers import StatementParser
parser = StatementParser()
test_data = {'investment_funds': [], 'fixed_income_positions': None}
missing = parser.detect_missing_sections(test_data)
print('Missing:', missing)  # ['investment_funds', 'fixed_income_positions']
"

# Teste de merge
python -c "
from app.integrations.claude.parsers import StatementParser
parser = StatementParser()
original = {'investment_funds': []}
focused = {'investment_funds': [{'fund_name': 'Test'}]}
merged = parser.merge_results(original, focused, 'investment_funds')
print('Recovered:', len(merged['investment_funds']))  # 1
"
```

---

## Possíveis Problemas a Investigar

### 1. Retry não está sendo acionado
- Verificar se `detect_missing_sections()` está identificando corretamente
- Log `parsing_sections_missing` deve aparecer

### 2. Retry está sendo acionado mas não recupera
- Verificar se o prompt focado está sendo usado
- Log `retry_for_section_start` deve mostrar prompt_length > 0
- Verificar resposta do Claude no retry

### 3. Merge não está funcionando
- Verificar se `merge_results()` está sendo chamado
- Log `section_recovered` deve aparecer se funcionou

### 4. Seção já vem preenchida (não é missing)
- Se `investment_funds: []` (array vazio) vem do Claude, é detectado como missing
- Se `investment_funds: null` vem do Claude, é detectado como missing
- Se a chave não existe, é detectado como missing
- **MAS:** Se `investment_funds` não aparece na resposta (chave omitida), `raw_data.get()` retorna `None` → detectado como missing ✓

### 5. Problema no prompt focado
- Talvez o prompt focado não seja claro o suficiente
- Testar manualmente enviando só o prompt focado para o Claude

---

## Commits Relacionados

- `c62fba15` - feat: add intelligent retry loop for missing PDF sections
- `4bd21f74` - fix: make investment_funds MANDATORY in Claude response
- `09e08d9d` - fix: disable Railway build cache and add prompt version tracking

---

## Próximos Passos (Amanhã)

1. **Ver logs no Railway** - Identificar se retry está sendo acionado
2. **Testar localmente com PDF real** - Simular o fluxo completo
3. **Ajustar prompt focado** se necessário
4. **Considerar alternativas:**
   - Aumentar temperatura no retry
   - Usar modelo diferente no retry (Sonnet?)
   - Mudar estratégia: pedir só fundos no parse inicial

---

## Como Testar Localmente com PDF Real

```bash
cd backend && source .venv/bin/activate

python -c "
import asyncio
from app.integrations.claude.parsers import StatementParser

async def test():
    parser = StatementParser()
    with open('../Extratos/2022/10-2022.pdf', 'rb') as f:
        result = await parser.parse(f.read())

    print('Success:', result.success)
    print('Keys:', list(result.raw_data.keys()))
    print('investment_funds:', result.raw_data.get('investment_funds'))

asyncio.run(test())
"
```

---

## Contexto Adicional

- O PDF de outubro/2022 tem 34 páginas
- Contém 2 fundos de investimento totalizando ~R$ 2.2M
- O problema é não-determinístico (~50% de falha)
- Prompt version atual: `v2.3-retry-loop`

---

## ✅ RESOLUÇÃO (2026-01-20)

### Diagnóstico

Através dos logs do Railway, identificamos que:

1. Claude **extraía corretamente** `investment_funds` (2 fundos)
2. Logs mostravam `investment_funds_count=2` no `extraction_summary`
3. **MAS** ao recuperar do banco, `has_investment_funds=false`

### Causa Raiz

O modelo Pydantic `ParsedStatementData` em `backend/app/services/validation.py` **não incluía** o campo `investment_funds`.

Quando o `ValidationService.validate_statement_data()` era chamado:
1. `model_validate(raw_data)` ignorava campos não definidos no modelo
2. `model_dump()` retornava apenas os campos do modelo
3. `investment_funds` era perdido antes de salvar no banco

### Correção

Commit `ba101b14`:
1. Adicionado modelo `InvestmentFundPosition` com validação de decimais
2. Adicionado `investment_funds: list[InvestmentFundPosition]` ao `ParsedStatementData`

### Resultado

- `has_investment_funds=true`
- `investment_funds_count=2`
- Fundos de investimento agora são preservados corretamente
