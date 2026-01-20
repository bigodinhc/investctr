"use client";

import { useState } from "react";
import { Trash2, AlertCircle, Briefcase } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ParsedInvestmentFund } from "@/lib/api/types";

interface SelectableInvestmentFund extends ParsedInvestmentFund {
  id: string;
  isSelected: boolean;
}

interface InvestmentFundsTableProps {
  items: ParsedInvestmentFund[];
  onSelectionChange?: (items: ParsedInvestmentFund[]) => void;
}

export function InvestmentFundsTable({ items, onSelectionChange }: InvestmentFundsTableProps) {
  const [funds, setFunds] = useState<SelectableInvestmentFund[]>(() =>
    items.map((item, i) => ({
      ...item,
      id: `fund-${i}`,
      isSelected: true,
    }))
  );

  const toggleSelect = (id: string) => {
    setFunds((prev) => {
      const updated = prev.map((f) =>
        f.id === id ? { ...f, isSelected: !f.isSelected } : f
      );
      onSelectionChange?.(
        updated.filter((f) => f.isSelected).map(({ id, isSelected, ...rest }) => rest)
      );
      return updated;
    });
  };

  const removeFund = (id: string) => {
    setFunds((prev) => {
      const updated = prev.filter((f) => f.id !== id);
      onSelectionChange?.(
        updated.filter((f) => f.isSelected).map(({ id, isSelected, ...rest }) => rest)
      );
      return updated;
    });
  };

  const selectedCount = funds.filter((f) => f.isSelected).length;

  const formatCurrency = (value: number | string | null | undefined) => {
    if (value === null || value === undefined) return "-";
    const num = typeof value === "string" ? parseFloat(value) : value;
    if (isNaN(num)) return "-";
    return new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: "BRL",
    }).format(num);
  };

  const formatNumber = (value: number | string | null | undefined, decimals = 2) => {
    if (value === null || value === undefined) return "-";
    const num = typeof value === "string" ? parseFloat(value) : value;
    if (isNaN(num)) return "-";
    return new Intl.NumberFormat("pt-BR", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(num);
  };

  const formatPercent = (value: number | string | null | undefined) => {
    if (value === null || value === undefined) return "-";
    const num = typeof value === "string" ? parseFloat(value) : value;
    if (isNaN(num)) return "-";
    const sign = num >= 0 ? "+" : "";
    return sign + new Intl.NumberFormat("pt-BR", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(num) + "%";
  };

  // Calculate total selected
  const totalGross = funds
    .filter((f) => f.isSelected)
    .reduce((acc, f) => {
      const val = typeof f.gross_balance === "string" ? parseFloat(f.gross_balance) : f.gross_balance;
      return acc + (isNaN(val) ? 0 : val);
    }, 0);

  const totalNet = funds
    .filter((f) => f.isSelected)
    .reduce((acc, f) => {
      if (f.net_balance === null || f.net_balance === undefined) return acc;
      const val = typeof f.net_balance === "string" ? parseFloat(f.net_balance) : f.net_balance;
      return acc + (isNaN(val) ? 0 : val);
    }, 0);

  return (
    <Card variant="elevated">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="font-display text-xl flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
              <Briefcase className="h-4 w-4 text-primary" />
            </div>
            FUNDOS DE INVESTIMENTO
          </CardTitle>
          <Badge variant="secondary">
            {selectedCount} de {funds.length} selecionados
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {funds.length === 0 ? (
          <div className="text-center py-12">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-warning/10 mx-auto mb-4">
              <AlertCircle className="h-8 w-8 text-warning" />
            </div>
            <h3 className="font-display text-xl mb-2">Nenhum fundo de investimento</h3>
            <p className="text-foreground-muted">
              O documento não contém posições em fundos de investimento.
            </p>
          </div>
        ) : (
          <>
            {/* Summary */}
            <div className="flex flex-wrap gap-4 text-sm">
              <div className="flex items-center gap-2">
                <span className="text-foreground-muted">Saldo Bruto Total:</span>
                <span className="font-mono font-semibold">
                  {formatCurrency(totalGross)}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-foreground-muted">Saldo Líquido Total:</span>
                <span className="font-mono font-semibold text-positive">
                  {formatCurrency(totalNet)}
                </span>
              </div>
            </div>

            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[50px]">
                      <input
                        type="checkbox"
                        checked={selectedCount === funds.length}
                        onChange={(e) =>
                          setFunds((prev) => {
                            const updated = prev.map((f) => ({ ...f, isSelected: e.target.checked }));
                            onSelectionChange?.(
                              updated.filter((f) => f.isSelected).map(({ id, isSelected, ...rest }) => rest)
                            );
                            return updated;
                          })
                        }
                        className="rounded border-border-subtle"
                      />
                    </TableHead>
                    <TableHead>Fundo</TableHead>
                    <TableHead className="text-right">Cotas</TableHead>
                    <TableHead className="text-right">Valor Cota</TableHead>
                    <TableHead className="text-right">Saldo Bruto</TableHead>
                    <TableHead className="text-right">Prov. IR</TableHead>
                    <TableHead className="text-right">Saldo Líquido</TableHead>
                    <TableHead className="text-right">Rent.</TableHead>
                    <TableHead className="w-[60px]"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {funds.map((fund) => {
                    const perfNum = fund.performance_pct
                      ? (typeof fund.performance_pct === "string" ? parseFloat(fund.performance_pct) : fund.performance_pct)
                      : null;
                    const isPositivePerf = perfNum !== null && !isNaN(perfNum) && perfNum >= 0;

                    return (
                      <TableRow
                        key={fund.id}
                        className={!fund.isSelected ? "opacity-50" : ""}
                      >
                        <TableCell>
                          <input
                            type="checkbox"
                            checked={fund.isSelected}
                            onChange={() => toggleSelect(fund.id)}
                            className="rounded border-border-subtle"
                          />
                        </TableCell>
                        <TableCell>
                          <div className="max-w-[280px]">
                            <div className="font-semibold text-sm truncate" title={fund.fund_name}>
                              {fund.fund_name}
                            </div>
                            {fund.cnpj && (
                              <div className="text-xs text-foreground-muted font-mono">
                                {fund.cnpj}
                              </div>
                            )}
                          </div>
                        </TableCell>
                        <TableCell className="text-right font-mono text-sm">
                          {formatNumber(fund.quota_quantity, 4)}
                        </TableCell>
                        <TableCell className="text-right font-mono text-sm">
                          {formatCurrency(fund.quota_price)}
                        </TableCell>
                        <TableCell className="text-right font-mono font-semibold">
                          {formatCurrency(fund.gross_balance)}
                        </TableCell>
                        <TableCell className="text-right font-mono text-sm text-negative">
                          {fund.ir_provision ? `-${formatCurrency(fund.ir_provision).replace('R$', 'R$ ')}` : "-"}
                        </TableCell>
                        <TableCell className="text-right font-mono font-semibold text-positive">
                          {formatCurrency(fund.net_balance)}
                        </TableCell>
                        <TableCell className={`text-right font-mono text-sm font-semibold ${
                          isPositivePerf ? "text-positive" : "text-negative"
                        }`}>
                          {formatPercent(fund.performance_pct)}
                        </TableCell>
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 hover:bg-destructive/10 hover:text-destructive"
                            onClick={() => removeFund(fund.id)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
