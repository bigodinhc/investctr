# Product Requirements Document (PRD)
# Plataforma de Gestão de Investimentos Pessoais

**Versão:** 1.0  
**Data:** Janeiro 2026  
**Autor:** Bigode  
**Status:** Draft

---

## 1. Visão Geral do Produto

### 1.1 Problema

Investidores com portfólios diversificados em múltiplas corretoras (BTG, XP, BTG Cayman) e classes de ativos (ações, derivativos, renda fixa, offshore) enfrentam dificuldades para:

- Consolidar informações fragmentadas em diferentes plataformas
- Acompanhar performance real descontando aportes e saques
- Calcular métricas de risco de forma integrada
- Extrair e organizar dados de extratos em PDF
- Visualizar evolução patrimonial de forma unificada

### 1.2 Solução

Uma plataforma web privada que consolida todas as posições e transações de investimento, oferecendo visão unificada de patrimônio, performance via sistema de cotas, análise de risco e extração automatizada de dados via LLM.

### 1.3 Objetivos do Produto

| Objetivo | Métrica de Sucesso |
|----------|-------------------|
| Consolidação completa | 100% das contas e ativos integrados |
| Precisão de dados | <0.1% de divergência vs extratos originais |
| Eficiência operacional | Parsing de PDF em <30 segundos |
| Atualização de cotações | 3x ao dia, latência <5 minutos |
| Histórico migrado | 5 anos de dados importados |

---

## 2. Escopo do Produto

### 2.1 Em Escopo (MVP + Completo)

**Gestão de Contas**
- Cadastro de contas: BTG Brasil, XP, BTG Cayman
- Suporte multi-moeda (BRL, USD)
- Categorização por tipo de conta

**Ingestão de Dados**
- Upload manual de PDFs (extratos, notas de corretagem)
- Parsing inteligente via Claude API
- Validação humana antes de commit
- Armazenamento de documentos originais

**Portfolio & Posições**
- Consolidação de posições abertas
- Classificação: long, short, day trade, swing
- Suporte a: ações, ETFs, FIIs, opções, futuros, Tesouro Direto
- Histórico completo de transações

**Sistema de Cotas**
- Cálculo automático diário de NAV
- Emissão de cotas em aportes
- Resgate de cotas em saques
- Rentabilidade real descontando fluxos
- Comparativo com benchmarks (CDI, IBOV, S&P500)

**Performance & P&L**
- P&L realizado por operação
- P&L não-realizado (mark-to-market)
- Custos operacionais (corretagem, emolumentos, custódia)
- Atribuição de performance por ativo e setor

**Risk Analytics**
- Value at Risk (VaR) - paramétrico e histórico
- Sharpe Ratio, Sortino Ratio, Calmar Ratio
- Beta vs benchmarks
- Matriz de correlação entre posições
- Drawdown máximo e tempo de recuperação
- Exposição por moeda, setor, geografia

**Market Data**
- Integração LSEG (premium)
- Fallback yfinance (gratuito)
- Atualização 2-3x ao dia
- Cache inteligente

### 2.2 Fora de Escopo (v1.0)

- Controle tributário (DARF, IR)
- Integração automática via APIs de corretoras
- Monitoramento de emails para PDFs
- Aplicativo mobile nativo
- Multi-usuário / multi-tenant
- Alertas e notificações push
- Backtesting de estratégias

---

## 3. Personas e Casos de Uso

### 3.1 Persona Principal

**Nome:** Investidor Individual Sofisticado  
**Perfil:** Profissional do mercado financeiro com portfólio diversificado em múltiplas corretoras e jurisdições  
**Necessidades:**
- Visão consolidada em tempo real
- Métricas profissionais de risco
- Controle preciso de performance
- Eficiência na organização de dados

### 3.2 Casos de Uso Principais

| ID | Caso de Uso | Prioridade |
|----|-------------|------------|
| UC01 | Upload e parsing de extrato BTG | Alta |
| UC02 | Visualizar posições consolidadas | Alta |
| UC03 | Acompanhar evolução de cotas | Alta |
| UC04 | Registrar aporte/saque | Alta |
| UC05 | Analisar P&L por período | Alta |
| UC06 | Consultar métricas de risco | Média |
| UC07 | Comparar performance vs benchmark | Média |
| UC08 | Exportar relatórios | Baixa |

---

## 4. Requisitos Funcionais

### 4.1 Módulo de Contas (RF-ACC)

