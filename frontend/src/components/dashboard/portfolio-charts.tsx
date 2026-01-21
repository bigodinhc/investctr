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
  LineChart,
  Line,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { usePortfolioHistory } from "@/hooks/use-portfolio";
import { formatCurrency, formatPercent } from "@/lib/utils";
import type { PeriodType } from "@/lib/api/types";
import { TrendingUp, TrendingDown, BarChart3, Wallet, LineChartIcon } from "lucide-react";

const PERIOD_OPTIONS: { value: PeriodType; label: string }[] = [
  { value: "1M", label: "1M" },
  { value: "3M", label: "3M" },
  { value: "6M", label: "6M" },
  { value: "1Y", label: "1A" },
  { value: "YTD", label: "YTD" },
  { value: "MAX", label: "MAX" },
];

// Colors
const NAV_COLOR = "#22B573"; // Green for NAV
const SHARE_COLOR = "#D4AF37"; // Gold for share value

interface ChartDataPoint {
  date: string;
  nav: number;
  shareValue: number | null;
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

interface NavTooltipProps {
  active?: boolean;
  payload?: { value: number; payload: ChartDataPoint }[];
}

function NavTooltip({ active, payload }: NavTooltipProps) {
  if (!active || !payload || !payload.length) return null;
  const data = payload[0].payload;

  return (
    <div className="bg-background-elevated border border-border rounded-lg p-3 shadow-lg">
      <p className="text-xs text-foreground-muted mb-1">
        {formatDateForTooltip(data.date)}
      </p>
      <p className="text-lg font-mono font-semibold text-foreground">
        {formatCurrency(data.nav)}
      </p>
    </div>
  );
}

interface ShareTooltipProps {
  active?: boolean;
  payload?: { value: number; payload: ChartDataPoint }[];
}

function ShareTooltip({ active, payload }: ShareTooltipProps) {
  if (!active || !payload || !payload.length) return null;
  const data = payload[0].payload;

  // Calculate return from R$100 base
  const returnPct = data.shareValue ? ((data.shareValue - 100) / 100) * 100 : null;

  return (
    <div className="bg-background-elevated border border-border rounded-lg p-3 shadow-lg">
      <p className="text-xs text-foreground-muted mb-1">
        {formatDateForTooltip(data.date)}
      </p>
      <p className="text-lg font-mono font-semibold text-foreground">
        {data.shareValue ? formatCurrency(data.shareValue) : "—"}
      </p>
      {returnPct !== null && (
        <p className={`text-sm font-mono ${returnPct >= 0 ? "text-success" : "text-destructive"}`}>
          {returnPct >= 0 ? "+" : ""}{formatPercent(returnPct)} desde o início
        </p>
      )}
    </div>
  );
}

export function PortfolioCharts() {
  const [selectedPeriod, setSelectedPeriod] = useState<PeriodType>("MAX");

  const {
    data: historyData,
    isLoading,
    error,
  } = usePortfolioHistory({ period: selectedPeriod, limit: 1000 });

  const chartData = useMemo<ChartDataPoint[]>(() => {
    if (!historyData?.items) return [];

    return historyData.items.map((item) => ({
      date: item.date,
      nav: parseFloat(item.nav),
      shareValue: item.share_value ? parseFloat(item.share_value) : null,
      formattedDate: formatDateForChart(item.date),
    }));
  }, [historyData]);

  const hasData = chartData.length > 0;

  // Calculate NAV change
  const navReturn = useMemo(() => {
    if (chartData.length < 2) return null;
    const first = chartData[0].nav;
    const last = chartData[chartData.length - 1].nav;
    return first > 0 ? ((last - first) / first) : null;
  }, [chartData]);

  // Calculate share value return (performance)
  const shareReturn = useMemo(() => {
    if (chartData.length < 2) return null;
    const firstShare = chartData.find(d => d.shareValue !== null)?.shareValue;
    const lastShare = [...chartData].reverse().find(d => d.shareValue !== null)?.shareValue;
    if (!firstShare || !lastShare) return null;
    return (lastShare - firstShare) / firstShare;
  }, [chartData]);

  // Calculate Y-axis domains
  const navDomain = useMemo(() => {
    if (!chartData.length) return [0, 100];
    const values = chartData.map((d) => d.nav);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const padding = (max - min) * 0.1 || max * 0.1;
    return [Math.max(0, min - padding), max + padding];
  }, [chartData]);

  const shareDomain = useMemo(() => {
    if (!chartData.length) return [0, 100];
    const values = chartData.filter(d => d.shareValue !== null).map((d) => d.shareValue!);
    if (values.length === 0) return [0, 100];
    const min = Math.min(...values);
    const max = Math.max(...values);
    const padding = (max - min) * 0.1 || max * 0.1;
    return [Math.max(0, min - padding), max + padding];
  }, [chartData]);

  const renderEmptyState = (icon: React.ReactNode, message: string) => (
    <div className="h-56 flex items-center justify-center border border-dashed border-border rounded-lg bg-background-surface/50">
      <div className="text-center space-y-3">
        {icon}
        <p className="text-foreground-muted text-sm">{message}</p>
      </div>
    </div>
  );

  const renderLoading = () => (
    <div className="h-56 flex items-center justify-center">
      <div className="animate-pulse space-y-4 w-full">
        <div className="h-4 bg-background-surface rounded w-3/4 mx-auto" />
        <div className="h-40 bg-background-surface rounded" />
      </div>
    </div>
  );

  return (
    <div className="space-y-4">
      {/* Period Selector */}
      <div className="flex justify-end">
        <div className="flex gap-1 bg-background-elevated rounded-lg p-1">
          {PERIOD_OPTIONS.map((option) => (
            <button
              key={option.value}
              onClick={() => setSelectedPeriod(option.value)}
              className={`px-3 py-1.5 text-xs font-medium rounded transition-colors ${
                selectedPeriod === option.value
                  ? "bg-background-surface text-foreground"
                  : "text-foreground-muted hover:text-foreground hover:bg-background-surface/50"
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* NAV Evolution Chart */}
        <Card variant="elevated">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Wallet className="h-4 w-4 text-foreground-muted" />
                <CardTitle className="font-display text-base">
                  PATRIMÔNIO TOTAL
                </CardTitle>
              </div>
              {navReturn !== null && hasData && (
                <div className="flex items-center gap-1">
                  {navReturn >= 0 ? (
                    <TrendingUp className="h-3 w-3 text-success" />
                  ) : (
                    <TrendingDown className="h-3 w-3 text-destructive" />
                  )}
                  <span
                    className={`text-xs font-mono font-semibold ${
                      navReturn >= 0 ? "text-success" : "text-destructive"
                    }`}
                  >
                    {navReturn >= 0 ? "+" : ""}
                    {formatPercent(navReturn * 100)}
                  </span>
                </div>
              )}
            </div>
            <p className="text-xs text-foreground-muted">
              Inclui aportes e saques
            </p>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              renderLoading()
            ) : error ? (
              renderEmptyState(
                <BarChart3 className="h-10 w-10 text-destructive mx-auto" />,
                "Erro ao carregar"
              )
            ) : !hasData ? (
              renderEmptyState(
                <BarChart3 className="h-10 w-10 text-foreground-dim mx-auto" />,
                "Sem dados para o período"
              )
            ) : (
              <ResponsiveContainer width="100%" height={224}>
                <AreaChart
                  data={chartData}
                  margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                >
                  <defs>
                    <linearGradient id="navGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={NAV_COLOR} stopOpacity={0.3} />
                      <stop offset="95%" stopColor={NAV_COLOR} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="hsl(var(--border))"
                    vertical={false}
                  />
                  <XAxis
                    dataKey="formattedDate"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: "hsl(var(--foreground-muted))", fontSize: 10 }}
                    dy={10}
                    interval="preserveStartEnd"
                    minTickGap={40}
                  />
                  <YAxis
                    domain={navDomain}
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: "hsl(var(--foreground-muted))", fontSize: 10 }}
                    tickFormatter={(value) =>
                      new Intl.NumberFormat("pt-BR", {
                        notation: "compact",
                        compactDisplay: "short",
                      }).format(value)
                    }
                    width={50}
                  />
                  <Tooltip content={<NavTooltip />} />
                  <Area
                    type="monotone"
                    dataKey="nav"
                    stroke={NAV_COLOR}
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#navGradient)"
                    dot={false}
                    activeDot={{
                      r: 5,
                      fill: NAV_COLOR,
                      stroke: "hsl(var(--background))",
                      strokeWidth: 2,
                    }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Share Value (Performance) Chart */}
        <Card variant="elevated">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <LineChartIcon className="h-4 w-4 text-foreground-muted" />
                <CardTitle className="font-display text-base">
                  PERFORMANCE
                </CardTitle>
              </div>
              {shareReturn !== null && hasData && (
                <div className="flex items-center gap-1">
                  {shareReturn >= 0 ? (
                    <TrendingUp className="h-3 w-3 text-success" />
                  ) : (
                    <TrendingDown className="h-3 w-3 text-destructive" />
                  )}
                  <span
                    className={`text-xs font-mono font-semibold ${
                      shareReturn >= 0 ? "text-success" : "text-destructive"
                    }`}
                  >
                    {shareReturn >= 0 ? "+" : ""}
                    {formatPercent(shareReturn * 100)}
                  </span>
                </div>
              )}
            </div>
            <p className="text-xs text-foreground-muted">
              Valor da cota (base R$ 100)
            </p>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              renderLoading()
            ) : error ? (
              renderEmptyState(
                <BarChart3 className="h-10 w-10 text-destructive mx-auto" />,
                "Erro ao carregar"
              )
            ) : !hasData ? (
              renderEmptyState(
                <BarChart3 className="h-10 w-10 text-foreground-dim mx-auto" />,
                "Sem dados para o período"
              )
            ) : (
              <ResponsiveContainer width="100%" height={224}>
                <LineChart
                  data={chartData}
                  margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                >
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="hsl(var(--border))"
                    vertical={false}
                  />
                  <XAxis
                    dataKey="formattedDate"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: "hsl(var(--foreground-muted))", fontSize: 10 }}
                    dy={10}
                    interval="preserveStartEnd"
                    minTickGap={40}
                  />
                  <YAxis
                    domain={shareDomain}
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: "hsl(var(--foreground-muted))", fontSize: 10 }}
                    tickFormatter={(value) => `R$${value.toFixed(0)}`}
                    width={55}
                  />
                  <Tooltip content={<ShareTooltip />} />
                  <Line
                    type="monotone"
                    dataKey="shareValue"
                    stroke={SHARE_COLOR}
                    strokeWidth={2}
                    dot={false}
                    activeDot={{
                      r: 5,
                      fill: SHARE_COLOR,
                      stroke: "hsl(var(--background))",
                      strokeWidth: 2,
                    }}
                    connectNulls
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
