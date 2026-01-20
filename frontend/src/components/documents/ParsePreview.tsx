"use client";

import { useState, useCallback } from "react";
import { Pencil, Trash2, Save, X, AlertCircle, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type {
  ParsedTransaction,
  ParsedDocumentData,
  ParsedFixedIncome,
  ParsedStockLending,
  ParsedCashMovement,
  ParsedInvestmentFund,
  CommitDocumentRequest,
} from "@/lib/api/types";
import { FixedIncomeTable } from "./FixedIncomeTable";
import { StockLendingTable } from "./StockLendingTable";
import { CashMovementsTable } from "./CashMovementsTable";
import { InvestmentFundsTable } from "./InvestmentFundsTable";
import { DocumentSummary } from "./DocumentSummary";

const TRANSACTION_TYPES = [
  { value: "buy", label: "Compra", color: "success" },
  { value: "sell", label: "Venda", color: "destructive" },
  { value: "dividend", label: "Dividendo", color: "info" },
  { value: "jcp", label: "JCP", color: "info" },
  { value: "split", label: "Desdobramento", color: "warning" },
  { value: "bonus", label: "Bonificação", color: "warning" },
  { value: "transfer_in", label: "Transferência (entrada)", color: "muted" },
  { value: "transfer_out", label: "Transferência (saída)", color: "muted" },
  { value: "other", label: "Outro", color: "default" },
] as const;

interface EditableTransaction extends ParsedTransaction {
  id: string;
  isEditing?: boolean;
  isSelected?: boolean;
}

interface ParsePreviewProps {
  data: ParsedDocumentData;
  onConfirm?: (data: Omit<CommitDocumentRequest, "account_id">) => void;
  onCancel?: () => void;
  isLoading?: boolean;
}

export function ParsePreview({ data, onConfirm, onCancel, isLoading }: ParsePreviewProps) {
  const [transactions, setTransactions] = useState<EditableTransaction[]>(() =>
    data.transactions.map((t, i) => ({
      ...t,
      id: `txn-${i}`,
      isEditing: false,
      isSelected: true,
    }))
  );

  const [selectedFixedIncome, setSelectedFixedIncome] = useState<ParsedFixedIncome[]>(
    data.fixed_income_positions || []
  );
  const [selectedStockLending, setSelectedStockLending] = useState<ParsedStockLending[]>(
    data.stock_lending || []
  );
  const [selectedCashMovements, setSelectedCashMovements] = useState<ParsedCashMovement[]>(
    data.cash_movements || []
  );
  const [selectedInvestmentFunds, setSelectedInvestmentFunds] = useState<ParsedInvestmentFund[]>(
    data.investment_funds || []
  );

  const [editingRow, setEditingRow] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<ParsedTransaction | null>(null);

  const startEdit = (txn: EditableTransaction) => {
    setEditingRow(txn.id);
    setEditForm({
      date: txn.date,
      type: txn.type,
      ticker: txn.ticker,
      quantity: txn.quantity,
      price: txn.price,
      total: txn.total,
      fees: txn.fees,
      notes: txn.notes,
    });
  };

  const cancelEdit = () => {
    setEditingRow(null);
    setEditForm(null);
  };

  const saveEdit = () => {
    if (!editingRow || !editForm) return;

    setTransactions((prev) =>
      prev.map((t) =>
        t.id === editingRow
          ? { ...t, ...editForm, isEditing: false }
          : t
      )
    );
    setEditingRow(null);
    setEditForm(null);
  };

  const toggleSelect = (id: string) => {
    setTransactions((prev) =>
      prev.map((t) =>
        t.id === id ? { ...t, isSelected: !t.isSelected } : t
      )
    );
  };

  const removeTransaction = (id: string) => {
    setTransactions((prev) => prev.filter((t) => t.id !== id));
  };

  // Helper to convert string/number to number
  const toNumber = (value: number | string | null | undefined): number | null => {
    if (value === null || value === undefined) return null;
    const num = typeof value === "string" ? parseFloat(value) : value;
    return isNaN(num) ? null : num;
  };

  const toNumberRequired = (value: number | string): number => {
    const num = typeof value === "string" ? parseFloat(value) : value;
    return isNaN(num) ? 0 : num;
  };

  const handleConfirm = () => {
    const selectedTransactions = transactions
      .filter((t) => t.isSelected)
      .map(({ id, isEditing, isSelected, ...rest }) => rest);

    onConfirm?.({
      transactions: selectedTransactions.map((t) => ({
        date: t.date,
        type: t.type,
        ticker: t.ticker,
        quantity: toNumber(t.quantity),
        price: toNumber(t.price),
        total: toNumber(t.total),
        fees: toNumber(t.fees),
        notes: t.notes,
      })),
      fixed_income: selectedFixedIncome.map((fi) => ({
        asset_name: fi.asset_name,
        asset_type: fi.asset_type,
        issuer: fi.issuer,
        quantity: toNumberRequired(fi.quantity),
        unit_price: toNumber(fi.unit_price),
        total_value: toNumberRequired(fi.total_value),
        indexer: fi.indexer,
        rate_percent: toNumber(fi.rate_percent),
        acquisition_date: fi.acquisition_date,
        maturity_date: fi.maturity_date,
        reference_date: fi.reference_date,
      })),
      stock_lending: selectedStockLending.map((sl) => ({
        date: sl.date,
        type: sl.type,
        ticker: sl.ticker,
        quantity: toNumberRequired(sl.quantity),
        rate_percent: toNumber(sl.rate_percent),
        total: toNumberRequired(sl.total),
        notes: sl.notes,
      })),
      cash_movements: selectedCashMovements.map((cm) => ({
        date: cm.date,
        type: cm.type,
        description: cm.description,
        ticker: cm.ticker,
        value: toNumberRequired(cm.value),
      })),
      investment_funds: selectedInvestmentFunds.map((fund) => ({
        fund_name: fund.fund_name,
        cnpj: fund.cnpj,
        quota_quantity: toNumberRequired(fund.quota_quantity),
        quota_price: toNumber(fund.quota_price),
        gross_balance: toNumberRequired(fund.gross_balance),
        ir_provision: toNumber(fund.ir_provision),
        net_balance: toNumber(fund.net_balance),
        performance_pct: toNumber(fund.performance_pct),
        reference_date: fund.reference_date || data.period?.end || new Date().toISOString().split("T")[0],
      })),
    });
  };

  const handleFixedIncomeChange = useCallback((items: ParsedFixedIncome[]) => {
    setSelectedFixedIncome(items);
  }, []);

  const handleStockLendingChange = useCallback((items: ParsedStockLending[]) => {
    setSelectedStockLending(items);
  }, []);

  const handleCashMovementsChange = useCallback((items: ParsedCashMovement[]) => {
    setSelectedCashMovements(items);
  }, []);

  const handleInvestmentFundsChange = useCallback((items: ParsedInvestmentFund[]) => {
    setSelectedInvestmentFunds(items);
  }, []);

  const getTransactionType = (type: string) => {
    return TRANSACTION_TYPES.find((t) => t.value === type) || TRANSACTION_TYPES[8];
  };

  const selectedTxnCount = transactions.filter((t) => t.isSelected).length;
  const hasTransactions = data.transactions.length > 0;
  const hasFixedIncome = (data.fixed_income_positions?.length || 0) > 0;
  const hasStockLending = (data.stock_lending?.length || 0) > 0;
  const hasCashMovements = (data.cash_movements?.length || 0) > 0;
  const hasInvestmentFunds = (data.investment_funds?.length || 0) > 0;

  const totalSelectedItems =
    selectedTxnCount +
    selectedFixedIncome.length +
    selectedStockLending.length +
    selectedCashMovements.length +
    selectedInvestmentFunds.length;

  const formatCurrency = (value: number | string | null | undefined) => {
    if (value === null || value === undefined) return "-";
    const num = typeof value === "string" ? parseFloat(value) : value;
    if (isNaN(num)) return "-";
    return new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: "BRL",
    }).format(num);
  };

  const formatNumber = (value: number | string | null | undefined) => {
    if (value === null || value === undefined) return "-";
    const num = typeof value === "string" ? parseFloat(value) : value;
    if (isNaN(num)) return "-";
    return new Intl.NumberFormat("pt-BR", {
      minimumFractionDigits: 0,
      maximumFractionDigits: 6,
    }).format(num);
  };

  // Determine which tabs to show
  const tabs = [];
  tabs.push({ id: "summary", label: "Resumo", count: null });
  if (hasTransactions) {
    tabs.push({ id: "transactions", label: "Transações", count: transactions.length });
  }
  if (hasInvestmentFunds) {
    tabs.push({ id: "investment-funds", label: "Fundos", count: data.investment_funds?.length });
  }
  if (hasFixedIncome) {
    tabs.push({ id: "fixed-income", label: "Renda Fixa", count: data.fixed_income_positions?.length });
  }
  if (hasStockLending) {
    tabs.push({ id: "stock-lending", label: "Aluguel", count: data.stock_lending?.length });
  }
  if (hasCashMovements) {
    tabs.push({ id: "cash-movements", label: "Movimentações", count: data.cash_movements?.length });
  }

  return (
    <div className="space-y-4">
      <Tabs defaultValue={hasTransactions ? "transactions" : "summary"} className="w-full">
        <TabsList className="w-full justify-start overflow-x-auto">
          {tabs.map((tab) => (
            <TabsTrigger key={tab.id} value={tab.id} className="min-w-fit">
              {tab.label}
              {tab.count !== null && (
                <Badge variant="secondary" className="ml-2">
                  {tab.count}
                </Badge>
              )}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="summary" className="mt-4">
          <DocumentSummary data={data} />
        </TabsContent>

        {hasTransactions && (
          <TabsContent value="transactions" className="mt-4">
            <Card variant="elevated">
              <CardHeader className="pb-4">
                <div className="flex items-center justify-between">
                  <CardTitle className="font-display text-xl flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-positive/10">
                      <CheckCircle2 className="h-4 w-4 text-positive" />
                    </div>
                    TRANSAÇÕES EXTRAÍDAS
                  </CardTitle>
                  <Badge variant="secondary">
                    {selectedTxnCount} de {transactions.length} selecionadas
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {transactions.length === 0 ? (
                  <div className="text-center py-12">
                    <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-warning/10 mx-auto mb-4">
                      <AlertCircle className="h-8 w-8 text-warning" />
                    </div>
                    <h3 className="font-display text-xl mb-2">Nenhuma transação encontrada</h3>
                    <p className="text-foreground-muted">
                      O documento não contém transações para importar.
                    </p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-[50px]">
                            <input
                              type="checkbox"
                              checked={selectedTxnCount === transactions.length}
                              onChange={(e) =>
                                setTransactions((prev) =>
                                  prev.map((t) => ({ ...t, isSelected: e.target.checked }))
                                )
                              }
                              className="rounded border-border-subtle"
                            />
                          </TableHead>
                          <TableHead>Data</TableHead>
                          <TableHead>Tipo</TableHead>
                          <TableHead>Ativo</TableHead>
                          <TableHead className="text-right">Quantidade</TableHead>
                          <TableHead className="text-right">Preço</TableHead>
                          <TableHead className="text-right">Total</TableHead>
                          <TableHead className="text-right">Taxas</TableHead>
                          <TableHead className="w-[100px]">Ações</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {transactions.map((txn) => {
                          const txnType = getTransactionType(txn.type);
                          const isEditing = editingRow === txn.id;

                          return (
                            <TableRow
                              key={txn.id}
                              className={!txn.isSelected ? "opacity-50" : ""}
                            >
                              <TableCell>
                                <input
                                  type="checkbox"
                                  checked={txn.isSelected}
                                  onChange={() => toggleSelect(txn.id)}
                                  className="rounded border-border-subtle"
                                />
                              </TableCell>

                              {isEditing && editForm ? (
                                <>
                                  <TableCell>
                                    <Input
                                      type="date"
                                      value={editForm.date}
                                      onChange={(e) =>
                                        setEditForm({ ...editForm, date: e.target.value })
                                      }
                                      className="h-8 w-32"
                                    />
                                  </TableCell>
                                  <TableCell>
                                    <Select
                                      value={editForm.type}
                                      onValueChange={(value) =>
                                        setEditForm({ ...editForm, type: value })
                                      }
                                    >
                                      <SelectTrigger className="h-8 w-32">
                                        <SelectValue />
                                      </SelectTrigger>
                                      <SelectContent>
                                        {TRANSACTION_TYPES.map((type) => (
                                          <SelectItem key={type.value} value={type.value}>
                                            {type.label}
                                          </SelectItem>
                                        ))}
                                      </SelectContent>
                                    </Select>
                                  </TableCell>
                                  <TableCell>
                                    <Input
                                      value={editForm.ticker}
                                      onChange={(e) =>
                                        setEditForm({ ...editForm, ticker: e.target.value })
                                      }
                                      className="h-8 w-24"
                                    />
                                  </TableCell>
                                  <TableCell>
                                    <Input
                                      type="number"
                                      value={editForm.quantity ?? ""}
                                      onChange={(e) =>
                                        setEditForm({
                                          ...editForm,
                                          quantity: e.target.value ? parseFloat(e.target.value) : null,
                                        })
                                      }
                                      className="h-8 w-24 text-right"
                                    />
                                  </TableCell>
                                  <TableCell>
                                    <Input
                                      type="number"
                                      step="0.01"
                                      value={editForm.price ?? ""}
                                      onChange={(e) =>
                                        setEditForm({
                                          ...editForm,
                                          price: e.target.value ? parseFloat(e.target.value) : null,
                                        })
                                      }
                                      className="h-8 w-24 text-right"
                                    />
                                  </TableCell>
                                  <TableCell>
                                    <Input
                                      type="number"
                                      step="0.01"
                                      value={editForm.total ?? ""}
                                      onChange={(e) =>
                                        setEditForm({
                                          ...editForm,
                                          total: e.target.value ? parseFloat(e.target.value) : null,
                                        })
                                      }
                                      className="h-8 w-28 text-right"
                                    />
                                  </TableCell>
                                  <TableCell>
                                    <Input
                                      type="number"
                                      step="0.01"
                                      value={editForm.fees ?? ""}
                                      onChange={(e) =>
                                        setEditForm({
                                          ...editForm,
                                          fees: e.target.value ? parseFloat(e.target.value) : null,
                                        })
                                      }
                                      className="h-8 w-24 text-right"
                                    />
                                  </TableCell>
                                  <TableCell>
                                    <div className="flex gap-1">
                                      <Button
                                        variant="ghost"
                                        size="icon"
                                        className="h-7 w-7 hover:bg-success/10 hover:text-success"
                                        onClick={saveEdit}
                                      >
                                        <Save className="h-4 w-4" />
                                      </Button>
                                      <Button
                                        variant="ghost"
                                        size="icon"
                                        className="h-7 w-7 hover:bg-destructive/10 hover:text-destructive"
                                        onClick={cancelEdit}
                                      >
                                        <X className="h-4 w-4" />
                                      </Button>
                                    </div>
                                  </TableCell>
                                </>
                              ) : (
                                <>
                                  <TableCell className="font-mono text-sm">
                                    {txn.date}
                                  </TableCell>
                                  <TableCell>
                                    <Badge
                                      variant={
                                        txnType.color === "success" ? "success" :
                                        txnType.color === "destructive" ? "destructive" :
                                        txnType.color === "info" ? "info" :
                                        txnType.color === "warning" ? "warning" :
                                        txnType.color === "muted" ? "muted" :
                                        "secondary"
                                      }
                                    >
                                      {txnType.label}
                                    </Badge>
                                  </TableCell>
                                  <TableCell className="font-mono font-semibold">
                                    {txn.ticker}
                                  </TableCell>
                                  <TableCell className="text-right font-mono">
                                    {formatNumber(txn.quantity)}
                                  </TableCell>
                                  <TableCell className="text-right font-mono">
                                    {formatCurrency(txn.price)}
                                  </TableCell>
                                  <TableCell className="text-right font-mono font-semibold">
                                    {formatCurrency(txn.total)}
                                  </TableCell>
                                  <TableCell className="text-right font-mono text-foreground-muted">
                                    {formatCurrency(txn.fees)}
                                  </TableCell>
                                  <TableCell>
                                    <div className="flex gap-1">
                                      <Button
                                        variant="ghost"
                                        size="icon"
                                        className="h-7 w-7 hover:bg-foreground/10 hover:text-foreground"
                                        onClick={() => startEdit(txn)}
                                      >
                                        <Pencil className="h-4 w-4" />
                                      </Button>
                                      <Button
                                        variant="ghost"
                                        size="icon"
                                        className="h-7 w-7 hover:bg-destructive/10 hover:text-destructive"
                                        onClick={() => removeTransaction(txn.id)}
                                      >
                                        <Trash2 className="h-4 w-4" />
                                      </Button>
                                    </div>
                                  </TableCell>
                                </>
                              )}
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        )}

        {hasInvestmentFunds && (
          <TabsContent value="investment-funds" className="mt-4">
            <InvestmentFundsTable
              items={data.investment_funds!}
              onSelectionChange={handleInvestmentFundsChange}
            />
          </TabsContent>
        )}

        {hasFixedIncome && (
          <TabsContent value="fixed-income" className="mt-4">
            <FixedIncomeTable
              items={data.fixed_income_positions!}
              onSelectionChange={handleFixedIncomeChange}
            />
          </TabsContent>
        )}

        {hasStockLending && (
          <TabsContent value="stock-lending" className="mt-4">
            <StockLendingTable
              items={data.stock_lending!}
              onSelectionChange={handleStockLendingChange}
            />
          </TabsContent>
        )}

        {hasCashMovements && (
          <TabsContent value="cash-movements" className="mt-4">
            <CashMovementsTable
              items={data.cash_movements!}
              onSelectionChange={handleCashMovementsChange}
            />
          </TabsContent>
        )}
      </Tabs>

      {/* Actions */}
      {totalSelectedItems > 0 && (
        <div className="flex justify-between items-center pt-4 border-t border-border-subtle">
          <div className="text-sm text-foreground-muted">
            {totalSelectedItems} itens selecionados para importação
          </div>
          <div className="flex gap-3">
            {onCancel && (
              <Button variant="outline" onClick={onCancel} disabled={isLoading}>
                Cancelar
              </Button>
            )}
            {onConfirm && (
              <Button
                onClick={handleConfirm}
                disabled={totalSelectedItems === 0 || isLoading}
              >
                {isLoading ? "Importando..." : `Importar ${totalSelectedItems} itens`}
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
