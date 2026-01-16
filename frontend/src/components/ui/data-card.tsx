"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown, Minus, LucideIcon } from "lucide-react";

export interface DataCardProps {
  title: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
  icon?: LucideIcon;
  trend?: "up" | "down" | "neutral";
  variant?: "default" | "highlight" | "success" | "destructive";
  className?: string;
  isLoading?: boolean;
}

export function DataCard({
  title,
  value,
  change,
  changeLabel,
  icon: Icon,
  trend,
  variant = "default",
  className,
  isLoading = false,
}: DataCardProps) {
  // Auto-determine trend from change value if not provided
  const effectiveTrend = trend ?? (change !== undefined ? (change > 0 ? "up" : change < 0 ? "down" : "neutral") : undefined);

  const TrendIcon = effectiveTrend === "up" ? TrendingUp : effectiveTrend === "down" ? TrendingDown : Minus;

  const variants = {
    default: "bg-card border-border",
    highlight: "bg-gold/5 border-gold/20",
    success: "bg-success/5 border-success/20",
    destructive: "bg-destructive/5 border-destructive/20",
  };

  const trendColors = {
    up: "text-success bg-success/10",
    down: "text-destructive bg-destructive/10",
    neutral: "text-foreground-muted bg-muted",
  };

  if (isLoading) {
    return (
      <div className={cn("rounded-lg border p-6", variants[variant], className)}>
        <div className="flex items-start justify-between">
          <div className="space-y-3 flex-1">
            <div className="h-4 w-24 skeleton rounded" />
            <div className="h-8 w-32 skeleton rounded" />
            <div className="h-4 w-20 skeleton rounded" />
          </div>
          <div className="h-10 w-10 skeleton rounded-lg" />
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "rounded-lg border p-6 transition-all duration-300 hover:shadow-lg hover:-translate-y-0.5",
        variants[variant],
        className
      )}
    >
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          {/* Title */}
          <p className="text-sm text-foreground-muted font-medium">{title}</p>

          {/* Value */}
          <p className="font-mono text-2xl font-semibold tracking-tight text-foreground">
            {value}
          </p>

          {/* Change indicator */}
          {(change !== undefined || changeLabel) && effectiveTrend && (
            <div className="flex items-center gap-2 pt-1">
              <span
                className={cn(
                  "inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium",
                  trendColors[effectiveTrend]
                )}
              >
                <TrendIcon className="h-3 w-3" />
                {change !== undefined && (
                  <span>{change > 0 ? "+" : ""}{typeof change === "number" ? change.toFixed(2) : change}%</span>
                )}
              </span>
              {changeLabel && (
                <span className="text-xs text-foreground-dim">{changeLabel}</span>
              )}
            </div>
          )}
        </div>

        {/* Icon */}
        {Icon && (
          <div
            className={cn(
              "flex h-10 w-10 items-center justify-center rounded-lg",
              variant === "highlight"
                ? "bg-gold/10 text-gold"
                : variant === "success"
                ? "bg-success/10 text-success"
                : variant === "destructive"
                ? "bg-destructive/10 text-destructive"
                : "bg-muted text-foreground-muted"
            )}
          >
            <Icon className="h-5 w-5" />
          </div>
        )}
      </div>
    </div>
  );
}

export interface StatProps {
  label: string;
  value: string | number;
  subValue?: string;
  change?: number;
  size?: "sm" | "md" | "lg" | "xl";
  align?: "left" | "center" | "right";
  className?: string;
}

export function Stat({
  label,
  value,
  subValue,
  change,
  size = "md",
  align = "left",
  className,
}: StatProps) {
  const sizes = {
    sm: "text-lg",
    md: "text-2xl",
    lg: "text-3xl",
    xl: "text-4xl",
  };

  const alignments = {
    left: "text-left",
    center: "text-center",
    right: "text-right",
  };

  const trend = change !== undefined ? (change > 0 ? "up" : change < 0 ? "down" : "neutral") : undefined;

  return (
    <div className={cn("space-y-1", alignments[align], className)}>
      <p className="text-xs uppercase tracking-wider text-foreground-dim font-medium">
        {label}
      </p>
      <p className={cn("font-mono font-bold", sizes[size])}>
        {value}
      </p>
      <div className="flex items-center gap-2 justify-start">
        {change !== undefined && trend && (
          <span
            className={cn(
              "text-sm font-mono font-medium",
              trend === "up" && "text-success",
              trend === "down" && "text-destructive",
              trend === "neutral" && "text-foreground-muted"
            )}
          >
            {change > 0 ? "+" : ""}{change.toFixed(2)}%
          </span>
        )}
        {subValue && (
          <span className="text-sm text-foreground-muted">{subValue}</span>
        )}
      </div>
    </div>
  );
}
