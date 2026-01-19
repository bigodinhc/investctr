"use client";

import { useState } from "react";
import {
  BarChart3,
  Building2,
  Clock,
  Filter,
  Landmark,
  Loader2,
  PieChart,
  RefreshCw,
  TrendingDown,
  TrendingUp,
  X,
} from "lucide-react";
import {
  usePositions,
  useConsolidatedPositions,
  usePositionsSummary,
  useRecalculatePositions,
} from "@/hooks/use-positions";
import { useSyncQuotes } from "@/hooks/use-quotes";
import { useAccounts } from "@/hooks/use-accounts";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { formatCurrency, formatQuantity, formatNumber, formatPercent, formatDate, getPnLColor } from "@/lib/format";
import type { AssetType, PositionWithMarketData } from "@/lib/api/types";

const ASSET_TYPE_LABELS: Record<AssetType, { label: string; icon: typeof Building2 }> = {
  stock: { label: "Ações", icon: TrendingUp },
  etf: { label: "ETFs", icon: BarChart3 },
  reit: { label: "REITs", icon: Building2 },
  bdr: { label: "BDRs", icon: Landmark },
  fund: { label: "Fundos", icon: PieChart },
  fixed_income: { label: "Renda Fixa", icon: Landmark },
  crypto: { label: "Cripto", icon: BarChart3 },
  option: { label: "Opções", icon: TrendingUp },
  future: { label: "Futuros", icon: TrendingUp },
  currency: { label: "Moedas", icon: Landmark },
  bond: { label: "Renda Fixa", icon: Landmark },
  treasury: { label: "Tesouro", icon: Landmark },
  other: { label: "Outros", icon: BarChart3 },
};

