/**
 * Accounts API functions
 */

import { api } from "./client";
import type {
  Account,
  AccountCreate,
  AccountUpdate,
  AccountsListResponse,
  PaginationParams,
} from "./types";

const BASE_PATH = "/api/v1/accounts";

export const accountsApi = {
  /**
   * List all accounts for the current user
   */
  list: async (params?: PaginationParams): Promise<AccountsListResponse> => {
    const queryParams: Record<string, string> = {};
    if (params?.skip !== undefined) queryParams.skip = params.skip.toString();
    if (params?.limit !== undefined) queryParams.limit = params.limit.toString();

    return api.get<AccountsListResponse>(BASE_PATH, queryParams);
  },

  /**
   * Get a single account by ID
   */
  get: async (id: string): Promise<Account> => {
    return api.get<Account>(`${BASE_PATH}/${id}`);
  },

  /**
   * Create a new account
   */
  create: async (data: AccountCreate): Promise<Account> => {
    return api.post<Account>(BASE_PATH, data);
  },

  /**
   * Update an existing account
   */
  update: async (id: string, data: AccountUpdate): Promise<Account> => {
    return api.put<Account>(`${BASE_PATH}/${id}`, data);
  },

  /**
   * Delete an account
   */
  delete: async (id: string): Promise<void> => {
    return api.delete<void>(`${BASE_PATH}/${id}`);
  },
};
