/**
 * API Types matching backend schemas
 */

// Enums
export type AccountType = "btg_personal" | "btg_corporate" | "xp" | "btg_cayman" | "other";
export type Currency = "BRL" | "USD" | "EUR";

// Account
export interface Account {
  id: string;
  user_id: string;
  name: string;
  type: AccountType;
  currency: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AccountCreate {
  name: string;
  type: AccountType;
  currency: Currency;
}

export interface AccountUpdate {
  name?: string;
  type?: AccountType;
  currency?: Currency;
}

export interface AccountsListResponse {
  items: Account[];
  total: number;
}

// Asset
export type AssetType =
  | "stock"
  | "etf"
  | "reit"
  | "bdr"
  | "fund"
  | "fixed_income"
  | "crypto"
  | "option"
  | "future"
  | "currency"
  | "other";

export interface Asset {
  id: string;
  ticker: string;
  name: string;
  type: AssetType;
  currency: string;
  exchange: string | null;
  isin: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AssetCreate {
  ticker: string;
  name: string;
  type: AssetType;
  currency: Currency;
  exchange?: string;
  isin?: string;
}

export interface AssetUpdate {
  ticker?: string;
  name?: string;
  type?: AssetType;
  currency?: Currency;
  exchange?: string;
  isin?: string;
}

export interface AssetsListResponse {
  items: Asset[];
  total: number;
}

// Pagination
export interface PaginationParams {
  skip?: number;
  limit?: number;
}

// Document
export type DocumentType = "statement" | "trade_note" | "income_report" | "other";
export type ParsingStatus = "pending" | "processing" | "completed" | "failed";

export interface Document {
  id: string;
  user_id: string;
  doc_type: DocumentType;
  account_id: string | null;
  file_name: string;
  file_path: string;
  file_size: number | null;
  parsing_status: ParsingStatus;
  parsing_error: string | null;
  parsed_at: string | null;
  created_at: string;
}

export interface DocumentWithData extends Document {
  raw_extracted_data: Record<string, unknown> | null;
}

export interface DocumentsListResponse {
  items: Document[];
  total: number;
}

export interface DocumentUpload {
  doc_type: DocumentType;
  account_id?: string;
}

export interface ParsedTransaction {
  date: string;
  type: string;
  ticker: string;
  quantity: number | null;
  price: number | null;
  total: number | null;
  fees: number | null;
  notes: string | null;
}

export interface ParsedDocumentData {
  document_type: string;
  period: { start: string; end: string } | null;
  account_number: string | null;
  transactions: ParsedTransaction[];
  summary: Record<string, number> | null;
}

export interface DocumentParseResponse {
  document_id: string;
  status: ParsingStatus;
  transactions_count: number;
  data: ParsedDocumentData | null;
  error: string | null;
}

export interface ParseTaskResponse {
  document_id: string;
  task_id: string;
  status: ParsingStatus;
  message: string;
}
