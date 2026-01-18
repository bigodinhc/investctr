/**
 * Fund API functions
 */

import { api } from "./client";
import type {
  FundPerformance,
  FundShare,
  FundShareFilters,
  FundSharesListResponse,
  NAVResponse,
} from "./types";

export async function getCurrentNAV(targetDate?: string): Promise<NAVResponse> {
  const queryParams: Record<string, string> = {};
  if (targetDate) queryParams.target_date = targetDate;

  return api.get<NAVResponse>("/api/v1/fund/nav", queryParams);
}

export async function getFundShares(
  params?: FundShareFilters
): Promise<FundSharesListResponse> {
  const queryParams: Record<string, string> = {};
  if (params?.start_date) queryParams.start_date = params.start_date;
  if (params?.end_date) queryParams.end_date = params.end_date;
  if (params?.limit) queryParams.limit = params.limit.toString();

  return api.get<FundSharesListResponse>("/api/v1/fund/shares", queryParams);
}

export async function getLatestFundShare(): Promise<FundShare | null> {
  try {
    return await api.get<FundShare>("/api/v1/fund/shares/latest");
  } catch (error) {
    // Return null if no fund share records exist (404)
    if (error instanceof Error &&
        (error.message.includes("No fund share records found") ||
         error.message.includes("404"))) {
      return null;
    }
    throw error;
  }
}

export async function getFundPerformance(): Promise<FundPerformance> {
  return api.get<FundPerformance>("/api/v1/fund/performance");
}

export async function calculateDailyShare(
  targetDate?: string
): Promise<FundShare> {
  const queryParams: Record<string, string> = {};
  if (targetDate) queryParams.target_date = targetDate;

  return api.post<FundShare>("/api/v1/fund/shares/calculate", undefined);
}

export const fundApi = {
  nav: getCurrentNAV,
  shares: getFundShares,
  latestShare: getLatestFundShare,
  performance: getFundPerformance,
  calculateShare: calculateDailyShare,
};
