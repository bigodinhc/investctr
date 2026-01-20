"use client";

import { useState } from "react";
import { Trash2, AlertCircle, ArrowUpDown } from "lucide-react";
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
import type { ParsedCashMovement } from "@/lib/api/types";

const MOVEMENT_TYPES: Record<string, { label: string; color: string }> = {
  deposit: { label: "Depósito", color: "success" },
  deposito: { label: "Depósito", color: "success" },
  aporte: { label: "Aporte", color: "success" },
  withdrawal: { label: "Saque", color: "destructive" },
  saque: { label: "Saque", color: "destructive" },
  resgate: { label: "Resgate", color: "destructive" },
  dividend: { label: "Dividendo", color: "info" },
  dividendo: { label: "Dividendo", color: "info" },
  jcp: { label: "JCP", color: "info" },
  jscp: { label: "JCP", color: "info" },
  interest: { label: "Juros", color: "info" },
  juros: { label: "Juros", color: "info" },
  rendimento: { label: "Rendimento", color: "info" },
  fee: { label: "Taxa", color: "warning" },
  taxa: { label: "Taxa", color: "warning" },
  tarifa: { label: "Tarifa", color: "warning" },
  tax: { label: "Imposto", color: "warning" },
  imposto: { label: "Imposto", color: "warning" },
  ir: { label: "IR", color: "warning" },
  iof: { label: "IOF", color: "warning" },
  settlement: { label: "Liquidação", color: "secondary" },
  liquidacao: { label: "Liquidação", color: "secondary" },
  rental_income: { label: "Aluguel", color: "info" },
  aluguel: { label: "Aluguel", color: "info" },
  other: { label: "Outro", color: "muted" },
};

interface SelectableCashMovement extends ParsedCashMovement {
  id: string;
  isSelected: boolean;
}

interface CashMovementsTableProps {
  items: ParsedCashMovement[];
  onSelectionChange?: (items: ParsedCashMovement[]) => void;
}

export function CashMovementsTable({ items, onSelectionChange }: CashMovementsTableProps) {
  const [movements, setMovements] = useState<SelectableCashMovement[]>(() =>
    items.map((item, i) => ({
      ...item,
      id: `cm-${i}`,
      isSelected: true,
    }))
  );

  const toggleSelect = (id: string) => {
    setMovements((prev) => {
      const updated = prev.map((m) =>
        m.id === id ? { ...m, isSelected: !m.isSelected } : m
      );
      onSelectionChange?.(
        updated.filter((m) => m.isSelected).map(({ id, isSelected, ...rest }) => rest)
      );
      return updated;
    });
  };

  const removeMovement = (id: string) => {
    setMovements((prev) => {
      const updated = prev.filter((m) => m.id !== id);
      onSelectionChange?.(
        updated.filter((m) => m.isSelected).map(({ id, isSelected, ...rest }) => rest)
      );
      return updated;
    });
  };

  const selectedCount = movements.filter((m) => m.isSelected).length;

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: "BRL",
    }).format(value);
  };

  const getMovementType = (type: string) => {
    const normalized = type.toLowerCase().replace(" ", "_");
    return MOVEMENT_TYPES[normalized] || { label: type, color: "muted" };
  };

  // Calculate totals
  const totals = movements
    .filter((m) => m.isSelected)
    .reduce(
      (acc, m) => {
        if (m.value > 0) {
          acc.inflows += m.value;
        } else {
          acc.outflows += Math.abs(m.value);
        }
        return acc;
      },
      { inflows: 0, outflows: 0 }
    );

  return (
    <Card variant="elevated">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="font-display text-xl flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
              <ArrowUpDown className="h-4 w-4 text-primary" />
            </div>
            MOVIMENTAÇÕES
          </CardTitle>
          <Badge variant="secondary">
            {selectedCount} de {movements.length} selecionadas
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {movements.length === 0 ? (
          <div className="text-center py-12">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-warning/10 mx-auto mb-4">
              <AlertCircle className="h-8 w-8 text-warning" />
            </div>
            <h3 className="font-display text-xl mb-2">Nenhuma movimentação</h3>
            <p className="text-foreground-muted">
              O documento não contém movimentações de caixa.
            </p>
          </div>
        ) : (
          <>
            {/* Summary */}
            <div className="flex flex-wrap gap-4 text-sm">
              <div className="flex items-center gap-2">
                <span className="text-foreground-muted">Entradas:</span>
                <span className="font-mono font-semibold text-positive">
                  {formatCurrency(totals.inflows)}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-foreground-muted">Saídas:</span>
                <span className="font-mono font-semibold text-negative">
                  {formatCurrency(totals.outflows)}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-foreground-muted">Líquido:</span>
                <span className={`font-mono font-semibold ${
                  totals.inflows - totals.outflows >= 0 ? "text-positive" : "text-negative"
                }`}>
                  {formatCurrency(totals.inflows - totals.outflows)}
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
                        checked={selectedCount === movements.length}
                        onChange={(e) =>
                          setMovements((prev) => {
                            const updated = prev.map((m) => ({ ...m, isSelected: e.target.checked }));
                            onSelectionChange?.(
                              updated.filter((m) => m.isSelected).map(({ id, isSelected, ...rest }) => rest)
                            );
                            return updated;
                          })
                        }
                        className="rounded border-border-subtle"
                      />
                    </TableHead>
                    <TableHead>Data</TableHead>
                    <TableHead>Tipo</TableHead>
                    <TableHead>Descrição</TableHead>
                    <TableHead>Ativo</TableHead>
                    <TableHead className="text-right">Valor</TableHead>
                    <TableHead className="w-[60px]"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {movements.map((movement) => {
                    const movementType = getMovementType(movement.type);
                    const isPositive = movement.value >= 0;

                    return (
                      <TableRow
                        key={movement.id}
                        className={!movement.isSelected ? "opacity-50" : ""}
                      >
                        <TableCell>
                          <input
                            type="checkbox"
                            checked={movement.isSelected}
                            onChange={() => toggleSelect(movement.id)}
                            className="rounded border-border-subtle"
                          />
                        </TableCell>
                        <TableCell className="font-mono text-sm">
                          {movement.date}
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant={
                              movementType.color === "success" ? "success" :
                              movementType.color === "destructive" ? "destructive" :
                              movementType.color === "info" ? "info" :
                              movementType.color === "warning" ? "warning" :
                              movementType.color === "muted" ? "muted" :
                              "secondary"
                            }
                          >
                            {movementType.label}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-foreground-muted max-w-[200px] truncate">
                          {movement.description || "-"}
                        </TableCell>
                        <TableCell className="font-mono text-sm">
                          {movement.ticker || "-"}
                        </TableCell>
                        <TableCell className={`text-right font-mono font-semibold ${
                          isPositive ? "text-positive" : "text-negative"
                        }`}>
                          {isPositive ? "+" : ""}{formatCurrency(movement.value)}
                        </TableCell>
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 hover:bg-destructive/10 hover:text-destructive"
                            onClick={() => removeMovement(movement.id)}
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
