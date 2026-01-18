"use client";

import React from "react";
import { AlertTriangle, RefreshCw, Home } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * Error Boundary component to catch JavaScript errors in child components
 * and display a fallback UI instead of crashing the whole app.
 */
class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    // Log error to console in development
    console.error("ErrorBoundary caught an error:", error, errorInfo);

    // Call optional error handler (for error reporting services like Sentry)
    this.props.onError?.(error, errorInfo);
  }

  handleRetry = (): void => {
    this.setState({ hasError: false, error: null });
  };

  handleGoHome = (): void => {
    window.location.href = "/dashboard";
  };

  render(): React.ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex flex-col items-center justify-center min-h-[400px] p-8">
          <div className="rounded-full bg-destructive/10 p-4 mb-6">
            <AlertTriangle className="h-12 w-12 text-destructive" />
          </div>
          <h2 className="text-xl font-semibold text-foreground mb-2">
            Algo deu errado
          </h2>
          <p className="text-foreground-muted text-center max-w-md mb-6">
            Ocorreu um erro inesperado. Tente recarregar a pagina ou voltar para o inicio.
          </p>
          {process.env.NODE_ENV === "development" && this.state.error && (
            <pre className="glass-card-subtle p-4 mb-6 max-w-lg overflow-auto text-xs text-destructive">
              {this.state.error.message}
            </pre>
          )}
          <div className="flex gap-3">
            <Button variant="outline" onClick={this.handleRetry}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Tentar novamente
            </Button>
            <Button onClick={this.handleGoHome}>
              <Home className="h-4 w-4 mr-2" />
              Ir para o inicio
            </Button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * Hook-based error boundary wrapper for functional components
 */
interface ErrorBoundaryWrapperProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  fallback?: React.ReactNode
): React.FC<P> {
  return function WrappedComponent(props: P) {
    return (
      <ErrorBoundary fallback={fallback}>
        <Component {...props} />
      </ErrorBoundary>
    );
  };
}

/**
 * Page-level error boundary with full-page error UI
 */
function PageErrorBoundary({ children }: { children: React.ReactNode }) {
  return (
    <ErrorBoundary
      fallback={
        <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-mesh p-8">
          <div className="rounded-full bg-destructive/10 p-6 mb-8">
            <AlertTriangle className="h-16 w-16 text-destructive" />
          </div>
          <h1 className="text-2xl font-bold text-foreground mb-3">
            Erro na aplicacao
          </h1>
          <p className="text-foreground-muted text-center max-w-md mb-8">
            A pagina encontrou um erro e nao pode ser exibida.
            Por favor, recarregue ou volte para a pagina inicial.
          </p>
          <div className="flex gap-4">
            <Button
              variant="outline"
              size="lg"
              onClick={() => window.location.reload()}
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Recarregar
            </Button>
            <Button size="lg" onClick={() => (window.location.href = "/dashboard")}>
              <Home className="h-4 w-4 mr-2" />
              Pagina inicial
            </Button>
          </div>
        </div>
      }
    >
      {children}
    </ErrorBoundary>
  );
}

/**
 * Section-level error boundary with compact error UI
 */
function SectionErrorBoundary({
  children,
  title = "Esta secao",
}: {
  children: React.ReactNode;
  title?: string;
}) {
  return (
    <ErrorBoundary
      fallback={
        <div className="flex flex-col items-center justify-center py-12 px-4 glass-card">
          <AlertTriangle className="h-8 w-8 text-destructive mb-3" />
          <p className="text-sm text-foreground-muted text-center mb-4">
            {title} nao pode ser carregada
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => window.location.reload()}
          >
            <RefreshCw className="h-3 w-3 mr-2" />
            Recarregar
          </Button>
        </div>
      }
    >
      {children}
    </ErrorBoundary>
  );
}

export {
  ErrorBoundary,
  PageErrorBoundary,
  SectionErrorBoundary,
  withErrorBoundary,
};