| ID | Requisito | Prioridade |
|----|-----------|------------|
| RF-ACC-01 | Sistema deve permitir cadastro de contas com nome, tipo e moeda | Alta |
| RF-ACC-02 | Sistema deve suportar tipos: BTG BR, XP, BTG Cayman, Tesouro Direto | Alta |
| RF-ACC-03 | Sistema deve exibir saldo e posições por conta | Alta |
| RF-ACC-04 | Sistema deve consolidar visão cross-account | Alta |

### 4.2 Módulo de Documentos (RF-DOC)

| ID | Requisito | Prioridade |
|----|-----------|------------|
| RF-DOC-01 | Sistema deve aceitar upload de PDF até 20MB | Alta |
| RF-DOC-02 | Sistema deve identificar tipo de documento automaticamente | Alta |
| RF-DOC-03 | Sistema deve extrair transações via LLM (Claude API) | Alta |
| RF-DOC-04 | Sistema deve apresentar preview para validação humana | Alta |
| RF-DOC-05 | Sistema deve armazenar documento original | Alta |
| RF-DOC-06 | Sistema deve permitir reprocessamento de documento | Média |

### 4.3 Módulo de Transações (RF-TXN)

| ID | Requisito | Prioridade |
|----|-----------|------------|
| RF-TXN-01 | Sistema deve registrar compras e vendas | Alta |
| RF-TXN-02 | Sistema deve registrar dividendos e JCP | Alta |
| RF-TXN-03 | Sistema deve registrar splits e grupamentos | Média |
| RF-TXN-04 | Sistema deve calcular preço médio automaticamente | Alta |
| RF-TXN-05 | Sistema deve permitir edição manual de transações | Média |
| RF-TXN-06 | Sistema deve manter audit trail de alterações | Baixa |

### 4.4 Módulo de Posições (RF-POS)

| ID | Requisito | Prioridade |
|----|-----------|------------|
| RF-POS-01 | Sistema deve calcular posições a partir de transações | Alta |
| RF-POS-02 | Sistema deve classificar posição como long/short | Alta |
| RF-POS-03 | Sistema deve identificar day trades | Alta |
| RF-POS-04 | Sistema deve marcar posições a mercado | Alta |
| RF-POS-05 | Sistema deve calcular P&L não-realizado | Alta |

### 4.5 Módulo de Cash Flow (RF-CF)

| ID | Requisito | Prioridade |
|----|-----------|------------|
| RF-CF-01 | Sistema deve registrar aportes com data e valor | Alta |
| RF-CF-02 | Sistema deve registrar saques com data e valor | Alta |
| RF-CF-03 | Sistema deve converter valores em moeda estrangeira | Alta |
| RF-CF-04 | Sistema deve calcular emissão/resgate de cotas | Alta |

### 4.6 Módulo de Cotas (RF-QUOTA)

| ID | Requisito | Prioridade |
|----|-----------|------------|
| RF-QUOTA-01 | Sistema deve calcular NAV diário automaticamente | Alta |
| RF-QUOTA-02 | Sistema deve calcular valor da cota diário | Alta |
| RF-QUOTA-03 | Sistema deve emitir cotas em aportes | Alta |
| RF-QUOTA-04 | Sistema deve resgatar cotas em saques | Alta |
| RF-QUOTA-05 | Sistema deve calcular rentabilidade da cota | Alta |
| RF-QUOTA-06 | Sistema deve comparar com benchmarks | Média |

### 4.7 Módulo de Market Data (RF-MKT)

| ID | Requisito | Prioridade |
|----|-----------|------------|
| RF-MKT-01 | Sistema deve buscar cotações via LSEG | Alta |
| RF-MKT-02 | Sistema deve usar yfinance como fallback | Alta |
| RF-MKT-03 | Sistema deve atualizar cotações 3x ao dia | Alta |
| RF-MKT-04 | Sistema deve armazenar histórico de preços | Alta |
| RF-MKT-05 | Sistema deve suportar múltiplas moedas | Alta |

### 4.8 Módulo de Risco (RF-RISK)

| ID | Requisito | Prioridade |
|----|-----------|------------|
| RF-RISK-01 | Sistema deve calcular VaR diário (95%, 99%) | Média |
| RF-RISK-02 | Sistema deve calcular Sharpe Ratio | Média |
| RF-RISK-03 | Sistema deve calcular Sortino Ratio | Média |
| RF-RISK-04 | Sistema deve calcular Beta vs benchmarks | Média |
| RF-RISK-05 | Sistema deve calcular drawdown máximo | Média |
| RF-RISK-06 | Sistema deve exibir matriz de correlação | Baixa |
| RF-RISK-07 | Sistema deve calcular exposição por categoria | Média |

