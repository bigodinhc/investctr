"use client";

import { type LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface EmptyStateAction {
  label: string;
  onClick: () => void;
  icon?: LucideIcon;
  variant?: "default" | "outline" | "secondary" | "ghost";
}

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: EmptyStateAction;
  className?: string;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center py-16 px-4 animate-fade-in",
        className
      )}
    >
      {/* Icon container with terminal-style border */}
      <div className="relative mb-6">
        <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-background-surface border border-border-subtle">
          <Icon className="h-10 w-10 text-foreground-muted" />
        </div>
        {/* Subtle corner accents */}
        <div className="absolute -top-1 -left-1 w-3 h-3 border-l-2 border-t-2 border-border-subtle rounded-tl" />
        <div className="absolute -top-1 -right-1 w-3 h-3 border-r-2 border-t-2 border-border-subtle rounded-tr" />
        <div className="absolute -bottom-1 -left-1 w-3 h-3 border-l-2 border-b-2 border-border-subtle rounded-bl" />
        <div className="absolute -bottom-1 -right-1 w-3 h-3 border-r-2 border-b-2 border-border-subtle rounded-br" />
      </div>

      {/* Title */}
      <h3 className="font-display text-xl text-foreground mb-2 text-center">
        {title}
      </h3>

      {/* Description */}
      <p className="text-foreground-muted text-center max-w-sm mb-6 leading-relaxed">
        {description}
      </p>

      {/* Optional action button */}
      {action && (
        <Button
          variant={action.variant || "default"}
          onClick={action.onClick}
          className="gap-2"
        >
          {action.icon && <action.icon className="h-4 w-4" />}
          {action.label}
        </Button>
      )}

      {/* Terminal-style prompt indicator */}
      <div className="mt-8 flex items-center gap-2 text-foreground-dim text-xs font-mono opacity-50">
        <span className="inline-block w-2 h-2 bg-foreground-dim rounded-full animate-pulse" />
        <span>aguardando dados...</span>
      </div>
    </div>
  );
}
