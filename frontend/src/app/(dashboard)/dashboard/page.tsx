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
import { NavEvolutionChart, AllocationChart, GlassHeroCard } from "@/components/dashboard";
import type { AssetType } from "@/lib/api/types";

// Asset type display configuration with vermillion palette
const assetTypeConfig: Record<AssetType, { label: string; color: string }> = {
  stock: { label: "Acoes", color: "bg-vermillion" },
  etf: { label: "ETFs", color: "bg-info" },
  reit: { label: "FIIs", color: "bg-purple-500" },
  bdr: { label: "BDRs", color: "bg-cyan-500" },
  fund: { label: "Fundos", color: "bg-teal-500" },
  fixed_income: { label: "Renda Fixa", color: "bg-success" },
  crypto: { label: "Crypto", color: "bg-orange-500" },
  option: { label: "Opcoes", color: "bg-pink-500" },
  future: { label: "Futuros", color: "bg-red-500" },
  currency: { label: "Cambio", color: "bg-emerald-500" },
  bond: { label: "Renda Fixa", color: "bg-success" },
  treasury: { label: "Tesouro", color: "bg-teal-500" },
  other: { label: "Outros", color: "bg-gray-500" },
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
        <div className="glass-card p-8 text-center space-y-4 max-w-md">
          <AlertCircle className="h-12 w-12 text-destructive mx-auto" />
          <h2 className="text-lg font-display font-semibold">Erro ao carregar dados</h2>
          <p className="text-foreground-muted">
            Nao foi possivel carregar os dados do portfolio. Tente novamente.
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
      {/* Hero Section - Glass NAV Card */}
      <GlassHeroCard
        label="Patrimonio Liquido"
        value={formatCurrency(totalValue)}
        change={dailyChange}
        changeLabel="variacao"
        isLoading={isLoading}
        badge={
          portfolioSummary?.last_price_update ? (
            <Badge variant="vermillion" size="lg">
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
              Cotacoes nao sincronizadas
            </Badge>
          )
        }
        actions={
          <>
            <Button variant="glass" size="lg" onClick={() => window.location.reload()}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Atualizar
            </Button>
            <Button size="lg" asChild>
              <a href="/documents">
                <FileUp className="h-4 w-4 mr-2" />
                Importar Extrato
              </a>
            </Button>
          </>
        }
      />

      {/* Summary Cards - Glass Style */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        <DataCard
          title="Valor da Cota"
          value={shareValue !== null ? formatCurrency(shareValue) : "R$ --"}
          change={dailyReturn !== null ? dailyReturn * 100 : undefined}
          icon={Coins}
          variant="glass-accent"
          isLoading={isLoading || isLoadingFundShare}
        />
        <DataCard
          title="Custo Total"
          value={formatCurrency(totalCost)}
          icon={TrendingUp}
          variant="glass"
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
          variant="glass"
          isLoading={isLoading}
        />
        <DataCard
          title="Posicoes Ativas"
          value={portfolioSummary?.total_positions.toString() || "0"}
          icon={TrendingDown}
          variant="glass"
          isLoading={isLoading}
        />
      </div>

      {/* Charts Section - Glass Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Chart - NAV Evolution */}
        <NavEvolutionChart />

        {/* Allocation Chart */}
        <AllocationChart />
      </div>

      {/* Positions Table - Glass Style */}
      <Card variant="glass">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="font-display text-xl">Posicoes Abertas</CardTitle>
          <Button variant="glass" size="sm" asChild>
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
                <div key={i} className="flex items-center justify-between py-4 border-b border-white/5">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 skeleton rounded-xl" />
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
            <div className="text-center py-12 glass-card-subtle rounded-xl">
              <Wallet className="h-12 w-12 text-foreground-dim mx-auto mb-4" />
              <p className="text-foreground-muted mb-2">
                Nenhuma posicao encontrada
              </p>
              <p className="text-sm text-foreground-dim mb-6">
                Importe um extrato para comecar a acompanhar seus investimentos
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
                  <tr className="border-b border-white/10">
                    <th className="text-left py-3 px-4 text-glass-label font-medium">
                      Ativo
                    </th>
                    <th className="text-right py-3 px-4 text-glass-label font-medium">
                      Quantidade
                    </th>
                    <th className="text-right py-3 px-4 text-glass-label font-medium">
                      Preco Medio
                    </th>
                    <th className="text-right py-3 px-4 text-glass-label font-medium">
                      Preco Atual
                    </th>
                    <th className="text-right py-3 px-4 text-glass-label font-medium">
                      P&L
                    </th>
                    <th className="text-right py-3 px-4 text-glass-label font-medium">
                      Variacao
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
                        className="border-b border-white/5 hover:bg-white/5 transition-colors cursor-pointer animate-fade-in"
                        style={{ animationDelay: `${index * 50}ms` }}
                      >
                        <td className="py-4 px-4">
                          <div className="flex items-center gap-3">
                            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-vermillion/10 border border-vermillion/20">
                              <span className="font-mono text-xs font-semibold text-vermillion">
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
