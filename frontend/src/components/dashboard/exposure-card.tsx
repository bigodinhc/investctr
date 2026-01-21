"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, TrendingDown, Activity, Scale } from "lucide-react";
import { formatCurrency, formatPercent, cn } from "@/lib/utils";

export interface ExposureCardProps {
  longValue: number;
  shortValue: number;
  longPositionsCount: number;
  shortPositionsCount: number;
  grossExposure: number;
  netExposure: number;
  grossExposurePct: number | null;
  netExposurePct: number | null;
  isLoading?: boolean;
}

export function ExposureCard({
  longValue,
  shortValue,
  longPositionsCount,
  shortPositionsCount,
  grossExposure,
  netExposure,
  grossExposurePct,
  netExposurePct,
  isLoading = false,
}: ExposureCardProps) {
  // Only show if there are any short positions or meaningful exposure data
  const hasShortPositions = shortPositionsCount > 0 || shortValue > 0;

  if (isLoading) {
    return (
      <Card variant="elevated">
        <CardHeader className="pb-2">
          <CardTitle className="font-display text-lg flex items-center gap-2">
            <Scale className="h-5 w-5 text-foreground-muted" />
            EXPOSICAO
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="h-16 skeleton rounded" />
              <div className="h-16 skeleton rounded" />
            </div>
            <div className="h-px bg-border" />
            <div className="grid grid-cols-2 gap-4">
              <div className="h-12 skeleton rounded" />
              <div className="h-12 skeleton rounded" />
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // If no short positions and it's a simple long-only portfolio, show simplified version
  if (!hasShortPositions) {
    return (
      <Card variant="elevated">
        <CardHeader className="pb-2">
          <CardTitle className="font-display text-lg flex items-center gap-2">
            <Scale className="h-5 w-5 text-foreground-muted" />
            EXPOSICAO
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Long Only */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-success/10">
                  <TrendingUp className="h-5 w-5 text-success" />
                </div>
                <div>
                  <p className="text-sm text-foreground-muted">Long</p>
                  <p className="font-mono text-lg font-semibold">{formatCurrency(longValue)}</p>
                </div>
              </div>
              <Badge variant="outline" size="sm">
                {longPositionsCount} posicoes
              </Badge>
            </div>

            <div className="h-px bg-border" />

            {/* Summary for long-only */}
            <div className="text-center">
              <p className="text-xs text-foreground-muted uppercase tracking-wider mb-1">
                Portfolio Long-Only
              </p>
              <p className="text-sm text-foreground-dim">
                100% de exposicao direcional
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Full exposure card with long/short breakdown
  return (
    <Card variant="elevated">
      <CardHeader className="pb-2">
        <CardTitle className="font-display text-lg flex items-center gap-2">
          <Scale className="h-5 w-5 text-foreground-muted" />
          EXPOSICAO
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Long/Short Values */}
          <div className="grid grid-cols-2 gap-4">
            {/* Long */}
            <div className="rounded-lg border border-success/20 bg-success/5 p-3">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="h-4 w-4 text-success" />
                <span className="text-xs uppercase tracking-wider text-success font-medium">Long</span>
              </div>
              <p className="font-mono text-lg font-semibold text-foreground">
                {formatCurrency(longValue)}
              </p>
              <p className="text-xs text-foreground-muted mt-1">
                {longPositionsCount} posicoes
              </p>
            </div>

            {/* Short */}
            <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-3">
              <div className="flex items-center gap-2 mb-2">
                <TrendingDown className="h-4 w-4 text-destructive" />
                <span className="text-xs uppercase tracking-wider text-destructive font-medium">Short</span>
              </div>
              <p className="font-mono text-lg font-semibold text-foreground">
                {formatCurrency(shortValue)}
              </p>
              <p className="text-xs text-foreground-muted mt-1">
                {shortPositionsCount} posicoes
              </p>
            </div>
          </div>

          <div className="h-px bg-border" />

          {/* Exposure Metrics */}
          <div className="grid grid-cols-2 gap-4">
            {/* Gross Exposure */}
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <Activity className="h-3 w-3 text-foreground-muted" />
                <span className="text-xs text-foreground-muted uppercase tracking-wider">
                  Gross Exposure
                </span>
              </div>
              <p className="font-mono text-base font-semibold">
                {formatCurrency(grossExposure)}
              </p>
              {grossExposurePct !== null && (
                <Badge
                  variant={grossExposurePct > 100 ? "outline-destructive" : "outline"}
                  size="sm"
                >
                  {formatPercent(grossExposurePct)}
                  {grossExposurePct > 100 && " (alavancado)"}
                </Badge>
              )}
            </div>

            {/* Net Exposure */}
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <Scale className="h-3 w-3 text-foreground-muted" />
                <span className="text-xs text-foreground-muted uppercase tracking-wider">
                  Net Exposure
                </span>
              </div>
              <p className="font-mono text-base font-semibold">
                {formatCurrency(netExposure)}
              </p>
              {netExposurePct !== null && (
                <Badge
                  variant={
                    netExposurePct > 70
                      ? "outline-success"
                      : netExposurePct < 30
                      ? "outline"
                      : "outline"
                  }
                  size="sm"
                >
                  {formatPercent(netExposurePct)}
                  {netExposurePct < 10 && " (neutro)"}
                </Badge>
              )}
            </div>
          </div>

          {/* Explanation */}
          <div className="text-xs text-foreground-dim bg-background-surface rounded-md p-2">
            <p>
              <strong>Gross:</strong> Risco total (Long + Short)
            </p>
            <p>
              <strong>Net:</strong> Direcao de mercado (Long - Short)
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
