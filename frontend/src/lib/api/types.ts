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

// Transaction Types
export type TransactionType =
  | "buy"
  | "sell"
  | "dividend"
  | "jcp"
  | "income"
  | "amortization"
  | "split"
  | "subscription"
  | "transfer_in"
  | "transfer_out"
  | "rental"
  | "other";

export type PositionType = "long" | "short";

export interface Transaction {
  id: string;
  account_id: string;
  asset_id: string;
  document_id: string | null;
  type: TransactionType;
  quantity: string;
  price: string;
  total_value: string | null;
  fees: string;
  currency: string;
  exchange_rate: string;
  executed_at: string;
  notes: string | null;
  created_at: string;
}

export interface TransactionWithAsset extends Transaction {
  ticker: string;
  asset_name: string;
}

export interface TransactionCreate {
  account_id: string;
  asset_id: string;
  document_id?: string;
  type: TransactionType;
  quantity: string;
  price: string;
  fees?: string;
  currency?: Currency;
  exchange_rate?: string;
  executed_at: string;
  notes?: string;
}

export interface TransactionUpdate {
  type?: TransactionType;
  quantity?: string;
  price?: string;
  fees?: string;
  executed_at?: string;
  notes?: string;
}

export interface TransactionsListResponse {
  items: Transaction[];
  total: number;
}

export interface TransactionsWithAssetListResponse {
  items: TransactionWithAsset[];
  total: number;
}

export interface TransactionFilters extends PaginationParams {
  account_id?: string;
  asset_id?: string;
  type_filter?: TransactionType;
  start_date?: string;
  end_date?: string;
}

// Commit Types
export interface CommitTransactionItem {
  date: string;
  type: string;
  ticker: string;
  asset_name?: string;
  asset_type?: string;
  quantity?: number | null;
  price?: number | null;
  total?: number | null;
  fees?: number | null;
  notes?: string | null;
}

export interface CommitDocumentRequest {
  account_id: string;
  transactions: CommitTransactionItem[];
}

export interface CommitDocumentResponse {
  document_id: string;
  transactions_created: number;
  assets_created: number;
  positions_updated: number;
  errors: string[];
}

// Position Types
export interface Position {
  id: string;
  account_id: string;
  asset_id: string;
  quantity: string;
  avg_price: string;
  total_cost: string;
  position_type: PositionType;
  opened_at: string | null;
  updated_at: string;
}

export interface PositionWithAsset extends Position {
  ticker: string;
  asset_name: string;
  asset_type: AssetType;
}

export interface PositionWithMarketData extends PositionWithAsset {
  current_price: string | null;
  market_value: string | null;
  unrealized_pnl: string | null;
  unrealized_pnl_pct: string | null;
  price_updated_at: string | null;
  is_profitable: boolean | null;
}

export interface PositionsListResponse {
  items: Position[];
  total: number;
}

export interface PositionsWithMarketDataResponse {
  items: PositionWithMarketData[];
  total: number;
  total_market_value: string;
  total_cost: string;
  total_unrealized_pnl: string;
  total_unrealized_pnl_pct: string | null;
}

export interface ConsolidatedPosition {
  asset_id: string;
  ticker: string;
  asset_name: string;
  asset_type: AssetType;
  total_quantity: string;
  weighted_avg_price: string;
  total_cost: string;
  current_price: string | null;
  market_value: string | null;
  unrealized_pnl: string | null;
  unrealized_pnl_pct: string | null;
  accounts_count: number;
}

export interface ConsolidatedPositionsResponse {
  items: ConsolidatedPosition[];
  total: number;
  total_market_value: string;
  total_cost: string;
  total_unrealized_pnl: string;
  total_unrealized_pnl_pct: string | null;
}

export interface PositionSummary {
  asset_type: AssetType;
  positions_count: number;
  total_cost: string;
  market_value: string | null;
  unrealized_pnl: string | null;
  allocation_pct: string | null;
}

export interface PortfolioSummary {
  total_positions: number;
  total_cost: string;
  total_market_value: string | null;
  total_unrealized_pnl: string | null;
  total_unrealized_pnl_pct: string | null;
  by_asset_type: PositionSummary[];
  last_updated: string | null;
}

export interface PositionFilters extends PaginationParams {
  account_id?: string;
  asset_type?: AssetType;
  min_value?: string;
}

// Cash Flow Types
export type CashFlowType = "deposit" | "withdrawal";

export interface CashFlow {
  id: string;
  account_id: string;
  type: CashFlowType;
  amount: string;
  currency: string;
  exchange_rate: string;
  executed_at: string;
  shares_affected: string | null;
  notes: string | null;
  created_at: string;
}

export interface CashFlowCreate {
  account_id: string;
  type: CashFlowType;
  amount: string;
  currency?: Currency;
  exchange_rate?: string;
  executed_at: string;
  shares_affected?: string;
  notes?: string;
}

export interface CashFlowUpdate {
  type?: CashFlowType;
  amount?: string;
  currency?: Currency;
  exchange_rate?: string;
  executed_at?: string;
  shares_affected?: string;
  notes?: string;
}

export interface CashFlowsListResponse {
  items: CashFlow[];
  total: number;
}

export interface CashFlowFilters extends PaginationParams {
  account_id?: string;
}
