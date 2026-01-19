import * as React from "react";
import { cn } from "@/lib/utils";

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  width?: string | number;
  height?: string | number;
  variant?: "default" | "circular" | "rounded" | "none";
}

export function Skeleton({
  className,
  width,
  height,
  variant = "default",
  style,
  ...props
}: SkeletonProps) {
  const variants = {
    default: "rounded",
    circular: "rounded-full",
    rounded: "rounded-lg",
    none: "",
  };

  return (
    <div
      className={cn("skeleton", variants[variant], className)}
      style={{
        width: typeof width === "number" ? `${width}px` : width,
        height: typeof height === "number" ? `${height}px` : height,
        ...style,
      }}
      {...props}
    />
  );
}

export interface SkeletonTextProps extends React.HTMLAttributes<HTMLDivElement> {
  lines?: number;
  lastLineWidth?: string;
  gap?: "sm" | "md" | "lg";
}

export function SkeletonText({
  lines = 1,
  lastLineWidth = "60%",
  gap = "md",
  className,
  ...props
}: SkeletonTextProps) {
  const gaps = { sm: "gap-1", md: "gap-2", lg: "gap-3" };
  return (
    <div className={cn("flex flex-col", gaps[gap], className)} {...props}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className="h-4"
          style={{ width: i === lines - 1 && lines > 1 ? lastLineWidth : "100%" }}
        />
      ))}
    </div>
  );
}

export function SkeletonDataCard({ className }: { className?: string }) {
  return (
    <div className={cn("rounded-lg border border-border bg-card p-6", className)}>
      <div className="flex items-start justify-between">
        <div className="space-y-3 flex-1">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-8 w-32" />
          <Skeleton className="h-4 w-20" />
        </div>
        <Skeleton className="h-10 w-10" variant="rounded" />
      </div>
    </div>
  );
}

export function SkeletonPositionRow({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-center justify-between py-4 border-b border-border/50", className)}>
      <div className="flex items-center gap-3">
        <Skeleton className="h-10 w-10" variant="rounded" />
        <div className="space-y-2">
          <Skeleton className="h-4 w-20" />
          <Skeleton className="h-3 w-32" />
        </div>
      </div>
      <div className="flex items-center gap-6">
        <Skeleton className="h-4 w-16" />
        <Skeleton className="h-4 w-20 hidden md:block" />
        <Skeleton className="h-4 w-20 hidden md:block" />
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-6 w-16" variant="rounded" />
      </div>
    </div>
  );
}

export function SkeletonTransactionRow({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-center gap-4 p-4 border-b border-border/50", className)}>
      <Skeleton className="h-10 w-10" variant="rounded" />
      <div className="flex-1 space-y-2">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-3 w-24" />
      </div>
      <div className="flex items-center gap-4">
        <Skeleton className="h-4 w-16 hidden sm:block" />
        <Skeleton className="h-4 w-20 hidden md:block" />
        <Skeleton className="h-4 w-24" />
      </div>
    </div>
  );
}

export function SkeletonTransactionCard({ className }: { className?: string }) {
  return (
    <div className={cn("p-4 rounded-lg bg-background-surface border border-border-subtle", className)}>
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0 space-y-2">
          <Skeleton className="h-5 w-20" />
          <Skeleton className="h-3 w-32" />
        </div>
        <Skeleton className="h-6 w-16" variant="rounded" />
      </div>
      <div className="grid grid-cols-2 gap-2 text-sm mb-3">
        <div className="space-y-1"><Skeleton className="h-3 w-10" /><Skeleton className="h-4 w-20" /></div>
        <div className="space-y-1 flex flex-col items-end"><Skeleton className="h-3 w-10" /><Skeleton className="h-4 w-24" /></div>
        <div className="space-y-1"><Skeleton className="h-3 w-10" /><Skeleton className="h-4 w-16" /></div>
        <div className="space-y-1 flex flex-col items-end"><Skeleton className="h-3 w-10" /><Skeleton className="h-4 w-20" /></div>
      </div>
      <div className="flex items-center justify-between pt-3 border-t border-border-subtle">
        <Skeleton className="h-3 w-24" />
        <div className="flex gap-1">
          <Skeleton className="h-8 w-8" variant="rounded" />
          <Skeleton className="h-8 w-8" variant="rounded" />
        </div>
      </div>
    </div>
  );
}

