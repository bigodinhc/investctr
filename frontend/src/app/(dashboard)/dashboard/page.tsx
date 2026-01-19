"use client";

import { DataCard } from "@/components/ui/data-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Wallet,
  TrendingUp,
  TrendingDown,
  BarChart3,
  ArrowUpRight,
  ArrowDownRight,
  FileUp,
  RefreshCw,
  Calendar,
  AlertCircle,
  Coins,
} from "lucide-react";
import { formatCurrency, formatPercent } from "@/lib/utils";
import { usePortfolioSummary } from "@/hooks/use-portfolio";
import { usePositions } from "@/hooks/use-positions";
import { useLatestFundShare } from "@/hooks/use-fund";
import { NavEvolutionChart, AllocationChart } from "@/components/dashboard";
import type { AssetType } from "@/lib/api/types";

// Asset type display configuration
const assetTypeConfig: Record<AssetType, { label: string; color: string }> = {
  stock: { label: "Ações", color: "bg-foreground" },
  etf: { label: "ETFs", color: "bg-foreground-muted" },
  reit: { label: "FIIs", color: "bg-info" },
  bdr: { label: "BDRs", color: "bg-foreground-dim" },
  fund: { label: "Fundos", color: "bg-foreground-muted" },
  fixed_income: { label: "Renda Fixa", color: "bg-success" },
  crypto: { label: "Crypto", color: "bg-warning" },
  option: { label: "Opções", color: "bg-foreground-muted" },
  future: { label: "Futuros", color: "bg-destructive" },
  currency: { label: "Câmbio", color: "bg-success" },
  bond: { label: "Renda Fixa", color: "bg-success" },
  treasury: { label: "Tesouro", color: "bg-foreground-muted" },
  other: { label: "Outros", color: "bg-foreground-dim" },
};

