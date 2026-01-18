"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { Button } from "./button";
import {
  FileQuestion,
  FolderOpen,
  Inbox,
  Search,
  AlertCircle,
  type LucideIcon,
} from "lucide-react";

interface EmptyStateProps extends React.HTMLAttributes<HTMLDivElement> {
  /**
   * Icon to display
   */
  icon?: LucideIcon;
  /**
   * Title text
   */
  title: string;
  /**
   * Description text
   */
  description?: string;
  /**
   * Primary action button
   */
  action?: {
    label: string;
    onClick: () => void;
    icon?: LucideIcon;
  };
  /**
   * Secondary action button
   */
  secondaryAction?: {
    label: string;
    onClick: () => void;
  };
  /**
   * Size variant
   */
  size?: "sm" | "md" | "lg";
}

/**
 * EmptyState component for when there's no data to display
 */
function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  action,
  secondaryAction,
  size = "md",
  className,
  ...props
}: EmptyStateProps) {
  const sizeClasses = {
    sm: {
      container: "py-8",
      icon: "h-8 w-8",
      title: "text-base",
      description: "text-sm",
    },
    md: {
      container: "py-12",
      icon: "h-12 w-12",
      title: "text-lg",
      description: "text-sm",
    },
    lg: {
      container: "py-16",
      icon: "h-16 w-16",
      title: "text-xl",
      description: "text-base",
    },
  };

  const sizes = sizeClasses[size];

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center text-center",
        sizes.container,
        className
      )}
      {...props}
    >
      <div className="rounded-full bg-foreground/5 p-4 mb-4">
        <Icon className={cn("text-foreground-dim", sizes.icon)} />
      </div>
      <h3 className={cn("font-semibold text-foreground mb-2", sizes.title)}>
        {title}
      </h3>
      {description && (
        <p
          className={cn(
            "text-foreground-muted max-w-sm mb-6",
            sizes.description
          )}
        >
          {description}
        </p>
      )}
      {(action || secondaryAction) && (
        <div className="flex flex-col sm:flex-row gap-3">
          {action && (
            <Button onClick={action.onClick}>
              {action.icon && <action.icon className="h-4 w-4 mr-2" />}
              {action.label}
            </Button>
          )}
          {secondaryAction && (
            <Button variant="outline" onClick={secondaryAction.onClick}>
              {secondaryAction.label}
            </Button>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Pre-built empty states for common scenarios
 */

interface PrebuiltEmptyStateProps {
  action?: {
    label: string;
    onClick: () => void;
    icon?: LucideIcon;
  };
  className?: string;
}

function EmptyStateNoData({ action, className }: PrebuiltEmptyStateProps) {
  return (
    <EmptyState
      icon={FolderOpen}
      title="Nenhum dado encontrado"
      description="Nao ha dados para exibir no momento."
      action={action}
      className={className}
    />
  );
}

function EmptyStateNoResults({ action, className }: PrebuiltEmptyStateProps) {
  return (
    <EmptyState
      icon={Search}
      title="Nenhum resultado"
      description="Nao encontramos resultados para sua busca. Tente ajustar os filtros."
      action={action}
      className={className}
    />
  );
}

function EmptyStateError({
  action,
  className,
  message,
}: PrebuiltEmptyStateProps & { message?: string }) {
  return (
    <EmptyState
      icon={AlertCircle}
      title="Erro ao carregar"
      description={message || "Ocorreu um erro ao carregar os dados. Tente novamente."}
      action={action || { label: "Tentar novamente", onClick: () => window.location.reload() }}
      className={className}
    />
  );
}

function EmptyStateNoDocuments({ action, className }: PrebuiltEmptyStateProps) {
  return (
    <EmptyState
      icon={FileQuestion}
      title="Nenhum documento"
      description="Importe um extrato para comecar a acompanhar seus investimentos."
      action={action}
      className={className}
    />
  );
}

function EmptyStateNoPositions({ action, className }: PrebuiltEmptyStateProps) {
  return (
    <EmptyState
      icon={Inbox}
      title="Nenhuma posicao"
      description="Voce ainda nao possui posicoes. Importe um extrato para comecar."
      action={action}
      className={className}
    />
  );
}

function EmptyStateNoTransactions({ action, className }: PrebuiltEmptyStateProps) {
  return (
    <EmptyState
      icon={Inbox}
      title="Nenhuma transacao"
      description="Nao ha transacoes registradas. Importe um extrato para adicionar transacoes."
      action={action}
      className={className}
    />
  );
}

export {
  EmptyState,
  EmptyStateNoData,
  EmptyStateNoResults,
  EmptyStateError,
  EmptyStateNoDocuments,
  EmptyStateNoPositions,
  EmptyStateNoTransactions,
};
