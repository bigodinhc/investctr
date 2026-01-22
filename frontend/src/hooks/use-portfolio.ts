/**
 * React Query hooks for portfolio
 */

import { useQuery } from "@tanstack/react-query";
import {
  getPortfolioSummary,
  getPortfolioHistory,
  getPortfolioAllocation,
  getConsolidatedPortfolio,
} from "@/lib/api/portfolio";
import type {
  AllocationFilters,
  PortfolioHistoryFilters,
} from "@/lib/api/types";

export const portfolioKeys = {
  all: ["portfolio"] as const,
  summary: (accountId?: string) => [...portfolioKeys.all, "summary", accountId] as const,
  history: (params?: PortfolioHistoryFilters) => [...portfolioKeys.all, "history", params] as const,
  allocation: (params?: AllocationFilters) => [...portfolioKeys.all, "allocation", params] as const,
  consolidated: () => [...portfolioKeys.all, "consolidated"] as const,
};

export function usePortfolioSummary(accountId?: string) {
  return useQuery({
    queryKey: portfolioKeys.summary(accountId),
    queryFn: () => getPortfolioSummary(accountId),
  });
}

export function usePortfolioHistory(params?: PortfolioHistoryFilters) {
  return useQuery({
    queryKey: portfolioKeys.history(params),
    queryFn: () => getPortfolioHistory(params),
  });
}

export function usePortfolioAllocation(params?: AllocationFilters) {
  return useQuery({
    queryKey: portfolioKeys.allocation(params),
    queryFn: () => getPortfolioAllocation(params),
  });
}

export function useConsolidatedPortfolio() {
  return useQuery({
    queryKey: portfolioKeys.consolidated(),
    queryFn: () => getConsolidatedPortfolio(),
  });
}