### 4.9 Módulo de Dashboard (RF-DASH)

| ID | Requisito | Prioridade |
|----|-----------|------------|
| RF-DASH-01 | Sistema deve exibir NAV atual e variação | Alta |
| RF-DASH-02 | Sistema deve exibir gráfico de evolução patrimonial | Alta |
| RF-DASH-03 | Sistema deve exibir alocação por classe de ativo | Alta |
| RF-DASH-04 | Sistema deve exibir posições abertas com P&L | Alta |
| RF-DASH-05 | Sistema deve exibir métricas de risco resumidas | Média |
| RF-DASH-06 | Sistema deve permitir filtros por período | Alta |

---

## 5. Requisitos Não-Funcionais

### 5.1 Performance (RNF-PERF)

| ID | Requisito | Métrica |
|----|-----------|---------|
| RNF-PERF-01 | Tempo de carregamento do dashboard | < 2 segundos |
| RNF-PERF-02 | Tempo de parsing de PDF | < 30 segundos |
| RNF-PERF-03 | Tempo de atualização de cotações | < 5 minutos |
| RNF-PERF-04 | Tempo de cálculo de risco | < 10 segundos |

### 5.2 Segurança (RNF-SEC)

| ID | Requisito |
|----|-----------|
| RNF-SEC-01 | Autenticação obrigatória via Supabase Auth |
| RNF-SEC-02 | Todos os dados criptografados em repouso |
| RNF-SEC-03 | Comunicação exclusivamente via HTTPS |
| RNF-SEC-04 | Row Level Security (RLS) no banco de dados |
| RNF-SEC-05 | PDFs armazenados em bucket privado |

### 5.3 Disponibilidade (RNF-AVAIL)

| ID | Requisito | Métrica |
|----|-----------|---------|
| RNF-AVAIL-01 | Uptime da aplicação | > 99% |
| RNF-AVAIL-02 | Backup diário do banco | Automático |
| RNF-AVAIL-03 | Retenção de backups | 30 dias |

### 5.4 Usabilidade (RNF-UX)

| ID | Requisito |
|----|-----------|
| RNF-UX-01 | Interface responsiva (desktop) |
| RNF-UX-02 | Feedback visual em operações assíncronas |
| RNF-UX-03 | Mensagens de erro claras e acionáveis |
| RNF-UX-04 | Navegação consistente entre módulos |

---

## 6. Integrações

### 6.1 Integrações Externas

| Sistema | Tipo | Propósito |
|---------|------|-----------|
| Claude API (Anthropic) | REST API | Parsing inteligente de PDFs |
| LSEG Workspace | API | Cotações premium de mercado |
| yfinance | Python lib | Cotações fallback (gratuito) |

### 6.2 Integrações de Infraestrutura

| Sistema | Propósito |
|---------|-----------|
| Supabase | Banco de dados, Auth, Storage |
| Vercel | Hospedagem frontend |
| Railway | Hospedagem backend + Redis |

---

## 7. Fluxos de Usuário

### 7.1 Fluxo: Upload de Extrato

```
1. Usuário acessa módulo "Documentos"
2. Usuário seleciona arquivo PDF
3. Sistema faz upload para Supabase Storage
4. Sistema envia PDF para Claude API
5. Claude extrai transações em formato estruturado
6. Sistema exibe preview das transações extraídas
7. Usuário valida ou corrige dados
8. Usuário confirma importação
9. Sistema persiste transações no banco
10. Sistema recalcula posições e cotas
```

### 7.2 Fluxo: Registro de Aporte

```
1. Usuário acessa módulo "Cash Flow"
2. Usuário clica em "Novo Aporte"
3. Usuário informa: conta, valor, data, moeda
4. Sistema calcula NAV atual
5. Sistema calcula quantidade de cotas a emitir
6. Sistema exibe preview da operação
7. Usuário confirma
8. Sistema registra aporte e emite cotas
9. Sistema atualiza dashboard
```

### 7.3 Fluxo: Visualização de Performance

```
1. Usuário acessa Dashboard
2. Sistema carrega NAV atual e histórico
3. Sistema exibe gráfico de evolução
4. Usuário seleciona período (MTD, YTD, 1Y, etc.)
5. Sistema recalcula métricas para o período
6. Sistema exibe: rentabilidade, drawdown, Sharpe
7. Usuário pode detalhar por conta ou ativo
```

---

## 8. Regras de Negócio

