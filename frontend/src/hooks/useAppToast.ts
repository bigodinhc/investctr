"use client";

/**
 * useAppToast - Convenience hook for toast notifications
 * Provides typed methods for success, error, warning, and info toasts
 * with consistent styling and auto-dismiss behavior.
 */

import { toast as baseToast } from "@/components/ui/use-toast";
import type { ToastActionElement } from "@/components/ui/toast";

type ToastOptions = {
  title?: string;
  description?: string;
  action?: ToastActionElement;
  duration?: number;
};

type SimpleToastOptions = string | ToastOptions;

function normalizeOptions(options: SimpleToastOptions): ToastOptions {
  if (typeof options === "string") {
    return { description: options };
  }
  return options;
}

/**
 * Success toast - for completed actions
 * Green styling with CheckCircle icon
 */
function success(options: SimpleToastOptions) {
  const { title, description, action, duration } = normalizeOptions(options);
  return baseToast({
    title: title || "Sucesso",
    description,
    variant: "success",
    action,
    duration: duration ?? 4000,
  });
}

/**
 * Error toast - for failed operations
 * Red styling with AlertCircle icon
 */
function error(options: SimpleToastOptions) {
  const { title, description, action, duration } = normalizeOptions(options);
  return baseToast({
    title: title || "Erro",
    description,
    variant: "destructive",
    action,
    duration: duration ?? 6000,
  });
}

/**
 * Warning toast - for potential issues
 * Yellow/amber styling with AlertTriangle icon
 */
function warning(options: SimpleToastOptions) {
  const { title, description, action, duration } = normalizeOptions(options);
  return baseToast({
    title: title || "Atencao",
    description,
    variant: "warning",
    action,
    duration: duration ?? 5000,
  });
}

/**
 * Info toast - for informational messages
 * Blue styling with Info icon
 */
function info(options: SimpleToastOptions) {
  const { title, description, action, duration } = normalizeOptions(options);
  return baseToast({
    title: title || "Informacao",
    description,
    variant: "info",
    action,
    duration: duration ?? 4000,
  });
}

/**
 * Promise toast - shows loading, success, or error based on promise result
 * Useful for async operations
 */
async function promise<T>(
  promiseOrFn: Promise<T> | (() => Promise<T>),
  options: {
    loading?: string;
    success?: string | ((data: T) => string);
    error?: string | ((error: Error) => string);
  }
): Promise<T> {
  const promiseValue =
    typeof promiseOrFn === "function" ? promiseOrFn() : promiseOrFn;

  const loadingToast = baseToast({
    title: "Processando...",
    description: options.loading || "Aguarde...",
    variant: "default",
    duration: Infinity,
  });

  try {
    const result = await promiseValue;
    loadingToast.dismiss();
    success({
      description:
        typeof options.success === "function"
          ? options.success(result)
          : options.success || "Operacao concluida com sucesso.",
    });
    return result;
  } catch (err) {
    loadingToast.dismiss();
    const errorMessage =
      typeof options.error === "function"
        ? options.error(err as Error)
        : options.error || (err as Error).message || "Ocorreu um erro.";
    error({ description: errorMessage });
    throw err;
  }
}

/**
 * App toast object with convenience methods
 */
export const appToast = {
  success,
  error,
  warning,
  info,
  promise,
  raw: baseToast,
};

/**
 * useAppToast hook - returns the appToast object
 * Can be used as a hook for consistency or imported directly as appToast
 */
export function useAppToast() {
  return appToast;
}

export default appToast;
