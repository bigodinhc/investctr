"use client";

import { useState } from "react";
import { Trash2, AlertCircle, Building2 } from "lucide-react";
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
import type { ParsedFixedIncome } from "@/lib/api/types";

const FIXED_INCOME_TYPES: Record<string, { label: string; color: string }> = {
  cdb: { label: "CDB", color: "info" },
  lca: { label: "LCA", color: "success" },
  lci: { label: "LCI", color: "success" },
  lft: { label: "LFT", color: "warning" },
  ntnb: { label: "NTN-B", color: "warning" },
  ntnf: { label: "NTN-F", color: "warning" },
  lf: { label: "LF", color: "info" },
  debenture: { label: "Debênture", color: "secondary" },
  cri: { label: "CRI", color: "secondary" },
  cra: { label: "CRA", color: "secondary" },
  other: { label: "Outro", color: "muted" },
};

const INDEXER_LABELS: Record<string, string> = {
  cdi: "CDI",
  selic: "SELIC",
  ipca: "IPCA+",
  igpm: "IGP-M+",
  prefixado: "Pré",
  other: "Outro",
};

interface SelectableFixedIncome extends ParsedFixedIncome {
  id: string;
  isSelected: boolean;
}

interface FixedIncomeTableProps {
  items: ParsedFixedIncome[];
  onSelectionChange?: (items: ParsedFixedIncome[]) => void;
}

export function FixedIncomeTable({ items, onSelectionChange }: FixedIncomeTableProps) {
  const [positions, setPositions] = useState<SelectableFixedIncome[]>(() =>
    items.map((item, i) => ({
      ...item,
      id: `fi-${i}`,
      isSelected: true,
    }))
  );

  const toggleSelect = (id: string) => {
    setPositions((prev) => {
      const updated = prev.map((p) =>
        p.id === id ? { ...p, isSelected: !p.isSelected } : p
      );
      onSelectionChange?.(
        updated.filter((p) => p.isSelected).map(({ id, isSelected, ...rest }) => rest)
      );
      return updated;
    });
  };

  const removePosition = (id: string) => {
    setPositions((prev) => {
      const updated = prev.filter((p) => p.id !== id);
      onSelectionChange?.(
        updated.filter((p) => p.isSelected).map(({ id, isSelected, ...rest }) => rest)
      );
      return updated;
    });
  };

  const selectedCount = positions.filter((p) => p.isSelected).length;

  const formatCurrency = (value: number | null) => {
    if (value === null) return "-";
    return new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: "BRL",
    }).format(value);
  };

  const formatNumber = (value: number | null, decimals = 2) => {
    if (value === null) return "-";
    return new Intl.NumberFormat("pt-BR", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(value);
  };

  const formatDate = (date: string | null) => {
    if (!date) return "-";
    return new Date(date).toLocaleDateString("pt-BR");
  };

  const getFixedIncomeType = (type: string) => {
    return FIXED_INCOME_TYPES[type.toLowerCase()] || FIXED_INCOME_TYPES.other;
  };

  const formatRate = (indexer: string | null, rate: number | null) => {
    if (!indexer && !rate) return "-";
    const indexerLabel = indexer ? (INDEXER_LABELS[indexer.toLowerCase()] || indexer) : "";
    const rateValue = rate ? formatNumber(rate, 2) + "%" : "";

    if (indexer?.toLowerCase() === "prefixado") {
      return rateValue || "Pré";
    }
    if (indexer?.toLowerCase() === "ipca" || indexer?.toLowerCase() === "igpm") {
      return `${indexerLabel}${rateValue ? " " + rateValue : ""}`;
    }
    return rateValue ? `${rateValue} ${indexerLabel}`.trim() : indexerLabel;
  };

  return (
    <Card variant="elevated">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="font-display text-xl flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-info/10">
              <Building2 className="h-4 w-4 text-info" />
            </div>
            RENDA FIXA
          </CardTitle>
          <Badge variant="secondary">
            {selectedCount} de {positions.length} selecionadas
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {positions.length === 0 ? (
          <div className="text-center py-12">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-warning/10 mx-auto mb-4">
              <AlertCircle className="h-8 w-8 text-warning" />
            </div>
            <h3 className="font-display text-xl mb-2">Nenhuma posição de renda fixa</h3>
            <p className="text-foreground-muted">
              O documento não contém posições de renda fixa.
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
                      checked={selectedCount === positions.length}
                      onChange={(e) =>
                        setPositions((prev) => {
                          const updated = prev.map((p) => ({ ...p, isSelected: e.target.checked }));
                          onSelectionChange?.(
                            updated.filter((p) => p.isSelected).map(({ id, isSelected, ...rest }) => rest)
                          );
                          return updated;
                        })
                      }
                      className="rounded border-border-subtle"
                    />
                  </TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Ativo</TableHead>
                  <TableHead>Emissor</TableHead>
                  <TableHead className="text-right">Taxa</TableHead>
                  <TableHead className="text-right">Qtd</TableHead>
                  <TableHead className="text-right">Valor</TableHead>
                  <TableHead>Vencimento</TableHead>
                  <TableHead className="w-[60px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {positions.map((pos) => {
                  const fiType = getFixedIncomeType(pos.asset_type);

                  return (
                    <TableRow
                      key={pos.id}
                      className={!pos.isSelected ? "opacity-50" : ""}
                    >
                      <TableCell>
                        <input
                          type="checkbox"
                          checked={pos.isSelected}
                          onChange={() => toggleSelect(pos.id)}
                          className="rounded border-border-subtle"
                        />
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            fiType.color === "success" ? "success" :
                            fiType.color === "info" ? "info" :
                            fiType.color === "warning" ? "warning" :
                            fiType.color === "muted" ? "muted" :
                            "secondary"
                          }
                        >
                          {fiType.label}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono font-semibold text-sm max-w-[200px] truncate">
                        {pos.asset_name}
                      </TableCell>
                      <TableCell className="text-sm text-foreground-muted max-w-[150px] truncate">
                        {pos.issuer || "-"}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        {formatRate(pos.indexer, pos.rate_percent)}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        {formatNumber(pos.quantity, 4)}
                      </TableCell>
                      <TableCell className="text-right font-mono font-semibold">
                        {formatCurrency(pos.total_value)}
                      </TableCell>
                      <TableCell className="font-mono text-sm text-foreground-muted">
                        {formatDate(pos.maturity_date)}
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 hover:bg-destructive/10 hover:text-destructive"
                          onClick={() => removePosition(pos.id)}
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
