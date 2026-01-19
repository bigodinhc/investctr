"use client";

import React, { Component, ErrorInfo, ReactNode } from "react";
import { AlertTriangle, RefreshCw, Home, Bug } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  className?: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

/**
 * ErrorBoundary - Class component para capturar erros em componentes filhos
 *
 * Uso:
 * <ErrorBoundary>
 *   <ComponenteQuePodeFalhar />
 * </ErrorBoundary>
 *
 * Com fallback customizado:
 * <ErrorBoundary fallback={<MeuComponenteDeErro />}>
 *   <ComponenteQuePodeFalhar />
 * </ErrorBoundary>
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    this.setState({ errorInfo });

    // Log do erro em desenvolvimento
    if (process.env.NODE_ENV === "development") {
      console.group("ErrorBoundary caught an error");
      console.error("Error:", error);
      console.error("Error Info:", errorInfo);
      console.error("Component Stack:", errorInfo.componentStack);
      console.groupEnd();
    }

    // Callback opcional para integracoes externas (ex: Sentry)
    this.props.onError?.(error, errorInfo);

    // Preparado para Sentry - descomente quando configurar:
    // if (typeof window !== 'undefined' && window.Sentry) {
    //   window.Sentry.captureException(error, {
    //     extra: {
    //       componentStack: errorInfo.componentStack,
    //     },
    //   });
    // }
  }

  handleReset = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  handleReload = (): void => {
    window.location.reload();
  };

  handleGoHome = (): void => {
    window.location.href = "/dashboard";
  };

  render(): ReactNode {
    const { hasError, error, errorInfo } = this.state;
    const { children, fallback, className } = this.props;

    if (hasError) {
      // Se um fallback customizado foi fornecido, use-o
      if (fallback) {
        return fallback;
      }

      // UI padrao de erro
      return (
        <div
          className={cn(
            "flex min-h-[400px] w-full items-center justify-center p-4 animate-fade-in",
            className
          )}
        >
          <Card variant="default" className="w-full max-w-lg">
            <CardHeader className="text-center">
              {/* Icon container with terminal-style border */}
              <div className="mx-auto mb-4 relative">
                <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-destructive/10 border border-destructive/20">
                  <AlertTriangle className="h-8 w-8 text-destructive" />
                </div>
                {/* Subtle corner accents */}
                <div className="absolute -top-1 -left-1 w-3 h-3 border-l-2 border-t-2 border-destructive/30 rounded-tl" />
                <div className="absolute -top-1 -right-1 w-3 h-3 border-r-2 border-t-2 border-destructive/30 rounded-tr" />
                <div className="absolute -bottom-1 -left-1 w-3 h-3 border-l-2 border-b-2 border-destructive/30 rounded-bl" />
                <div className="absolute -bottom-1 -right-1 w-3 h-3 border-r-2 border-b-2 border-destructive/30 rounded-br" />
              </div>

              <CardTitle className="text-xl">Algo deu errado</CardTitle>
              <p className="text-foreground-muted text-sm mt-2">
                Ocorreu um erro inesperado. Voce pode tentar novamente ou voltar para a pagina inicial.
              </p>
            </CardHeader>

            <CardContent>
              {/* Error details in dev mode */}
              {process.env.NODE_ENV === "development" && error && (
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
                    {errorInfo?.componentStack && (
                      <details className="cursor-pointer">
                        <summary className="text-xs font-mono text-foreground-dim hover:text-foreground-muted transition-colors">
                          Ver stack trace
                        </summary>
                        <pre className="mt-2 max-h-32 overflow-auto rounded bg-background-deep p-2 text-xs font-mono text-foreground-dim">
                          {errorInfo.componentStack}
                        </pre>
                      </details>
                    )}
                  </div>
                </div>
              )}

              {/* Terminal-style status */}
              <div className="mt-4 flex items-center justify-center gap-2 text-foreground-dim text-xs font-mono opacity-60">
                <span className="inline-block w-2 h-2 bg-destructive rounded-full" />
                <span>erro capturado pelo boundary</span>
              </div>
            </CardContent>

            <CardFooter className="flex flex-col gap-2 sm:flex-row">
              <Button
                variant="default"
                onClick={this.handleReset}
                className="w-full sm:w-auto gap-2"
              >
                <RefreshCw className="h-4 w-4" />
                Tentar novamente
              </Button>
              <Button
                variant="outline"
                onClick={this.handleGoHome}
                className="w-full sm:w-auto gap-2"
              >
                <Home className="h-4 w-4" />
                Ir para Dashboard
              </Button>
            </CardFooter>
          </Card>
        </div>
      );
    }

    return children;
  }
}

/**
 * Hook wrapper para usar ErrorBoundary com componentes funcionais
 * Util para resetar o boundary quando a key muda
 */
interface ErrorBoundaryWrapperProps extends Omit<ErrorBoundaryProps, "children"> {
  children: ReactNode;
  resetKey?: string | number;
}

export function ErrorBoundaryWrapper({
  children,
  resetKey,
  ...props
}: ErrorBoundaryWrapperProps) {
  return (
    <ErrorBoundary key={resetKey} {...props}>
      {children}
    </ErrorBoundary>
  );
}
