"use client";

import { FileText, TrendingUp, Banknote, Building2, RefreshCw, ArrowUpDown } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ParsedDocumentData } from "@/lib/api/types";

interface DocumentSummaryProps {
  data: ParsedDocumentData;
}

export function DocumentSummary({ data }: DocumentSummaryProps) {
  const toNumber = (value: number | string | null | undefined): number => {
    if (value === null || value === undefined) return 0;
    const num = typeof value === "string" ? parseFloat(value) : value;
    return isNaN(num) ? 0 : num;
  };

  const formatCurrency = (value: number | string | null | undefined) => {
    if (value === null || value === undefined) return "-";
    const num = typeof value === "string" ? parseFloat(value) : value;
    if (isNaN(num)) return "-";
    return new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: "BRL",
    }).format(num);
  };

  const transactionsCount = data.transactions?.length || 0;
  const fixedIncomeCount = data.fixed_income_positions?.length || 0;
  const stockLendingCount = data.stock_lending?.length || 0;
  const cashMovementsCount = data.cash_movements?.length || 0;

  const consolidated = data.consolidated_position;

  // Calculate totals from transactions
  const transactionsTotals = data.transactions?.reduce(
    (acc, t) => {
      const total = toNumber(t.total);
      if (t.type === "buy" || t.type === "compra") {
        acc.buys += total;
      } else if (t.type === "sell" || t.type === "venda") {
        acc.sells += total;
      } else if (t.type === "dividend" || t.type === "dividendo" || t.type === "jcp") {
        acc.income += total;
      }
      return acc;
    },
    { buys: 0, sells: 0, income: 0 }
  ) || { buys: 0, sells: 0, income: 0 };

  // Calculate fixed income total
  const fixedIncomeTotal = data.fixed_income_positions?.reduce(
    (acc, fi) => acc + toNumber(fi.total_value),
    0
  ) || 0;

  // Calculate stock lending total
  const stockLendingTotal = data.stock_lending?.reduce(
    (acc, sl) => acc + toNumber(sl.total),
    0
  ) || 0;

  // Calculate cash movements totals
  const cashTotals = data.cash_movements?.reduce(
    (acc, cm) => {
      const value = toNumber(cm.value);
      if (value >= 0) {
        acc.inflows += value;
      } else {
        acc.outflows += Math.abs(value);
      }
      return acc;
    },
    { inflows: 0, outflows: 0 }
  ) || { inflows: 0, outflows: 0 };

  return (
    <Card variant="elevated">
      <CardHeader className="pb-4">
        <CardTitle className="font-display text-xl flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
            <FileText className="h-4 w-4 text-primary" />
          </div>
          RESUMO DO DOCUMENTO
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Document Info */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          {data.period && (
            <div>
              <span className="text-foreground-muted block">Período</span>
              <span className="font-semibold">{data.period.start} a {data.period.end}</span>
            </div>
          )}
          {data.account_number && (
            <div>
              <span className="text-foreground-muted block">Conta</span>
              <span className="font-mono font-semibold">{data.account_number}</span>
            </div>
          )}
          <div>
            <span className="text-foreground-muted block">Tipo</span>
            <span className="font-semibold capitalize">{data.document_type}</span>
          </div>
        </div>

        {/* Data Counts */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="flex items-center gap-3 p-3 rounded-lg bg-surface-elevated">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-positive/10">
              <TrendingUp className="h-5 w-5 text-positive" />
            </div>
            <div>
              <div className="text-2xl font-display font-semibold">{transactionsCount}</div>
              <div className="text-sm text-foreground-muted">Transações</div>
            </div>
          </div>

          <div className="flex items-center gap-3 p-3 rounded-lg bg-surface-elevated">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-info/10">
              <Building2 className="h-5 w-5 text-info" />
            </div>
            <div>
              <div className="text-2xl font-display font-semibold">{fixedIncomeCount}</div>
              <div className="text-sm text-foreground-muted">Renda Fixa</div>
            </div>
          </div>

          <div className="flex items-center gap-3 p-3 rounded-lg bg-surface-elevated">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-warning/10">
              <RefreshCw className="h-5 w-5 text-warning" />
            </div>
            <div>
              <div className="text-2xl font-display font-semibold">{stockLendingCount}</div>
              <div className="text-sm text-foreground-muted">Aluguel</div>
            </div>
          </div>

          <div className="flex items-center gap-3 p-3 rounded-lg bg-surface-elevated">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
              <ArrowUpDown className="h-5 w-5 text-primary" />
            </div>
            <div>
              <div className="text-2xl font-display font-semibold">{cashMovementsCount}</div>
              <div className="text-sm text-foreground-muted">Movimentações</div>
            </div>
          </div>
        </div>

        {/* Consolidated Position */}
        {consolidated && (
          <div className="space-y-3">
            <h4 className="font-display text-sm text-foreground-muted uppercase tracking-wide">
              Posição Consolidada
            </h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {consolidated.total_stocks !== null && (
                <div className="p-3 rounded-lg bg-surface-elevated">
                  <div className="text-sm text-foreground-muted mb-1">Ações/FIIs</div>
                  <div className="text-lg font-mono font-semibold">
                    {formatCurrency(consolidated.total_stocks)}
                  </div>
                </div>
              )}
              {consolidated.total_fixed_income !== null && (
                <div className="p-3 rounded-lg bg-surface-elevated">
                  <div className="text-sm text-foreground-muted mb-1">Renda Fixa</div>
                  <div className="text-lg font-mono font-semibold">
                    {formatCurrency(consolidated.total_fixed_income)}
                  </div>
                </div>
              )}
              {consolidated.total_cash !== null && (
                <div className="p-3 rounded-lg bg-surface-elevated">
                  <div className="text-sm text-foreground-muted mb-1">Caixa</div>
                  <div className="text-lg font-mono font-semibold">
                    {formatCurrency(consolidated.total_cash)}
                  </div>
                </div>
              )}
              {consolidated.grand_total !== null && (
                <div className="p-3 rounded-lg bg-primary/5 border border-primary/20">
                  <div className="text-sm text-foreground-muted mb-1">Total</div>
                  <div className="text-lg font-mono font-semibold text-primary">
                    {formatCurrency(consolidated.grand_total)}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Calculated Totals */}
        <div className="space-y-3">
          <h4 className="font-display text-sm text-foreground-muted uppercase tracking-wide">
            Totais Extraídos
          </h4>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 text-sm">
            {transactionsTotals.buys > 0 && (
              <div>
                <span className="text-foreground-muted block">Compras</span>
                <span className="font-mono font-semibold text-negative">
                  {formatCurrency(transactionsTotals.buys)}
                </span>
              </div>
            )}
            {transactionsTotals.sells > 0 && (
              <div>
                <span className="text-foreground-muted block">Vendas</span>
                <span className="font-mono font-semibold text-positive">
                  {formatCurrency(transactionsTotals.sells)}
                </span>
              </div>
            )}
            {transactionsTotals.income > 0 && (
              <div>
                <span className="text-foreground-muted block">Proventos</span>
                <span className="font-mono font-semibold text-positive">
                  {formatCurrency(transactionsTotals.income)}
                </span>
              </div>
            )}
            {fixedIncomeTotal > 0 && (
              <div>
                <span className="text-foreground-muted block">Renda Fixa</span>
                <span className="font-mono font-semibold">
                  {formatCurrency(fixedIncomeTotal)}
                </span>
              </div>
            )}
            {stockLendingTotal > 0 && (
              <div>
                <span className="text-foreground-muted block">Aluguel</span>
                <span className="font-mono font-semibold text-positive">
                  {formatCurrency(stockLendingTotal)}
                </span>
              </div>
            )}
            {(cashTotals.inflows > 0 || cashTotals.outflows > 0) && (
              <div>
                <span className="text-foreground-muted block">Mov. Líquido</span>
                <span className={`font-mono font-semibold ${
                  cashTotals.inflows - cashTotals.outflows >= 0 ? "text-positive" : "text-negative"
                }`}>
                  {formatCurrency(cashTotals.inflows - cashTotals.outflows)}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Original Summary from parsing */}
        {data.summary && Object.keys(data.summary).length > 0 && (
          <div className="space-y-3">
            <h4 className="font-display text-sm text-foreground-muted uppercase tracking-wide">
              Resumo Original
            </h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              {Object.entries(data.summary).map(([key, value]) => (
                <div key={key}>
                  <span className="text-foreground-muted block capitalize">
                    {key.replace(/_/g, " ")}
                  </span>
                  <span className="font-mono font-semibold">
                    {typeof value === "number" ? formatCurrency(value) : String(value)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
