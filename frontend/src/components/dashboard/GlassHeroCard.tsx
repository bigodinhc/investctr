"use client";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

interface GlassHeroCardProps {
  value: string;
  label: string;
  change?: number;
  changeLabel?: string;
  className?: string;
  isLoading?: boolean;
  badge?: React.ReactNode;
  actions?: React.ReactNode;
}

export function GlassHeroCard({
  value,
  label,
  change,
  changeLabel,
  className,
  isLoading = false,
  badge,
  actions,
}: GlassHeroCardProps) {
  return (
    <div
      className={cn(
        "glass-card-accent p-8 animate-glow-pulse relative overflow-hidden",
        className
      )}
    >
      {/* Background glow effect */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-vermillion/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2 pointer-events-none" />

      <div className="relative flex flex-col lg:flex-row lg:items-end lg:justify-between gap-6">
        <div className="space-y-4">
          {/* Badge */}
          {badge && <div>{badge}</div>}

          {/* Label */}
          <div>
            <p className="text-glass-label mb-2">{label}</p>

            {/* Value */}
            {isLoading ? (
              <div className="h-14 w-64 skeleton rounded" />
            ) : (
              <h1 className="text-value-hero">{value}</h1>
            )}
          </div>

          {/* Change indicator */}
          {(change !== undefined || changeLabel) && !isLoading && (
            <div className="flex items-center gap-4">
              {change !== undefined && (
                <Badge
                  variant={change >= 0 ? "success" : "destructive"}
                  size="lg"
                  className="font-mono"
                >
                  {change >= 0 ? "+" : ""}
                  {change.toFixed(2)}%
                </Badge>
              )}
              {changeLabel && (
                <span className="text-sm text-foreground-muted">
                  {changeLabel}
                </span>
              )}
            </div>
          )}
        </div>

        {/* Actions */}
        {actions && <div className="flex gap-3">{actions}</div>}
      </div>
    </div>
  );
}
