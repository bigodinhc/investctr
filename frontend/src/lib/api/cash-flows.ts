/**
 * Cash Flows API functions
 */

import { api } from "./client";
import type {
  CashFlow,
  CashFlowCreate,
  CashFlowUpdate,
  CashFlowsListResponse,
  CashFlowFilters,
} from "./types";

const BASE_PATH = "/api/v1/cash-flows";

export const cashFlowsApi = {
  /**
   * List all cash flows for the current user
   */
  list: async (params?: CashFlowFilters): Promise<CashFlowsListResponse> => {
    const queryParams: Record<string, string> = {};
    if (params?.skip !== undefined) queryParams.skip = params.skip.toString();
    if (params?.limit !== undefined) queryParams.limit = params.limit.toString();
    if (params?.account_id) queryParams.account_id = params.account_id;

    return api.get<CashFlowsListResponse>(BASE_PATH, queryParams);
  },

  /**
   * Get a single cash flow by ID
   */
  get: async (id: string): Promise<CashFlow> => {
    return api.get<CashFlow>(`${BASE_PATH}/${id}`);
  },

  /**
   * Create a new cash flow
   */
  create: async (data: CashFlowCreate): Promise<CashFlow> => {
    return api.post<CashFlow>(BASE_PATH, data);
  },

  /**
   * Update an existing cash flow
   */
  update: async (id: string, data: CashFlowUpdate): Promise<CashFlow> => {
    return api.put<CashFlow>(`${BASE_PATH}/${id}`, data);
  },

  /**
   * Delete a cash flow
   */
  delete: async (id: string): Promise<void> => {
    return api.delete<void>(`${BASE_PATH}/${id}`);
  },
};
