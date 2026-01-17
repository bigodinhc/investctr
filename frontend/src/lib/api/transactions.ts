/**
 * Transactions API functions
 */

import { api } from "./client";
import type {
  Transaction,
  TransactionWithAsset,
  TransactionsWithAssetListResponse,
  TransactionCreate,
  TransactionUpdate,
  TransactionFilters,
  CommitDocumentRequest,
  CommitDocumentResponse,
} from "./types";

export async function getTransactions(
  params?: TransactionFilters
): Promise<TransactionsWithAssetListResponse> {
  const queryParams: Record<string, string> = {};

  if (params?.skip !== undefined) queryParams.skip = params.skip.toString();
  if (params?.limit !== undefined) queryParams.limit = params.limit.toString();
  if (params?.account_id) queryParams.account_id = params.account_id;
  if (params?.asset_id) queryParams.asset_id = params.asset_id;
  if (params?.type_filter) queryParams.type_filter = params.type_filter;
  if (params?.start_date) queryParams.start_date = params.start_date;
  if (params?.end_date) queryParams.end_date = params.end_date;

  return api.get<TransactionsWithAssetListResponse>("/api/v1/transactions", queryParams);
}

export async function getTransaction(id: string): Promise<TransactionWithAsset> {
  return api.get<TransactionWithAsset>(`/api/v1/transactions/${id}`);
}

export async function createTransaction(
  data: TransactionCreate
): Promise<Transaction> {
  return api.post<Transaction>("/api/v1/transactions", data);
}

export async function updateTransaction(
  id: string,
  data: TransactionUpdate
): Promise<Transaction> {
  return api.put<Transaction>(`/api/v1/transactions/${id}`, data);
}

export async function deleteTransaction(id: string): Promise<void> {
  return api.delete(`/api/v1/transactions/${id}`);
}

export async function commitDocumentTransactions(
  documentId: string,
  data: CommitDocumentRequest
): Promise<CommitDocumentResponse> {
  return api.post<CommitDocumentResponse>(
    `/api/v1/documents/${documentId}/commit`,
    data
  );
}

export const transactionsApi = {
  list: getTransactions,
  get: getTransaction,
  create: createTransaction,
  update: updateTransaction,
  delete: deleteTransaction,
  commitDocument: commitDocumentTransactions,
};