export function SkeletonAreaChart({ className }: { className?: string }) {
  return (
    <div className={cn("space-y-4", className)}>
      <div className="relative h-72">
        <div className="absolute left-0 top-0 h-full w-12 flex flex-col justify-between py-2">
          <Skeleton className="h-3 w-10" />
          <Skeleton className="h-3 w-8" />
          <Skeleton className="h-3 w-10" />
          <Skeleton className="h-3 w-8" />
          <Skeleton className="h-3 w-10" />
        </div>
        <div className="ml-14 h-full rounded-lg bg-background-surface/50 relative overflow-hidden">
          <div className="absolute inset-0 flex items-end px-4 pb-4">
            {[40, 55, 48, 62, 58, 70, 65, 75, 72, 80, 78, 85].map((h, i) => (
              <div key={i} className="flex-1 mx-0.5 skeleton rounded-t" style={{ height: `${h}%` }} />
            ))}
          </div>
        </div>
      </div>
      <div className="flex justify-between ml-14">
        {[1,2,3,4,5].map(i => <Skeleton key={i} className="h-3 w-10" />)}
      </div>
    </div>
  );
}

export function SkeletonDonutChart({ className }: { className?: string }) {
  return (
    <div className={cn("space-y-4", className)}>
      <div className="h-48 flex items-center justify-center">
        <div className="relative">
          <Skeleton className="h-40 w-40" variant="circular" />
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="h-20 w-20 rounded-full bg-card" />
          </div>
        </div>
      </div>
      <div className="space-y-2">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Skeleton className="h-3 w-3" variant="circular" />
              <Skeleton className="h-4 w-24" />
            </div>
            <Skeleton className="h-4 w-12" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function SkeletonSummaryCard({ className }: { className?: string }) {
  return (
    <div className={cn("rounded-lg border border-border bg-background-elevated p-4", className)}>
      <div className="flex items-center gap-3">
        <Skeleton className="h-10 w-10" variant="rounded" />
        <div className="space-y-1">
          <Skeleton className="h-3 w-16" />
          <Skeleton className="h-7 w-20" />
        </div>
      </div>
    </div>
  );
}

export function SkeletonHeroSection({ className }: { className?: string }) {
  return (
    <div className={cn("rounded-xl bg-background-elevated border border-border p-8", className)}>
      <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-6">
        <div className="space-y-4">
          <Skeleton className="h-6 w-48" variant="rounded" />
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-14 w-64" />
          <div className="flex items-center gap-4">
            <Skeleton className="h-8 w-24" variant="rounded" />
            <Skeleton className="h-4 w-20" />
          </div>
        </div>
        <div className="flex gap-3">
          <Skeleton className="h-11 w-32" variant="rounded" />
          <Skeleton className="h-11 w-40" variant="rounded" />
        </div>
      </div>
    </div>
  );
}

export function SkeletonTable({ rows = 5, columns = 6, className }: { rows?: number; columns?: number; className?: string }) {
  return (
    <div className={cn("space-y-4", className)}>
      <div className="flex items-center gap-4 py-3 border-b border-border">
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={i} className="h-3 flex-1" style={{ maxWidth: i === 0 ? "150px" : "100px" }} />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="flex items-center gap-4 py-4 border-b border-border/50">
          {Array.from({ length: columns }).map((_, colIndex) => (
            <Skeleton key={colIndex} className="h-4 flex-1" style={{ maxWidth: colIndex === 0 ? "150px" : "100px" }} />
          ))}
        </div>
      ))}
    </div>
  );
}

export function SkeletonPositionsTable({ rows = 5, className }: { rows?: number; className?: string }) {
  return (
    <div className={cn("space-y-0", className)}>
      {Array.from({ length: rows }).map((_, i) => <SkeletonPositionRow key={i} />)}
    </div>
  );
}

export function SkeletonTransactionsTable({ rows = 5, className }: { rows?: number; className?: string }) {
  return (
    <div className={cn("space-y-0", className)}>
      {Array.from({ length: rows }).map((_, i) => <SkeletonTransactionRow key={i} />)}
    </div>
  );
}

export function SkeletonTransactionsCards({ count = 5, className }: { count?: number; className?: string }) {
  return (
    <div className={cn("space-y-3", className)}>
      {Array.from({ length: count }).map((_, i) => <SkeletonTransactionCard key={i} />)}
    </div>
  );
}

export function SkeletonAllocationCard({ className }: { className?: string }) {
  return (
    <div className={cn("p-4 rounded-lg bg-background-surface border border-border-subtle", className)}>
      <div className="flex items-center gap-2 mb-2">
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-16" />
      </div>
      <Skeleton className="h-5 w-24 mb-1" />
      <Skeleton className="h-3 w-20 mb-1" />
      <Skeleton className="h-3 w-16" />
    </div>
  );
}

export default Skeleton;
