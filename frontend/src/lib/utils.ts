import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Re-export formatting utilities from format.ts for backwards compatibility
export {
  formatCurrency,
  formatPercent,
  formatNumber,
  formatQuantity,
  formatDate,
  formatFileSize,
  getPnLColor,
  formatCurrencyWithSign,
  type DateFormat,
} from "./format";
