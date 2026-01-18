/**
 * Centralized formatting utilities for consistent display across the application.
 * All currency, date, number, and percentage formatting should use these functions.
 */

export type DateFormat = "short" | "medium" | "long" | "relative" | "datetime" | "datetime-short";

/**
 * Format a number as currency (default: BRL).
 * @param value - The number to format
 * @param currency - The currency code (default: "BRL")
 * @returns Formatted currency string (e.g., "R$ 1.234,56")
 */
export function formatCurrency(
  value: number | string | null | undefined,
  currency: string = "BRL"
): string {
  if (value === null || value === undefined || value === "") return "-";
  const numValue = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(numValue)) return "-";

  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency,
  }).format(numValue);
}

/**
 * Format a number as a percentage with +/- sign.
 * @param value - The number to format
 * @param decimals - Number of decimal places (default: 2)
 * @param showSign - Whether to show +/- sign (default: true)
 * @returns Formatted percentage string (e.g., "+12.34%")
 */
export function formatPercent(
  value: number | string | null | undefined,
  decimals: number = 2,
  showSign: boolean = true
): string {
  if (value === null || value === undefined || value === "") return "-";
  const numValue = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(numValue)) return "-";

  const sign = showSign && numValue >= 0 ? "+" : "";
  return `${sign}${numValue.toFixed(decimals)}%`;
}

/**
 * Format a number with locale-specific formatting.
 * @param value - The number to format
 * @param decimals - Number of decimal places (default: 2)
 * @returns Formatted number string (e.g., "1.234,56")
 */
export function formatNumber(
  value: number | string | null | undefined,
  decimals: number = 2
): string {
  if (value === null || value === undefined || value === "") return "-";
  const numValue = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(numValue)) return "-";

  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(numValue);
}

/**
 * Format a quantity (number without forced decimal places).
 * @param value - The number to format
 * @param maxDecimals - Maximum decimal places (default: 6)
 * @returns Formatted number string
 */
export function formatQuantity(
  value: number | string | null | undefined,
  maxDecimals: number = 6
): string {
  if (value === null || value === undefined || value === "") return "-";
  const numValue = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(numValue)) return "-";

  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: maxDecimals,
  }).format(numValue);
}

/**
 * Format a date with various format options.
 * @param date - The date to format (Date object or ISO string)
 * @param format - The format style (default: "short")
 * @returns Formatted date string
 *
 * Format options:
 * - "short": "18/01/2026"
 * - "medium": "18 Jan 2026"
 * - "long": "18 de janeiro de 2026"
 * - "relative": "há 5 min", "ontem", etc.
 * - "datetime": "18 Jan 2026, 14:30"
 * - "datetime-short": "18/01 14:30"
 */
export function formatDate(
  date: Date | string | null | undefined,
  format: DateFormat = "short"
): string {
  if (!date) return "-";

  const d = typeof date === "string" ? new Date(date) : date;
  if (isNaN(d.getTime())) return "-";

  switch (format) {
    case "short":
      return new Intl.DateTimeFormat("pt-BR", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
      }).format(d);

    case "medium":
      return new Intl.DateTimeFormat("pt-BR", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      }).format(d);

    case "long":
      return new Intl.DateTimeFormat("pt-BR", {
        day: "2-digit",
        month: "long",
        year: "numeric",
      }).format(d);

    case "relative":
      return formatRelativeDate(d);

    case "datetime":
      return new Intl.DateTimeFormat("pt-BR", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      }).format(d);

    case "datetime-short":
      return new Intl.DateTimeFormat("pt-BR", {
        day: "2-digit",
        month: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      }).format(d);

    default:
      return new Intl.DateTimeFormat("pt-BR").format(d);
  }
}

/**
 * Format a date as relative time (e.g., "há 5 min", "ontem").
 * @param date - The date to format
 * @returns Relative time string
 */
function formatRelativeDate(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 1) return "agora";
  if (diffMins < 60) return `há ${diffMins} min`;
  if (diffHours < 24) return `há ${diffHours}h`;
  if (diffDays === 1) return "ontem";
  if (diffDays < 7) return `há ${diffDays} dias`;

  return formatDate(date, "medium");
}

/**
 * Format a file size in bytes to human-readable format.
 * @param bytes - The file size in bytes
 * @returns Formatted file size string (e.g., "1.5 MB")
 */
export function formatFileSize(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined) return "-";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}

/**
 * Get CSS class for P&L color based on value.
 * @param value - The P&L value
 * @returns CSS class name for the color
 */
export function getPnLColor(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "text-foreground-muted";
  const numValue = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(numValue)) return "text-foreground-muted";

  if (numValue > 0) return "text-success";
  if (numValue < 0) return "text-destructive";
  return "text-foreground-muted";
}

/**
 * Format a number as currency with a +/- sign prefix.
 * @param value - The number to format
 * @param currency - The currency code (default: "BRL")
 * @returns Formatted currency string with sign (e.g., "+R$ 1.234,56")
 */
export function formatCurrencyWithSign(
  value: number | string | null | undefined,
  currency: string = "BRL"
): string {
  if (value === null || value === undefined || value === "") return "-";
  const numValue = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(numValue)) return "-";

  const formatted = formatCurrency(Math.abs(numValue), currency);
  return numValue >= 0 ? `+${formatted}` : `-${formatted.replace("-", "")}`;
}
