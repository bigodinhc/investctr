/**
 * Portfolio API functions
 */

import { api } from "./client";
import type {
  AllocationFilters,
  AllocationResponse,
  PeriodType,
  PortfolioHistoryFilters,
  PortfolioHistoryResponse,
  PortfolioSummaryResponse,
} from "./types";

export async function getPortfolioSummary(
  accountId?: string
): Promise<PortfolioSummaryResponse> {
  const queryParams: Record<string, string> = {};
  if (accountId) queryParams.account_id = accountId;

  return api.get<PortfolioSummaryResponse>("/api/v1/portfolio/summary", queryParams);
}

export async function getPortfolioHistory(
  params?: PortfolioHistoryFilters
): Promise<PortfolioHistoryResponse> {
  const queryParams: Record<string, string> = {};
  if (params?.period) queryParams.period = params.period;
  if (params?.account_id) queryParams.account_id = params.account_id;
  if (params?.limit) queryParams.limit = params.limit.toString();

  return api.get<PortfolioHistoryResponse>("/api/v1/portfolio/history", queryParams);
}

export async function getPortfolioAllocation(
  params?: AllocationFilters
): Promise<AllocationResponse> {
  const queryParams: Record<string, string> = {};
  if (params?.account_id) queryParams.account_id = params.account_id;
  if (params?.top_assets) queryParams.top_assets = params.top_assets.toString();

  return api.get<AllocationResponse>("/api/v1/portfolio/allocation", queryParams);
}

export const portfolioApi = {
  summary: getPortfolioSummary,
  history: getPortfolioHistory,
  allocation: getPortfolioAllocation,
};
