"use client";

import { DataCard, Stat } from "@/components/ui/data-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Wallet,
  TrendingUp,
  TrendingDown,
  PieChart,
  BarChart3,
  ArrowUpRight,
  ArrowDownRight,
  FileUp,
  Plus,
  RefreshCw,
  Calendar,
} from "lucide-react";
import { formatCurrency, formatPercent } from "@/lib/utils";

// Mock data - will be replaced with real data from API
const mockData = {
  nav: 847293.45,
  shareValue: 1.2847,
  returns: 28.47,
  pnl: 187543.21,
  navChange: 2.34,
  positions: [
    { ticker: "PETR4", name: "Petrobras PN", quantity: 1200, avgPrice: 28.45, currentPrice: 32.67, pnl: 5064.00, pnlPercent: 14.83, type: "Ação" },
    { ticker: "VALE3", name: "Vale ON", quantity: 500, avgPrice: 68.90, currentPrice: 63.45, pnl: -2725.00, pnlPercent: -7.91, type: "Ação" },
    { ticker: "XPLG11", name: "XP Log FII", quantity: 300, avgPrice: 98.50, currentPrice: 105.20, pnl: 2010.00, pnlPercent: 6.80, type: "FII" },
    { ticker: "ITUB4", name: "Itaú PN", quantity: 800, avgPrice: 24.30, currentPrice: 27.85, pnl: 2840.00, pnlPercent: 14.61, type: "Ação" },
    { ticker: "WEGE3", name: "WEG ON", quantity: 200, avgPrice: 35.60, currentPrice: 42.15, pnl: 1310.00, pnlPercent: 18.40, type: "Ação" },
  ],
  allocation: [
    { name: "Ações BR", value: 45, color: "bg-gold" },
    { name: "FIIs", value: 25, color: "bg-info" },
    { name: "Renda Fixa", value: 20, color: "bg-success" },
    { name: "Internacional", value: 10, color: "bg-warning" },
  ],
};

