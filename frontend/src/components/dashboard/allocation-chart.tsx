"use client";

import { useMemo } from "react";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { usePortfolioAllocation } from "@/hooks/use-portfolio";
import { formatCurrency, formatPercent } from "@/lib/utils";
import { PieChart as PieChartIcon } from "lucide-react";

// Vermillion Glass color palette - vibrant colors that work with glass
const COLORS = [
  "#ED3900", // Vermillion (primary)
  "#FF5A30", // Vermillion light
  "#22B573", // Success green
  "#3D8BF5", // Info blue
  "#F5A623", // Warning amber
  "#9B59B6", // Purple
  "#1ABC9C", // Teal
  "#E91E63", // Pink
  "#00BCD4", // Cyan
  "#8BC34A", // Light green
];

interface ChartDataPoint {
  name: string;
  value: number;
  percentage: number;
  color: string;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: { payload: ChartDataPoint }[];
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || !payload.length) return null;

  const data = payload[0].payload;

  return (
    <div className="glass-card-elevated p-3 shadow-lg">
      <p className="text-sm font-semibold mb-1">{data.name}</p>
      <p className="text-lg font-mono font-semibold text-gradient-vermillion">
        {formatCurrency(data.value)}
      </p>
      <p className="text-xs text-foreground-muted">
        {formatPercent(data.percentage)} do portfolio
      </p>
    </div>
  );
}

interface CustomLegendProps {
  payload?: Array<{
    value: string;
    color: string;
    payload: ChartDataPoint;
  }>;
}

function CustomLegend({ payload }: CustomLegendProps) {
  if (!payload) return null;

  return (
    <div className="space-y-2 mt-4">
      {payload.map((entry, index) => (
        <div key={`legend-${index}`} className="flex items-center justify-between group">
          <div className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full transition-transform group-hover:scale-125"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-sm text-foreground-muted truncate max-w-[120px] group-hover:text-foreground transition-colors">
              {entry.value}
            </span>
          </div>
          <span className="font-mono text-sm font-semibold">
            {formatPercent(entry.payload.percentage)}
          </span>
        </div>
      ))}
    </div>
  );
}

export function AllocationChart() {
  const { data: allocationData, isLoading, error } = usePortfolioAllocation();

  const chartData = useMemo<ChartDataPoint[]>(() => {
    if (!allocationData?.by_asset_type) return [];

    // Always use frontend colors (ignore backend colors to maintain theme consistency)
    return allocationData.by_asset_type.map((item, index) => ({
      name: item.name,
      value: parseFloat(item.value),
      percentage: parseFloat(item.percentage),
      color: COLORS[index % COLORS.length],
    }));
  }, [allocationData]);

  const hasData = chartData.length > 0;
  const totalValue = allocationData?.total_value
    ? parseFloat(allocationData.total_value)
    : 0;

  return (
    <Card variant="glass">
      <CardHeader className="pb-2">
        <CardTitle className="font-display text-xl">Alocacao</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-4">
            <div className="h-48 flex items-center justify-center">
              <div className="w-40 h-40 skeleton rounded-full" />
            </div>
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="flex items-center justify-between">
                <div className="h-4 w-24 skeleton rounded" />
                <div className="h-4 w-12 skeleton rounded" />
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="h-48 flex items-center justify-center glass-card-subtle rounded-xl">
            <div className="text-center space-y-2">
              <PieChartIcon className="h-8 w-8 text-destructive mx-auto" />
              <p className="text-sm text-foreground-muted">Erro ao carregar alocacao</p>
            </div>
          </div>
        ) : !hasData ? (
          <div className="h-48 flex items-center justify-center glass-card-subtle rounded-xl">
            <div className="text-center space-y-2">
              <PieChartIcon className="h-8 w-8 text-foreground-dim mx-auto" />
              <p className="text-sm text-foreground-muted">Sem dados de alocacao</p>
            </div>
          </div>
        ) : (
          <>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={80}
                  paddingAngle={2}
                  dataKey="value"
                  stroke="rgba(0, 0, 0, 0.3)"
                  strokeWidth={1}
                >
                  {chartData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={entry.color}
                      className="transition-opacity hover:opacity-80"
                    />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
              </PieChart>
            </ResponsiveContainer>

            {/* Center label */}
            <div className="text-center -mt-28 mb-24 pointer-events-none">
              <p className="text-glass-label">Total</p>
              <p className="font-mono text-sm font-semibold text-gradient-vermillion">
                {formatCurrency(totalValue)}
              </p>
            </div>

            {/* Legend */}
            <CustomLegend
              payload={chartData.map((item) => ({
                value: item.name,
                color: item.color,
                payload: item,
              }))}
            />
          </>
        )}
      </CardContent>
    </Card>
  );
}
