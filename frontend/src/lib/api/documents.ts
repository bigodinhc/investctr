/**
 * Documents API functions
 */

import { api } from "./client";
import type {
  Document,
  DocumentWithData,
  DocumentsListResponse,
  DocumentType,
  DocumentParseResponse,
  ParseTaskResponse,
  PaginationParams,
} from "./types";

export async function getDocuments(
  params?: PaginationParams
): Promise<DocumentsListResponse> {
  const queryParams: Record<string, string> = {};
  if (params?.skip !== undefined) queryParams.skip = params.skip.toString();
  if (params?.limit !== undefined) queryParams.limit = params.limit.toString();

  return api.get<DocumentsListResponse>("/api/v1/documents", queryParams);
}

export async function getDocument(id: string): Promise<DocumentWithData> {
  return api.get<DocumentWithData>(`/api/v1/documents/${id}`);
}

export async function uploadDocument(
  file: File,
  docType: DocumentType,
  accountId?: string
): Promise<Document> {
  const additionalData: Record<string, string> = {
    doc_type: docType,
  };
  if (accountId) {
    additionalData.account_id = accountId;
  }

  return api.uploadFile<Document>("/api/v1/documents/upload", file, additionalData);
}

export async function parseDocument(
  documentId: string,
  asyncMode: boolean = true
): Promise<ParseTaskResponse | DocumentParseResponse> {
  return api.post(`/api/v1/documents/${documentId}/parse`, { async_mode: asyncMode });
}

export async function getParseResult(
  documentId: string
): Promise<DocumentParseResponse> {
  return api.get<DocumentParseResponse>(`/api/v1/documents/${documentId}/parse-result`);
}

export async function deleteDocument(id: string): Promise<void> {
  return api.delete(`/api/v1/documents/${id}`);
}