export default function DashboardPage() {
  return (
    <div className="space-y-8 animate-fade-in">
      {/* Hero Section - Main NAV */}
      <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-background-elevated via-background to-background-surface border border-border p-8">
        {/* Background glow */}
        <div className="absolute top-0 right-0 w-96 h-96 bg-gold/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />

        <div className="relative flex flex-col lg:flex-row lg:items-end lg:justify-between gap-6">
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <Badge variant="gold" size="lg">
                <Calendar className="h-3 w-3 mr-1" />
                Atualizado hoje às 18:30
              </Badge>
            </div>

            <div>
              <p className="text-sm text-foreground-muted uppercase tracking-wider mb-2">
                Patrimônio Líquido
              </p>
              <h1 className="font-display text-5xl lg:text-6xl tracking-tight">
                <span className="text-gradient-gold">{formatCurrency(mockData.nav)}</span>
              </h1>
            </div>

            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <span
                  className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-mono font-semibold ${
                    mockData.navChange >= 0
                      ? "bg-success/10 text-success"
                      : "bg-destructive/10 text-destructive"
                  }`}
                >
                  {mockData.navChange >= 0 ? (
                    <ArrowUpRight className="h-4 w-4" />
                  ) : (
                    <ArrowDownRight className="h-4 w-4" />
                  )}
                  {formatPercent(mockData.navChange)}
                </span>
                <span className="text-sm text-foreground-muted">hoje</span>
              </div>
              <div className="h-6 w-px bg-border" />
              <span className="text-sm text-foreground-muted">
                <span className="font-mono font-semibold text-success">{formatPercent(mockData.returns)}</span> no ano
              </span>
            </div>
          </div>

          <div className="flex gap-3">
            <Button variant="outline" size="lg">
              <RefreshCw className="h-4 w-4 mr-2" />
              Atualizar
            </Button>
            <Button size="lg">
              <FileUp className="h-4 w-4 mr-2" />
              Importar Extrato
            </Button>
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <DataCard
          title="Valor da Cota"
          value={`R$ ${mockData.shareValue.toFixed(4)}`}
          change={1.23}
          changeLabel="vs. ontem"
          icon={TrendingUp}
          variant="highlight"
        />
        <DataCard
          title="Rentabilidade Total"
          value={formatPercent(mockData.returns)}
          change={2.34}
          changeLabel="este mês"
          icon={BarChart3}
          variant="success"
        />
        <DataCard
          title="P&L Realizado"
          value={formatCurrency(mockData.pnl)}
          change={5.67}
          changeLabel="este mês"
          icon={Wallet}
        />
        <DataCard
          title="P&L Não Realizado"
          value={formatCurrency(mockData.pnl * 0.3)}
          change={-1.23}
          changeLabel="hoje"
          icon={TrendingDown}
        />
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Chart */}
        <Card variant="elevated" className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="font-display text-xl">EVOLUÇÃO DO PATRIMÔNIO</CardTitle>
            <div className="flex gap-2">
              {["1M", "3M", "6M", "1A", "YTD", "MAX"].map((period) => (
                <button
                  key={period}
                  className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                    period === "YTD"
                      ? "bg-gold/10 text-gold"
                      : "text-foreground-muted hover:text-foreground hover:bg-background-surface"
                  }`}
                >
                  {period}
                </button>
              ))}
            </div>
          </CardHeader>
          <CardContent>
            {/* Chart placeholder */}
            <div className="h-72 flex items-center justify-center border border-dashed border-border rounded-lg bg-background-surface/50">
              <div className="text-center space-y-3">
                <BarChart3 className="h-12 w-12 text-foreground-dim mx-auto" />
                <p className="text-foreground-muted">
                  Gráfico de evolução será exibido aqui
                </p>
                <p className="text-xs text-foreground-dim">
                  Importe extratos para visualizar seus dados
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Allocation Chart */}
        <Card variant="elevated">
          <CardHeader className="pb-2">
            <CardTitle className="font-display text-xl">ALOCAÇÃO</CardTitle>
          </CardHeader>
          <CardContent>
            {/* Donut chart placeholder */}
            <div className="h-48 flex items-center justify-center mb-6">
              <div className="relative w-40 h-40">
                <div className="absolute inset-0 rounded-full border-8 border-gold/20" />
                <div className="absolute inset-4 rounded-full border-8 border-info/20" />
                <div className="absolute inset-8 rounded-full border-8 border-success/20" />
                <div className="absolute inset-12 rounded-full border-8 border-warning/20" />
                <div className="absolute inset-0 flex items-center justify-center">
                  <PieChart className="h-8 w-8 text-foreground-dim" />
                </div>
              </div>
            </div>

            {/* Legend */}
            <div className="space-y-3">
              {mockData.allocation.map((item) => (
                <div key={item.name} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className={`w-3 h-3 rounded-full ${item.color}`} />
                    <span className="text-sm text-foreground-muted">{item.name}</span>
                  </div>
                  <span className="font-mono text-sm font-semibold">{item.value}%</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Positions Table */}
      <Card variant="elevated">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="font-display text-xl">POSIÇÕES ABERTAS</CardTitle>
          <Button variant="outline" size="sm">
            <Plus className="h-4 w-4 mr-2" />
            Nova Posição
          </Button>
        </CardHeader>
        <CardContent>
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
                {mockData.positions.map((position, index) => (
                  <tr
                    key={position.ticker}
                    className="border-b border-border/50 hover:bg-background-surface/50 transition-colors cursor-pointer"
                    style={{ animationDelay: `${index * 50}ms` }}
                  >
                    <td className="py-4 px-4">
                      <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gold/10 border border-gold/20">
                          <span className="font-mono text-xs font-semibold text-gold">
                            {position.ticker.slice(0, 2)}
                          </span>
                        </div>
                        <div>
                          <p className="font-semibold">{position.ticker}</p>
                          <p className="text-xs text-foreground-muted">{position.name}</p>
                        </div>
                      </div>
                    </td>
                    <td className="py-4 px-4 text-right font-mono">
                      {position.quantity.toLocaleString("pt-BR")}
                    </td>
                    <td className="py-4 px-4 text-right font-mono text-foreground-muted">
                      {formatCurrency(position.avgPrice)}
                    </td>
                    <td className="py-4 px-4 text-right font-mono">
                      {formatCurrency(position.currentPrice)}
                    </td>
                    <td
                      className={`py-4 px-4 text-right font-mono font-semibold ${
                        position.pnl >= 0 ? "text-success" : "text-destructive"
                      }`}
                    >
                      {position.pnl >= 0 ? "+" : ""}
                      {formatCurrency(position.pnl)}
                    </td>
                    <td className="py-4 px-4 text-right">
                      <Badge
                        variant={position.pnlPercent >= 0 ? "outline-success" : "outline-destructive"}
                        size="sm"
                      >
                        {position.pnlPercent >= 0 ? (
                          <ArrowUpRight className="h-3 w-3 mr-1" />
                        ) : (
                          <ArrowDownRight className="h-3 w-3 mr-1" />
                        )}
                        {formatPercent(position.pnlPercent)}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Empty state - shown when no positions */}
          {mockData.positions.length === 0 && (
            <div className="text-center py-12">
              <Wallet className="h-12 w-12 text-foreground-dim mx-auto mb-4" />
              <p className="text-foreground-muted mb-2">
                Nenhuma posição encontrada
              </p>
              <p className="text-sm text-foreground-dim mb-6">
                Importe um extrato para começar a acompanhar seus investimentos
              </p>
              <Button>
                <FileUp className="h-4 w-4 mr-2" />
                Importar Extrato
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