### 8.1 Cálculo de Cotas

```
RN-01: NAV = Σ(posições * preço atual) + saldo em caixa
RN-02: Valor da Cota = NAV / Cotas em Circulação
RN-03: Cotas Emitidas em Aporte = Valor Aporte / Valor Cota (D-1)
RN-04: Cotas Resgatadas em Saque = Valor Saque / Valor Cota (D-1)
RN-05: Rentabilidade = (Cota Atual / Cota Inicial) - 1
```

### 8.2 Cálculo de P&L

```
RN-06: P&L Realizado = Preço Venda - Preço Médio - Custos
RN-07: P&L Não-Realizado = (Preço Atual - Preço Médio) * Quantidade
RN-08: Preço Médio = Σ(Custo Aquisições) / Σ(Quantidades)
```

### 8.3 Cálculo de Risco

```
RN-09: VaR(95%) = μ - 1.645σ (paramétrico)
RN-10: Sharpe = (Rp - Rf) / σp
RN-11: Drawdown = (NAV Atual - NAV Máximo) / NAV Máximo
RN-12: Beta = Cov(Rp, Rm) / Var(Rm)
```

### 8.4 Conversão Cambial

```
RN-13: Posições USD convertidas para BRL usando PTAX do dia
RN-14: Consolidação sempre exibida em BRL
RN-15: Histórico mantém valor original + taxa de conversão
```

---

## 9. Cronograma de Entregas

### Fase 1: Foundation (Semana 1)
- Setup Supabase (schema, auth, storage)
- Setup Next.js + shadcn/ui
- Setup FastAPI + estrutura de projeto
- CI/CD básico

### Fase 2: Core Backend (Semanas 2-3)
- CRUD de contas e ativos
- CRUD de transações
- Cálculo de posições
- API de cash flows

### Fase 3: PDF Parser (Semanas 4-5)
- Integração Claude API
- Parser para extratos BTG
- Parser para notas de corretagem
- UI de validação

### Fase 4: Portfolio Engine (Semanas 6-7)
- Consolidação de posições
- Cálculo de P&L
- Mark-to-market

### Fase 5: Market Data (Semana 8)
- Integração LSEG
- Integração yfinance
- Scheduler de atualização
- Cache Redis

### Fase 6: Sistema de Cotas (Semana 9)
- Cálculo de NAV
- Emissão/resgate de cotas
- Histórico de rentabilidade

### Fase 7: Risk Module (Semana 10)
- VaR
- Sharpe/Sortino/Calmar
- Correlações
- Exposição

### Fase 8: Frontend (Semanas 11-13)
- Dashboard principal
- Tela de posições
- Tela de transações
- Tela de documentos
- Tela de risco
- Charts e visualizações

### Fase 9: Migração (Semana 14)
- Importação de 5 anos de histórico
- Validação de dados
- Ajustes finais

---

## 10. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Variação no formato de PDFs das corretoras | Alta | Alto | Prompts adaptativos + validação humana |
| Limites de rate da Claude API | Média | Médio | Queue com retry + batch processing |
| Indisponibilidade LSEG | Baixa | Médio | Fallback automático para yfinance |
| Complexidade na migração histórica | Alta | Alto | Script incremental com validação |
| Performance com 5 anos de dados | Média | Médio | Índices otimizados + agregações |

---

## 11. Métricas de Sucesso

| Métrica | Meta | Medição |
|---------|------|---------|
| Precisão do parsing | > 95% | Comparação com extrato original |
| Cobertura de ativos | 100% | Ativos com cotação atualizada |
| Divergência de NAV | < 0.1% | vs cálculo manual |
| Tempo de onboarding | < 1 hora | Primeira importação completa |
| Uptime | > 99% | Monitoramento contínuo |

---

## 12. Glossário

| Termo | Definição |
|-------|-----------|
| NAV | Net Asset Value - valor total do patrimônio |
| Cota | Unidade de participação no fundo próprio |
| P&L | Profit & Loss - lucro ou prejuízo |
| VaR | Value at Risk - perda máxima esperada |
| Sharpe | Retorno ajustado ao risco |
| Drawdown | Queda do pico ao vale |
| Mark-to-market | Avaliação a preço de mercado |
| PTAX | Taxa de câmbio oficial do Banco Central |

---

## 13. Aprovações

| Papel | Nome | Data |
|-------|------|------|
| Product Owner | Bigode | ___ |
| Tech Lead | Bigode | ___ |

---

*Documento vivo - última atualização: Janeiro 2026*
