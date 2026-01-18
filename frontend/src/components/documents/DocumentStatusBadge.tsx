"use client";

import { Loader2, CheckCircle2, AlertCircle, Clock } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { ParsingStatus } from "@/lib/api/types";

interface DocumentStatusBadgeProps {
  status: ParsingStatus;
  className?: string;
}

const STATUS_CONFIG: Record<ParsingStatus, {
  label: string;
  variant: "default" | "secondary" | "success" | "destructive" | "warning" | "info" | "vermillion";
  icon: React.ReactNode;
}> = {
  pending: {
    label: "Pendente",
    variant: "secondary",
    icon: <Clock className="h-3 w-3" />,
  },
  processing: {
    label: "Processando",
    variant: "warning",
    icon: <Loader2 className="h-3 w-3 animate-spin" />,
  },
  completed: {
    label: "Concluído",
    variant: "success",
    icon: <CheckCircle2 className="h-3 w-3" />,
  },
  failed: {
    label: "Falhou",
    variant: "destructive",
    icon: <AlertCircle className="h-3 w-3" />,
  },
};

export function DocumentStatusBadge({ status, className }: DocumentStatusBadgeProps) {
  const config = STATUS_CONFIG[status];

  return (
    <Badge variant={config.variant} className={className}>
      <span className="flex items-center gap-1.5">
        {config.icon}
        {config.label}
      </span>
    </Badge>
  );
}
