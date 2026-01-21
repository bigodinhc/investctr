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
  | "bond"
  | "treasury"
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

export type ParsingStage = "downloading" | "processing_ai" | "validating" | null;

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
  parsing_stage: ParsingStage;
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
  quantity: number | string | null;
  price: number | string | null;
  total: number | string | null;
  fees: number | string | null;
  notes: string | null;
}

export interface ParsedFixedIncome {
  asset_name: string;
  asset_type: string;
  issuer: string | null;
  quantity: number | string;
  unit_price: number | string | null;
  total_value: number | string;
  indexer: string | null;
  rate_percent: number | string | null;
  acquisition_date: string | null;
  maturity_date: string | null;
  reference_date?: string;
}

export interface ParsedStockLending {
  date: string;
  type: string; // lending_out, lending_return
  ticker: string;
  quantity: number | string;
  rate_percent: number | string | null;
  total: number | string;
  notes: string | null;
}

export interface ParsedCashMovement {
  date: string;
  type: string;
  description: string | null;
  ticker: string | null;
  value: number | string;
}

export interface ParsedInvestmentFund {
  fund_name: string;
  cnpj: string | null;
  quota_quantity: number | string;
  quota_price: number | string | null;
  gross_balance: number | string;
  ir_provision: number | string | null;
  net_balance: number | string | null;
  performance_pct: number | string | null;
  reference_date?: string;
}

export interface ParsedDocumentData {
  document_type: string;
  period: { start: string; end: string } | null;
  account_number: string | null;
  transactions: ParsedTransaction[];
  fixed_income_positions?: ParsedFixedIncome[];
  stock_lending?: ParsedStockLending[];
  cash_movements?: ParsedCashMovement[];
  investment_funds?: ParsedInvestmentFund[];
  summary: Record<string, number | string> | null;
  consolidated_position?: {
    total_stocks: number | string | null;
    total_fixed_income: number | string | null;
    total_investment_funds: number | string | null;
    total_cash: number | string | null;
    grand_total: number | string | null;
  };
}

export interface DocumentParseResponse {
  document_id: string;
  status: ParsingStatus;
  stage: ParsingStage;
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

export interface CommitFixedIncomeItem {
  asset_name: string;
  asset_type: string;
  issuer?: string | null;
  quantity: number;
  unit_price?: number | null;
  total_value: number;
  indexer?: string | null;
  rate_percent?: number | null;
  acquisition_date?: string | null;
  maturity_date?: string | null;
  reference_date?: string;
}

export interface CommitStockLendingItem {
  date: string;
  type: string;
  ticker: string;
  quantity: number;
  rate_percent?: number | null;
  total: number;
  notes?: string | null;
}

export interface CommitCashMovementItem {
  date: string;
  type: string;
  description?: string | null;
  ticker?: string | null;
  value: number;
}

export interface CommitInvestmentFundItem {
  fund_name: string;
  cnpj?: string | null;
  quota_quantity: number;
  quota_price?: number | null;
  gross_balance: number;
  ir_provision?: number | null;
  net_balance?: number | null;
  performance_pct?: number | null;
  reference_date: string;
}

export interface CommitDocumentRequest {
  account_id: string;
  transactions: CommitTransactionItem[];
  fixed_income?: CommitFixedIncomeItem[];
  stock_lending?: CommitStockLendingItem[];
  cash_movements?: CommitCashMovementItem[];
  investment_funds?: CommitInvestmentFundItem[];
}

export interface CommitDocumentResponse {
  document_id: string;
  transactions_created: number;
  assets_created: number;
  positions_updated: number;
  fixed_income_created: number;
  cash_flows_created: number;
  investment_funds_created: number;
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

// Quote Types
export interface QuoteSyncResponse {
  message: string;
  assets_synced: number;
  quotes_updated: number;
  errors: string[];
}

// Cash Flow Types
export type CashFlowType =
  | "deposit"
  | "withdrawal"
  | "dividend"
  | "jcp"
  | "interest"
  | "fee"
  | "tax"
  | "settlement"
  | "rental_income"
  | "other";

// Fixed Income Types
export type FixedIncomeType =
  | "cdb"
  | "lca"
  | "lci"
  | "lft"
  | "ntnb"
  | "ntnf"
  | "lf"
  | "debenture"
  | "cri"
  | "cra"
  | "other";

export type IndexerType =
  | "cdi"
  | "selic"
  | "ipca"
  | "igpm"
  | "prefixado"
  | "other";

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

// Portfolio Summary Types (from /api/v1/portfolio/summary)
export interface AssetTypeSummary {
  asset_type: AssetType;
  positions_count: number;
  total_cost: string;
  market_value: string | null;
  unrealized_pnl: string | null;
  unrealized_pnl_pct: string | null;
  allocation_pct: string | null;
}

export interface AccountSummary {
  account_id: string;
  account_name: string;
  broker: string | null;
  positions_count: number;
  total_cost: string;
  market_value: string | null;
  unrealized_pnl: string | null;
  unrealized_pnl_pct: string | null;
  allocation_pct: string | null;
}

export interface PortfolioSummaryResponse {
  total_positions: number;
  total_value: string;
  total_cost: string;
  total_unrealized_pnl: string;
  total_unrealized_pnl_pct: string | null;
  total_realized_pnl: string;

  // Position counts by type
  long_positions_count: number;
  short_positions_count: number;

  // Exposure metrics (for long/short portfolios)
  long_value: string;
  short_value: string;
  gross_exposure: string;
  net_exposure: string;
  gross_exposure_pct: string | null;
  net_exposure_pct: string | null;

  by_asset_type: AssetTypeSummary[];
  by_account: AccountSummary[];
  accounts_count: number;
  last_price_update: string | null;
}

// Fund Types
export interface NAVResponse {
  user_id: string;
  date: string;
  nav: string;
  total_market_value: string;
  total_cash: string;
  positions_count: number;
  positions_with_prices: number;
}

export interface FundShare {
  id: string;
  user_id: string;
  date: string;
  nav: string;
  shares_outstanding: string;
  share_value: string;
  daily_return: string | null;
  cumulative_return: string | null;
  created_at: string;
}

export interface FundSharesListResponse {
  items: FundShare[];
  total: number;
}

export interface FundPerformance {
  current_nav: string;
  current_share_value: string;
  shares_outstanding: string;
  total_return: string | null;
  daily_return: string | null;
  mtd_return: string | null;
  ytd_return: string | null;
  one_year_return: string | null;
  max_drawdown: string | null;
  volatility: string | null;
}

export interface FundShareFilters {
  start_date?: string;
  end_date?: string;
  limit?: number;
}

// Portfolio History Types
export type PeriodType = "1M" | "3M" | "6M" | "1Y" | "YTD" | "MAX";

export interface PortfolioHistoryItem {
  date: string;
  nav: string;
  total_cost: string;
  realized_pnl: string;
  unrealized_pnl: string;
  share_value?: string;
  cumulative_return?: string;
}

export interface PortfolioHistoryResponse {
  items: PortfolioHistoryItem[];
  total: number;
  period_return: string | null;
  start_nav: string | null;
  end_nav: string | null;
}

export interface PortfolioHistoryFilters {
  period?: PeriodType;
  account_id?: string;
  limit?: number;
}

// Portfolio Allocation Types
export interface AllocationItem {
  name: string;
  value: string;
  percentage: string;
  color: string | null;
}

export interface AllocationResponse {
  by_asset_type: AllocationItem[];
  by_asset: AllocationItem[];
  total_value: string;
  positions_count: number;
}

export interface AllocationFilters {
  account_id?: string;
  top_assets?: number;
}
