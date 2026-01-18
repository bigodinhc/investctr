"use client";

import { useMemo, useState } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { usePortfolioHistory } from "@/hooks/use-portfolio";
import { formatCurrency, formatPercent } from "@/lib/utils";
import type { PeriodType, PortfolioHistoryItem } from "@/lib/api/types";
import { TrendingUp, TrendingDown, BarChart3 } from "lucide-react";

const PERIOD_OPTIONS: { value: PeriodType; label: string }[] = [
  { value: "1M", label: "1M" },
  { value: "3M", label: "3M" },
  { value: "6M", label: "6M" },
  { value: "1Y", label: "1A" },
  { value: "YTD", label: "YTD" },
  { value: "MAX", label: "MAX" },
];

// Vermillion color for chart
const VERMILLION = "#ED3900";
const VERMILLION_LIGHT = "#FF5A30";

interface ChartDataPoint {
  date: string;
  nav: number;
  formattedDate: string;
}

function formatDateForChart(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
}

function formatDateForTooltip(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  });
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: { value: number; payload: ChartDataPoint }[];
  label?: string;
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || !payload.length) return null;

  const data = payload[0].payload;

  return (
    <div className="glass-card-elevated p-3 shadow-lg">
      <p className="text-xs text-foreground-muted mb-1">
        {formatDateForTooltip(data.date)}
      </p>
      <p className="text-lg font-mono font-semibold text-gradient-vermillion">
        {formatCurrency(data.nav)}
      </p>
    </div>
  );
}

export function NavEvolutionChart() {
  const [selectedPeriod, setSelectedPeriod] = useState<PeriodType>("YTD");

  const {
    data: historyData,
    isLoading,
    error,
  } = usePortfolioHistory({ period: selectedPeriod });

  const chartData = useMemo<ChartDataPoint[]>(() => {
    if (!historyData?.items) return [];

    return historyData.items.map((item) => ({
      date: item.date,
      nav: parseFloat(item.nav),
      formattedDate: formatDateForChart(item.date),
    }));
  }, [historyData]);

  const periodReturn = historyData?.period_return
    ? parseFloat(historyData.period_return)
    : null;

  const hasData = chartData.length > 0;
  const isPositive = periodReturn !== null ? periodReturn >= 0 : null;

  // Calculate Y-axis domain with some padding
  const yDomain = useMemo(() => {
    if (!chartData.length) return [0, 100];

    const navValues = chartData.map((d) => d.nav);
    const min = Math.min(...navValues);
    const max = Math.max(...navValues);
    const padding = (max - min) * 0.1 || max * 0.1;

    return [Math.max(0, min - padding), max + padding];
  }, [chartData]);

  return (
    <Card variant="glass" className="lg:col-span-2">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <div className="space-y-1">
          <CardTitle className="font-display text-xl">
            Evolucao do Patrimonio
          </CardTitle>
          {periodReturn !== null && hasData && (
            <div className="flex items-center gap-2">
              {isPositive ? (
                <TrendingUp className="h-4 w-4 text-success" />
              ) : (
                <TrendingDown className="h-4 w-4 text-destructive" />
              )}
              <span
                className={`text-sm font-mono font-semibold ${
                  isPositive ? "text-success" : "text-destructive"
                }`}
              >
                {isPositive ? "+" : ""}
                {formatPercent(periodReturn * 100)}
              </span>
              <span className="text-sm text-foreground-muted">no periodo</span>
            </div>
          )}
        </div>
        <div className="flex gap-1 glass-card-subtle p-1 rounded-xl">
          {PERIOD_OPTIONS.map((option) => (
            <button
              key={option.value}
              onClick={() => setSelectedPeriod(option.value)}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-all ${
                selectedPeriod === option.value
                  ? "bg-vermillion/20 text-vermillion shadow-glow-vermillion-sm"
                  : "text-foreground-muted hover:text-foreground hover:bg-white/5"
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="h-72 flex items-center justify-center">
            <div className="animate-pulse space-y-4 w-full">
              <div className="h-4 bg-white/5 rounded w-3/4 mx-auto" />
              <div className="h-48 bg-white/5 rounded" />
            </div>
          </div>
        ) : error ? (
          <div className="h-72 flex items-center justify-center glass-card-subtle rounded-xl">
            <div className="text-center space-y-3">
              <BarChart3 className="h-12 w-12 text-destructive mx-auto" />
              <p className="text-foreground-muted">
                Erro ao carregar historico
              </p>
            </div>
          </div>
        ) : !hasData ? (
          <div className="h-72 flex items-center justify-center glass-card-subtle rounded-xl">
            <div className="text-center space-y-3">
              <BarChart3 className="h-12 w-12 text-foreground-dim mx-auto" />
              <p className="text-foreground-muted">
                Sem dados de historico para o periodo
              </p>
              <p className="text-xs text-foreground-dim">
                Os snapshots sao gerados diariamente as 19:30
              </p>
            </div>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={288}>
            <AreaChart
              data={chartData}
              margin={{ top: 10, right: 10, left: 10, bottom: 0 }}
            >
              <defs>
                <linearGradient id="navGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={VERMILLION} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={VERMILLION} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(255, 255, 255, 0.05)"
                vertical={false}
              />
              <XAxis
                dataKey="formattedDate"
                axisLine={false}
                tickLine={false}
                tick={{ fill: "hsl(var(--foreground-muted))", fontSize: 11 }}
                dy={10}
                interval="preserveStartEnd"
                minTickGap={50}
              />
              <YAxis
                domain={yDomain}
                axisLine={false}
                tickLine={false}
                tick={{ fill: "hsl(var(--foreground-muted))", fontSize: 11 }}
                tickFormatter={(value) =>
                  new Intl.NumberFormat("pt-BR", {
                    notation: "compact",
                    compactDisplay: "short",
                  }).format(value)
                }
                width={60}
              />
              <Tooltip content={<CustomTooltip />} />
              <Area
                type="monotone"
                dataKey="nav"
                stroke={VERMILLION}
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#navGradient)"
                dot={false}
                activeDot={{
                  r: 6,
                  fill: VERMILLION,
                  stroke: "hsl(var(--background))",
                  strokeWidth: 2,
                }}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
