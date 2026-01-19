"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCw, Home, Bug, LayoutDashboard } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";

interface DashboardErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

/**
 * Dashboard Error Page - Next.js App Router
 * Captura erros especificos da area do dashboard
 * Mantem o layout (Sidebar + Header) intacto
 */
export default function DashboardError({ error, reset }: DashboardErrorProps) {
  useEffect(() => {
    // Log do erro em desenvolvimento
    if (process.env.NODE_ENV === "development") {
      console.group("Dashboard Error Page");
      console.error("Error:", error);
      console.error("Digest:", error.digest);
      console.groupEnd();
    }

    // Preparado para Sentry - descomente quando configurar:
    // if (typeof window !== 'undefined' && window.Sentry) {
    //   window.Sentry.captureException(error, {
    //     extra: {
    //       digest: error.digest,
    //       location: 'dashboard',
    //     },
    //   });
    // }
  }, [error]);

  const handleGoToDashboard = () => {
    window.location.href = "/dashboard";
  };

  return (
    <div className="flex min-h-[calc(100vh-4rem)] w-full items-center justify-center p-4 animate-fade-in">
      <Card variant="default" className="w-full max-w-lg">
        <CardHeader className="text-center">
          {/* Icon container with terminal-style border */}
          <div className="mx-auto mb-4 relative">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-warning/10 border border-warning/20">
              <AlertTriangle className="h-8 w-8 text-warning" />
            </div>
            {/* Subtle corner accents */}
            <div className="absolute -top-1 -left-1 w-3 h-3 border-l-2 border-t-2 border-warning/30 rounded-tl" />
            <div className="absolute -top-1 -right-1 w-3 h-3 border-r-2 border-t-2 border-warning/30 rounded-tr" />
            <div className="absolute -bottom-1 -left-1 w-3 h-3 border-l-2 border-b-2 border-warning/30 rounded-bl" />
            <div className="absolute -bottom-1 -right-1 w-3 h-3 border-r-2 border-b-2 border-warning/30 rounded-br" />
          </div>

          <CardTitle className="text-xl">Erro no dashboard</CardTitle>
          <p className="text-foreground-muted text-sm mt-2">
            Nao foi possivel carregar esta pagina. Voce pode tentar novamente ou voltar ao dashboard principal.
          </p>
        </CardHeader>

        <CardContent>
          {/* Error details in dev mode */}
          {process.env.NODE_ENV === "development" && (
            <div className="mt-4 rounded-lg bg-background-surface border border-border-subtle p-4">
              <div className="flex items-center gap-2 text-xs font-mono text-foreground-muted mb-2">
                <Bug className="h-3 w-3" />
                <span>Debug Info (apenas em desenvolvimento)</span>
              </div>
              <div className="space-y-2">
                <div>
                  <span className="text-xs font-mono text-destructive">
                    {error.name}: {error.message}
                  </span>
                </div>
                {error.digest && (
                  <div className="text-xs font-mono text-foreground-dim">
                    Digest: {error.digest}
                  </div>
                )}
                {error.stack && (
                  <details className="cursor-pointer">
                    <summary className="text-xs font-mono text-foreground-dim hover:text-foreground-muted transition-colors">
                      Ver stack trace
                    </summary>
                    <pre className="mt-2 max-h-32 overflow-auto rounded bg-background-deep p-2 text-xs font-mono text-foreground-dim">
                      {error.stack}
                    </pre>
                  </details>
                )}
              </div>
            </div>
          )}

          {/* Terminal-style status */}
          <div className="mt-4 flex items-center justify-center gap-2 text-foreground-dim text-xs font-mono opacity-60">
            <span className="inline-block w-2 h-2 bg-warning rounded-full animate-pulse" />
            <span>erro na area do dashboard</span>
          </div>
        </CardContent>

        <CardFooter className="flex flex-col gap-2 sm:flex-row">
          <Button
            variant="default"
            onClick={reset}
            className="w-full sm:w-auto gap-2"
          >
            <RefreshCw className="h-4 w-4" />
            Tentar novamente
          </Button>
          <Button
            variant="outline"
            onClick={handleGoToDashboard}
            className="w-full sm:w-auto gap-2"
          >
            <LayoutDashboard className="h-4 w-4" />
            Ir para Dashboard
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