export default function PositionsPage() {
  const [filters, setFilters] = useState<{
    account_id?: string;
    asset_type?: AssetType;
  }>({});
  const [isFiltersOpen, setIsFiltersOpen] = useState(false);
  const [viewMode, setViewMode] = useState<"detailed" | "consolidated">("detailed");

  const { data: positionsData, isLoading, error, refetch } = usePositions(filters);
  const { data: consolidatedData, isLoading: isConsolidatedLoading } = useConsolidatedPositions(
    filters.asset_type
  );
  const { data: summaryData } = usePositionsSummary(filters.account_id);
  const { data: accountsData } = useAccounts();
  const recalculatePositions = useRecalculatePositions();
  const syncQuotes = useSyncQuotes();

  const accounts = accountsData?.items || [];

  const data = viewMode === "detailed" ? positionsData : consolidatedData;
  const positions = viewMode === "detailed"
    ? positionsData?.items || []
    : consolidatedData?.items || [];

  // Get the most recent price_updated_at from positions
  const lastPriceUpdate = positions.reduce((latest, pos) => {
    const position = pos as PositionWithMarketData;
    if (position.price_updated_at) {
      const posDate = new Date(position.price_updated_at);
      if (!latest || posDate > latest) {
        return posDate;
      }
    }
    return latest;
  }, null as Date | null);

  const hasFilters = Object.values(filters).some((v) => v);

  const clearFilters = () => {
    setFilters({});
  };

  if (error) {
    return (
      <div className="space-y-8 animate-fade-in">
        <Card variant="elevated">
          <CardContent className="p-8">
            <div className="flex items-center gap-4 text-destructive">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-destructive/10">
                <X className="h-6 w-6" />
              </div>
              <div>
                <p className="font-semibold">Erro ao carregar posições</p>
                <p className="text-sm text-foreground-muted">{error.message}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="space-y-1">
          <h1 className="font-display text-3xl tracking-tight text-foreground">
            Posições
          </h1>
          <p className="text-foreground-muted">
            Visualize seu portfólio e posições atuais
          </p>
        </div>
        <div className="flex flex-col sm:flex-row gap-2 sm:items-center">
          {/* Last update indicator */}
          {lastPriceUpdate && (
            <div className="flex items-center gap-1.5 text-sm text-foreground-muted mr-2">
              <Clock className="h-4 w-4" />
              <span>Cotacoes: {formatDate(lastPriceUpdate, "relative")}</span>
            </div>
          )}
          <div className="flex gap-2">
            <Button
              variant={hasFilters ? "default" : "outline"}
              size="lg"
              onClick={() => setIsFiltersOpen(!isFiltersOpen)}
              aria-label="Abrir filtros"
            >
              <Filter className="h-4 w-4 sm:mr-2" />
              <span className="hidden sm:inline">Filtros</span>
              {hasFilters && (
                <Badge variant="muted" className="ml-1 sm:ml-2">
                  {Object.values(filters).filter((v) => v).length}
                </Badge>
              )}
            </Button>
            <Button
              variant="outline"
              size="lg"
              onClick={() => syncQuotes.mutate()}
              disabled={syncQuotes.isPending}
              aria-label="Atualizar cotacoes"
            >
              {syncQuotes.isPending ? (
                <Loader2 className="h-4 w-4 sm:mr-2 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4 sm:mr-2" />
              )}
              <span className="hidden sm:inline">
                {syncQuotes.isPending ? "Atualizando..." : "Atualizar"}
              </span>
            </Button>
          </div>
        </div>
      </div>

      {/* Filters Panel */}
      {isFiltersOpen && (
        <Card variant="elevated" className="animate-slide-down">
          <CardContent className="p-4">
            <div className="flex flex-wrap gap-4">
              <div className="flex-1 min-w-[200px]">
                <label className="text-sm font-medium mb-1 block">Visualização</label>
                <Select
                  value={viewMode}
                  onValueChange={(value) => setViewMode(value as "detailed" | "consolidated")}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="detailed">Por Conta (Detalhado)</SelectItem>
                    <SelectItem value="consolidated">Consolidado</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              {viewMode === "detailed" && (
                <div className="flex-1 min-w-[200px]">
                  <label className="text-sm font-medium mb-1 block">Conta</label>
                  <Select
                    value={filters.account_id || "all"}
                    onValueChange={(value) =>
                      setFilters({ ...filters, account_id: value === "all" ? undefined : value })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Todas as contas" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Todas as contas</SelectItem>
                      {accounts.map((account) => (
                        <SelectItem key={account.id} value={account.id}>
                          {account.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}
              <div className="flex-1 min-w-[200px]">
                <label className="text-sm font-medium mb-1 block">Tipo de Ativo</label>
                <Select
                  value={filters.asset_type || "all"}
                  onValueChange={(value) =>
                    setFilters({
                      ...filters,
                      asset_type: value === "all" ? undefined : (value as AssetType),
                    })
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Todos os tipos" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todos os tipos</SelectItem>
                    {Object.entries(ASSET_TYPE_LABELS).map(([value, { label }]) => (
                      <SelectItem key={value} value={value}>
                        {label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              {hasFilters && (
                <div className="flex items-end">
                  <Button variant="ghost" onClick={clearFilters}>
                    <X className="h-4 w-4 mr-2" />
                    Limpar
                  </Button>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4">
        <Card variant="elevated" className="p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-background-surface">
              <PieChart className="h-5 w-5 text-foreground" />
            </div>
            <div>
              <p className="text-sm text-foreground-muted">Posições</p>
              <p className="font-mono text-2xl font-semibold">
                {isLoading ? "-" : summaryData?.total_positions || 0}
              </p>
            </div>
          </div>
        </Card>
        <Card variant="elevated" className="p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-info/10">
              <Landmark className="h-5 w-5 text-info" />
            </div>
            <div>
              <p className="text-sm text-foreground-muted">Custo Total</p>
              <p className="font-mono text-xl font-semibold">
                {formatCurrency(summaryData?.total_cost || positionsData?.total_cost || null)}
              </p>
            </div>
          </div>
        </Card>
        <Card variant="elevated" className="p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-background-surface">
              <BarChart3 className="h-5 w-5 text-foreground" />
            </div>
            <div>
              <p className="text-sm text-foreground-muted">Valor de Mercado</p>
              <p className="font-mono text-xl font-semibold">
                {formatCurrency(
                  summaryData?.total_market_value ||
                    positionsData?.total_market_value ||
                    null
                )}
              </p>
            </div>
          </div>
        </Card>
        <Card variant="elevated" className="p-4">
          <div className="flex items-center gap-3">
            <div
              className={`flex h-10 w-10 items-center justify-center rounded-lg ${
                parseFloat(positionsData?.total_unrealized_pnl || "0") >= 0
                  ? "bg-success/10"
                  : "bg-destructive/10"
              }`}
            >
              {parseFloat(positionsData?.total_unrealized_pnl || "0") >= 0 ? (
                <TrendingUp className="h-5 w-5 text-success" />
              ) : (
                <TrendingDown className="h-5 w-5 text-destructive" />
              )}
            </div>
            <div>
              <p className="text-sm text-foreground-muted">P&L Não Realizado</p>
              <p
                className={`font-mono text-xl font-semibold ${getPnLColor(
                  positionsData?.total_unrealized_pnl || null
                )}`}
              >
                {formatCurrency(positionsData?.total_unrealized_pnl || null)}
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Allocation by Asset Type */}
      {summaryData?.by_asset_type && summaryData.by_asset_type.length > 0 && (
        <Card variant="elevated">
          <CardHeader className="pb-4">
            <CardTitle className="font-display text-xl flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-background-surface">
                <PieChart className="h-4 w-4 text-foreground" />
              </div>
              ALOCAÇÃO POR TIPO
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3 sm:gap-4">
              {summaryData.by_asset_type.map((item) => {
                const typeInfo = ASSET_TYPE_LABELS[item.asset_type] || ASSET_TYPE_LABELS.other;
                const Icon = typeInfo.icon;
                return (
                  <div
                    key={item.asset_type}
                    className="p-4 rounded-lg bg-background-surface border border-border-subtle"
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <Icon className="h-4 w-4 text-foreground" />
                      <span className="text-sm font-medium">{typeInfo.label}</span>
                    </div>
                    <p className="font-mono text-lg font-semibold">
                      {formatCurrency(item.total_cost)}
                    </p>
                    {item.allocation_pct && (
                      <p className="text-sm text-foreground-muted">
                        {formatNumber(item.allocation_pct)}% do total
                      </p>
                    )}
                    <p className="text-xs text-foreground-dim">
                      {item.positions_count} {item.positions_count === 1 ? "posição" : "posições"}
                    </p>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Positions Table */}
      <Card variant="elevated">
        <CardHeader className="pb-4">
          <CardTitle className="font-display text-xl flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-background-surface">
              <TrendingUp className="h-4 w-4 text-foreground" />
            </div>
            {viewMode === "detailed" ? "MINHAS POSIÇÕES" : "POSIÇÕES CONSOLIDADAS"}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading || isConsolidatedLoading ? (
            <div className="space-y-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="flex items-center gap-4 p-4">
                  <div className="h-10 w-10 skeleton rounded-lg" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 w-32 skeleton rounded" />
                    <div className="h-3 w-24 skeleton rounded" />
                  </div>
                  <div className="h-4 w-20 skeleton rounded" />
                  <div className="h-4 w-24 skeleton rounded" />
                </div>
              ))}
            </div>
          ) : positions.length === 0 ? (
            <div className="text-center py-16">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-background-surface mx-auto mb-6">
                <TrendingUp className="h-8 w-8 text-foreground" />
              </div>
              <h3 className="font-display text-xl mb-2">Nenhuma posição</h3>
              <p className="text-foreground-muted max-w-sm mx-auto">
                {hasFilters
                  ? "Nenhuma posição encontrada com os filtros aplicados."
                  : "Importe transações para ver suas posições calculadas automaticamente."}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Ativo</TableHead>
                    <TableHead>Tipo</TableHead>
                    <TableHead className="text-right">Quantidade</TableHead>
                    <TableHead className="text-right">Preço Médio</TableHead>
                    <TableHead className="text-right">Custo Total</TableHead>
                    <TableHead className="text-right">Preço Atual</TableHead>
                    <TableHead className="text-right">Valor de Mercado</TableHead>
                    <TableHead className="text-right">P&L</TableHead>
                    {viewMode === "consolidated" && (
                      <TableHead className="text-right">Contas</TableHead>
                    )}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {positions.map((pos, index) => {
                    const position = pos as PositionWithMarketData;
                    const typeInfo =
                      ASSET_TYPE_LABELS[position.asset_type] || ASSET_TYPE_LABELS.other;

                    // Handle both detailed and consolidated position types
                    const quantity = "total_quantity" in pos
                      ? (pos as { total_quantity: string }).total_quantity
                      : position.quantity;
                    const avgPrice = "weighted_avg_price" in pos
                      ? (pos as { weighted_avg_price: string }).weighted_avg_price
                      : position.avg_price;
                    const accountsCount = "accounts_count" in pos
                      ? (pos as { accounts_count: number }).accounts_count
                      : undefined;

                    return (
                      <TableRow
                        key={position.asset_id || index}
                        style={{ animationDelay: `${index * 30}ms` }}
                      >
                        <TableCell>
                          <div>
                            <p className="font-semibold truncate max-w-[200px]">{position.asset_name}</p>
                            <p className="text-xs text-foreground-muted font-mono">
                              {position.ticker}
                            </p>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-col gap-1">
                            <Badge variant="secondary">{typeInfo.label}</Badge>
                            {position.position_type === "short" && (
                              <Badge variant="destructive" size="sm">Short</Badge>
                            )}
                          </div>
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {formatNumber(quantity)}
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {formatCurrency(avgPrice)}
                        </TableCell>
                        <TableCell className="text-right font-mono font-semibold">
                          {formatCurrency(position.total_cost)}
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {formatCurrency(position.current_price)}
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {formatCurrency(position.market_value)}
                        </TableCell>
                        <TableCell className="text-right">
                          <div>
                            <p
                              className={`font-mono font-semibold ${getPnLColor(
                                position.unrealized_pnl
                              )}`}
                            >
                              {formatCurrency(position.unrealized_pnl)}
                            </p>
                            <p
                              className={`text-xs ${getPnLColor(position.unrealized_pnl_pct)}`}
                            >
                              {formatPercent(position.unrealized_pnl_pct)}
                            </p>
                          </div>
                        </TableCell>
                        {viewMode === "consolidated" && accountsCount !== undefined && (
                          <TableCell className="text-right">
                            <Badge variant="outline">{accountsCount}</Badge>
                          </TableCell>
                        )}
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
