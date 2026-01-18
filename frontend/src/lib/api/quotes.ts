/**
 * Quotes API functions
 */

import { api } from "./client";
import type { QuoteSyncResponse } from "./types";

export async function syncQuotes(): Promise<QuoteSyncResponse> {
  return api.post<QuoteSyncResponse>("/api/v1/quotes/sync", {});
}

export const quotesApi = {
  sync: syncQuotes,
};
