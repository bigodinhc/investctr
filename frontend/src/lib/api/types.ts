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