export default function DashboardPage() {
  const { data: portfolioSummary, isLoading: isLoadingPortfolio, error: portfolioError } = usePortfolioSummary();
  const { data: positionsData, isLoading: isLoadingPositions, error: positionsError } = usePositions({ limit: 10 });
  const { data: fundShareData, isLoading: isLoadingFundShare } = useLatestFundShare();

  const isLoading = isLoadingPortfolio || isLoadingPositions;
  const hasError = portfolioError || positionsError;

  // Fund share data
  const shareValue = fundShareData ? parseFloat(fundShareData.share_value) : null;
  const dailyReturn = fundShareData?.daily_return ? parseFloat(fundShareData.daily_return) : null;
  const sharesOutstanding = fundShareData ? parseFloat(fundShareData.shares_outstanding) : null;

  // Parse numeric values from API response
  const totalValue = portfolioSummary ? parseFloat(portfolioSummary.total_value) : 0;
  const totalUnrealizedPnl = portfolioSummary ? parseFloat(portfolioSummary.total_unrealized_pnl) : 0;
  const totalUnrealizedPnlPct = portfolioSummary?.total_unrealized_pnl_pct
    ? parseFloat(portfolioSummary.total_unrealized_pnl_pct)
    : null;
  const totalRealizedPnl = portfolioSummary ? parseFloat(portfolioSummary.total_realized_pnl) : 0;
  const totalCost = portfolioSummary ? parseFloat(portfolioSummary.total_cost) : 0;

  // Calculate daily change (approximation - would need historical data for accurate calculation)
  const dailyChange = totalUnrealizedPnlPct !== null ? totalUnrealizedPnlPct : 0;

  // Positions from API
  const positions = positionsData?.items || [];

  // Check if user has no data
  const hasNoData = !isLoading && portfolioSummary?.total_positions === 0;

  if (hasError) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center space-y-4">
          <AlertCircle className="h-12 w-12 text-destructive mx-auto" />
          <h2 className="text-lg font-semibold">Erro ao carregar dados</h2>
          <p className="text-foreground-muted">
            Não foi possível carregar os dados do portfolio. Tente novamente.
          </p>
          <Button onClick={() => window.location.reload()}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Tentar novamente
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Hero Section - Main NAV */}
      <div className="rounded-xl bg-background-elevated border border-border p-4 sm:p-6 lg:p-8">
        <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4 sm:gap-6">
          <div className="space-y-3 sm:space-y-4">
            <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
              {portfolioSummary?.last_price_update ? (
                <Badge variant="muted" size="lg">
                  <Calendar className="h-3 w-3 mr-1" />
                  Atualizado {new Date(portfolioSummary.last_price_update).toLocaleString("pt-BR", {
                    day: "2-digit",
                    month: "2-digit",
                    hour: "2-digit",
                    minute: "2-digit"
                  })}
                </Badge>
              ) : (
                <Badge variant="outline" size="lg">
                  <Calendar className="h-3 w-3 mr-1" />
                  Cotações não sincronizadas
                </Badge>
              )}
            </div>

            <div>
              <p className="text-sm text-foreground-muted uppercase tracking-wider mb-2">
                Patrimônio Líquido
              </p>
              {isLoading ? (
                <div className="h-14 w-64 skeleton rounded" />
              ) : (
                <h1 className="font-display text-3xl sm:text-5xl lg:text-6xl tracking-tight text-foreground">
                  {formatCurrency(totalValue)}
                </h1>
              )}
            </div>

            <div className="flex items-center gap-4">
              {isLoading ? (
                <div className="h-8 w-40 skeleton rounded" />
              ) : (
                <>
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-mono font-semibold ${
                        dailyChange >= 0
                          ? "bg-success/10 text-success"
                          : "bg-destructive/10 text-destructive"
                      }`}
                    >
                      {dailyChange >= 0 ? (
                        <ArrowUpRight className="h-4 w-4" />
                      ) : (
                        <ArrowDownRight className="h-4 w-4" />
                      )}
                      {formatPercent(dailyChange)}
                    </span>
                    <span className="text-sm text-foreground-muted">variação</span>
                  </div>
                  {totalUnrealizedPnlPct !== null && (
                    <>
                      <div className="h-6 w-px bg-border" />
                      <span className="text-sm text-foreground-muted">
                        <span className={`font-mono font-semibold ${totalUnrealizedPnlPct >= 0 ? "text-success" : "text-destructive"}`}>
                          {formatPercent(totalUnrealizedPnlPct)}
                        </span>{" "}
                        total
                      </span>
                    </>
                  )}
                </>
              )}
            </div>
          </div>

          <div className="flex gap-2 sm:gap-3">
            <Button variant="outline" size="default" className="flex-1 sm:flex-none" onClick={() => window.location.reload()}>
              <RefreshCw className="h-4 w-4 sm:mr-2" />
              <span className="hidden sm:inline">Atualizar</span>
            </Button>
            <Button size="default" className="flex-1 sm:flex-none" asChild>
              <a href="/documents">
                <FileUp className="h-4 w-4 sm:mr-2" />
                <span className="hidden sm:inline">Importar Extrato</span>
              </a>
            </Button>
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 sm:gap-4">
        <DataCard
          title="Valor da Cota"
          value={shareValue !== null ? formatCurrency(shareValue) : "R$ --"}
          change={dailyReturn !== null ? dailyReturn * 100 : undefined}
          icon={Coins}
          variant="highlight"
          isLoading={isLoading || isLoadingFundShare}
        />
        <DataCard
          title="Custo Total"
          value={formatCurrency(totalCost)}
          icon={TrendingUp}
          isLoading={isLoading}
        />
        <DataCard
          title="P&L Nao Realizado"
          value={formatCurrency(totalUnrealizedPnl)}
          change={totalUnrealizedPnlPct !== null ? totalUnrealizedPnlPct : undefined}
          icon={BarChart3}
          variant={totalUnrealizedPnl >= 0 ? "success" : "destructive"}
          isLoading={isLoading}
        />
        <DataCard
          title="P&L Realizado"
          value={formatCurrency(totalRealizedPnl)}
          icon={Wallet}
          variant={totalRealizedPnl >= 0 ? "default" : "destructive"}
          isLoading={isLoading}
        />
        <DataCard
          title="Posicoes Ativas"
          value={portfolioSummary?.total_positions.toString() || "0"}
          icon={TrendingDown}
          isLoading={isLoading}
        />
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Chart - NAV Evolution */}
        <NavEvolutionChart />

        {/* Allocation Chart */}
        <AllocationChart />
      </div>

      {/* Positions Table */}
      <Card variant="elevated">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="font-display text-xl">POSIÇÕES ABERTAS</CardTitle>
          <Button variant="outline" size="sm" asChild>
            <a href="/positions">
              Ver todas
              <ArrowUpRight className="h-4 w-4 ml-2" />
            </a>
          </Button>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="flex items-center justify-between py-4 border-b border-border/50">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 skeleton rounded-lg" />
                    <div className="space-y-2">
                      <div className="h-4 w-20 skeleton rounded" />
                      <div className="h-3 w-32 skeleton rounded" />
                    </div>
                  </div>
                  <div className="h-4 w-24 skeleton rounded" />
                </div>
              ))}
            </div>
          ) : positions.length === 0 || hasNoData ? (
            <div className="text-center py-12">
              <Wallet className="h-12 w-12 text-foreground-dim mx-auto mb-4" />
              <p className="text-foreground-muted mb-2">
                Nenhuma posição encontrada
              </p>
              <p className="text-sm text-foreground-dim mb-6">
                Importe um extrato para começar a acompanhar seus investimentos
              </p>
              <Button asChild>
                <a href="/documents">
                  <FileUp className="h-4 w-4 mr-2" />
                  Importar Extrato
                </a>
              </Button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-3 px-4 text-xs uppercase tracking-wider text-foreground-muted font-medium">
                      Ativo
                    </th>
                    <th className="text-right py-3 px-4 text-xs uppercase tracking-wider text-foreground-muted font-medium">
                      Quantidade
                    </th>
                    <th className="text-right py-3 px-4 text-xs uppercase tracking-wider text-foreground-muted font-medium">
                      Preço Médio
                    </th>
                    <th className="text-right py-3 px-4 text-xs uppercase tracking-wider text-foreground-muted font-medium">
                      Preço Atual
                    </th>
                    <th className="text-right py-3 px-4 text-xs uppercase tracking-wider text-foreground-muted font-medium">
                      P&L
                    </th>
                    <th className="text-right py-3 px-4 text-xs uppercase tracking-wider text-foreground-muted font-medium">
                      Variação
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {positions.map((position, index) => {
                    const quantity = parseFloat(position.quantity);
                    const avgPrice = parseFloat(position.avg_price);
                    const currentPrice = position.current_price ? parseFloat(position.current_price) : null;
                    const pnl = position.unrealized_pnl ? parseFloat(position.unrealized_pnl) : null;
                    const pnlPct = position.unrealized_pnl_pct ? parseFloat(position.unrealized_pnl_pct) : null;

                    return (
                      <tr
                        key={position.id}
                        className="border-b border-border/50 hover:bg-background-surface/50 transition-colors cursor-pointer"
                        style={{ animationDelay: `${index * 50}ms` }}
                      >
                        <td className="py-4 px-4">
                          <div className="flex items-center gap-3">
                            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-background-surface border border-border">
                              <span className="font-mono text-xs font-semibold text-foreground">
                                {position.ticker.slice(0, 2)}
                              </span>
                            </div>
                            <div>
                              <p className="font-semibold">{position.ticker}</p>
                              <p className="text-xs text-foreground-muted">{position.asset_name}</p>
                            </div>
                          </div>
                        </td>
                        <td className="py-4 px-4 text-right font-mono">
                          {quantity.toLocaleString("pt-BR")}
                        </td>
                        <td className="py-4 px-4 text-right font-mono text-foreground-muted">
                          {formatCurrency(avgPrice)}
                        </td>
                        <td className="py-4 px-4 text-right font-mono">
                          {currentPrice !== null ? formatCurrency(currentPrice) : "-"}
                        </td>
                        <td
                          className={`py-4 px-4 text-right font-mono font-semibold ${
                            pnl !== null ? (pnl >= 0 ? "text-success" : "text-destructive") : "text-foreground-muted"
                          }`}
                        >
                          {pnl !== null ? (
                            <>
                              {pnl >= 0 ? "+" : ""}
                              {formatCurrency(pnl)}
                            </>
                          ) : (
                            "-"
                          )}
                        </td>
                        <td className="py-4 px-4 text-right">
                          {pnlPct !== null ? (
                            <Badge
                              variant={pnlPct >= 0 ? "outline-success" : "outline-destructive"}
                              size="sm"
                            >
                              {pnlPct >= 0 ? (
                                <ArrowUpRight className="h-3 w-3 mr-1" />
                              ) : (
                                <ArrowDownRight className="h-3 w-3 mr-1" />
                              )}
                              {formatPercent(pnlPct)}
                            </Badge>
                          ) : (
                            <span className="text-foreground-muted">-</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
