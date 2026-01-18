/**
 * Positions API functions
 */

import { api } from "./client";
import type {
  PositionWithMarketData,
  PositionsWithMarketDataResponse,
  ConsolidatedPositionsResponse,
  PortfolioSummary,
  PositionFilters,
  AssetType,
} from "./types";

export async function getPositions(
  params?: PositionFilters
): Promise<PositionsWithMarketDataResponse> {
  const queryParams: Record<string, string> = {};

  if (params?.skip !== undefined) queryParams.skip = params.skip.toString();
  if (params?.limit !== undefined) queryParams.limit = params.limit.toString();
  if (params?.account_id) queryParams.account_id = params.account_id;
  if (params?.asset_type) queryParams.asset_type = params.asset_type;
  if (params?.min_value) queryParams.min_value = params.min_value;

  return api.get<PositionsWithMarketDataResponse>("/api/v1/positions", queryParams);
}

export async function getPosition(id: string): Promise<PositionWithMarketData> {
  return api.get<PositionWithMarketData>(`/api/v1/positions/${id}`);
}

export async function getConsolidatedPositions(
  assetType?: AssetType
): Promise<ConsolidatedPositionsResponse> {
  const queryParams: Record<string, string> = {};
  if (assetType) queryParams.asset_type = assetType;

  return api.get<ConsolidatedPositionsResponse>(
    "/api/v1/positions/consolidated",
    queryParams
  );
}

export async function getPositionsSummary(
  accountId?: string
): Promise<PortfolioSummary> {
  const queryParams: Record<string, string> = {};
  if (accountId) queryParams.account_id = accountId;

  return api.get<PortfolioSummary>("/api/v1/positions/summary", queryParams);
}

export async function recalculatePositions(
  accountId: string
): Promise<{ message: string; positions_updated: number }> {
  return api.post(`/api/v1/positions/${accountId}/recalculate`, {});
}

export const positionsApi = {
  list: getPositions,
  get: getPosition,
  consolidated: getConsolidatedPositions,
  summary: getPositionsSummary,
  recalculate: recalculatePositions,
};
