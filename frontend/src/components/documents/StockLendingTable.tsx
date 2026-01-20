"use client";

import { useState } from "react";
import { Trash2, AlertCircle, RefreshCw } from "lucide-react";
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
import type { ParsedStockLending } from "@/lib/api/types";

const LENDING_TYPES: Record<string, { label: string; color: string }> = {
  lending_out: { label: "Empréstimo", color: "warning" },
  lending_return: { label: "Devolução", color: "success" },
  rental_income: { label: "Renda", color: "info" },
};

interface SelectableStockLending extends ParsedStockLending {
  id: string;
  isSelected: boolean;
}

interface StockLendingTableProps {
  items: ParsedStockLending[];
  onSelectionChange?: (items: ParsedStockLending[]) => void;
}

export function StockLendingTable({ items, onSelectionChange }: StockLendingTableProps) {
  const [lendings, setLendings] = useState<SelectableStockLending[]>(() =>
    items.map((item, i) => ({
      ...item,
      id: `sl-${i}`,
      isSelected: true,
    }))
  );

  const toggleSelect = (id: string) => {
    setLendings((prev) => {
      const updated = prev.map((l) =>
        l.id === id ? { ...l, isSelected: !l.isSelected } : l
      );
      onSelectionChange?.(
        updated.filter((l) => l.isSelected).map(({ id, isSelected, ...rest }) => rest)
      );
      return updated;
    });
  };

  const removeLending = (id: string) => {
    setLendings((prev) => {
      const updated = prev.filter((l) => l.id !== id);
      onSelectionChange?.(
        updated.filter((l) => l.isSelected).map(({ id, isSelected, ...rest }) => rest)
      );
      return updated;
    });
  };

  const selectedCount = lendings.filter((l) => l.isSelected).length;

  const formatCurrency = (value: number | null) => {
    if (value === null) return "-";
    return new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: "BRL",
    }).format(value);
  };

  const formatNumber = (value: number | null, decimals = 0) => {
    if (value === null) return "-";
    return new Intl.NumberFormat("pt-BR", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(value);
  };

  const formatPercent = (value: number | null) => {
    if (value === null) return "-";
    return new Intl.NumberFormat("pt-BR", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value) + "%";
  };

  const getLendingType = (type: string) => {
    return LENDING_TYPES[type.toLowerCase()] || { label: type, color: "secondary" };
  };

  return (
    <Card variant="elevated">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="font-display text-xl flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-warning/10">
              <RefreshCw className="h-4 w-4 text-warning" />
            </div>
            ALUGUEL DE AÇÕES
          </CardTitle>
          <Badge variant="secondary">
            {selectedCount} de {lendings.length} selecionadas
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {lendings.length === 0 ? (
          <div className="text-center py-12">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-warning/10 mx-auto mb-4">
              <AlertCircle className="h-8 w-8 text-warning" />
            </div>
            <h3 className="font-display text-xl mb-2">Nenhuma operação de aluguel</h3>
            <p className="text-foreground-muted">
              O documento não contém operações de aluguel de ações.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[50px]">
                    <input
                      type="checkbox"
                      checked={selectedCount === lendings.length}
                      onChange={(e) =>
                        setLendings((prev) => {
                          const updated = prev.map((l) => ({ ...l, isSelected: e.target.checked }));
                          onSelectionChange?.(
                            updated.filter((l) => l.isSelected).map(({ id, isSelected, ...rest }) => rest)
                          );
                          return updated;
                        })
                      }
                      className="rounded border-border-subtle"
                    />
                  </TableHead>
                  <TableHead>Data</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Ativo</TableHead>
                  <TableHead className="text-right">Quantidade</TableHead>
                  <TableHead className="text-right">Taxa a.a.</TableHead>
                  <TableHead className="text-right">Valor</TableHead>
                  <TableHead className="w-[60px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {lendings.map((lending) => {
                  const lendingType = getLendingType(lending.type);

                  return (
                    <TableRow
                      key={lending.id}
                      className={!lending.isSelected ? "opacity-50" : ""}
                    >
                      <TableCell>
                        <input
                          type="checkbox"
                          checked={lending.isSelected}
                          onChange={() => toggleSelect(lending.id)}
                          className="rounded border-border-subtle"
                        />
                      </TableCell>
                      <TableCell className="font-mono text-sm">
                        {lending.date}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            lendingType.color === "success" ? "success" :
                            lendingType.color === "info" ? "info" :
                            lendingType.color === "warning" ? "warning" :
                            "secondary"
                          }
                        >
                          {lendingType.label}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono font-semibold">
                        {lending.ticker}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {formatNumber(lending.quantity)}
                      </TableCell>
                      <TableCell className="text-right font-mono text-foreground-muted">
                        {formatPercent(lending.rate_percent)}
                      </TableCell>
                      <TableCell className="text-right font-mono font-semibold">
                        {formatCurrency(lending.total)}
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 hover:bg-destructive/10 hover:text-destructive"
                          onClick={() => removeLending(lending.id)}
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
        )}
      </CardContent>
    </Card>
  );
}
