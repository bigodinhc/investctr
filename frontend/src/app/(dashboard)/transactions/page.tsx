"use client";

import { useState } from "react";
import {
  ArrowDownLeft,
  ArrowUpRight,
  Calendar,
  Filter,
  Pencil,
  RefreshCw,
  Trash2,
  TrendingUp,
  X,
} from "lucide-react";
import {
  useTransactions,
  useUpdateTransaction,
  useDeleteTransaction,
} from "@/hooks/use-transactions";
import { useAccounts } from "@/hooks/use-accounts";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "@/components/ui/use-toast";
import { formatCurrency, formatQuantity, formatDate } from "@/lib/format";
import type { TransactionWithAsset, TransactionType, TransactionUpdate } from "@/lib/api/types";

const TRANSACTION_TYPE_LABELS: Record<TransactionType, { label: string; color: string }> = {
  buy: { label: "Compra", color: "success" },
  sell: { label: "Venda", color: "destructive" },
  dividend: { label: "Dividendo", color: "info" },
  jcp: { label: "JCP", color: "info" },
  income: { label: "Rendimento", color: "info" },
  amortization: { label: "Amortização", color: "warning" },
  split: { label: "Desdobramento", color: "warning" },
  subscription: { label: "Subscrição", color: "secondary" },
  transfer_in: { label: "Transf. Entrada", color: "secondary" },
  transfer_out: { label: "Transf. Saída", color: "secondary" },
  rental: { label: "Aluguel", color: "secondary" },
  other: { label: "Outro", color: "secondary" },
};

export default function TransactionsPage() {
  const [filters, setFilters] = useState<{
    account_id?: string;
    type_filter?: TransactionType;
    start_date?: string;
    end_date?: string;
  }>({});
  const [isFiltersOpen, setIsFiltersOpen] = useState(false);
  const [editingTransaction, setEditingTransaction] = useState<TransactionWithAsset | null>(null);
  const [deletingTransaction, setDeletingTransaction] = useState<TransactionWithAsset | null>(null);
  const [editForm, setEditForm] = useState<TransactionUpdate>({});

  const { data, isLoading, error, refetch } = useTransactions({
    ...filters,
    limit: 100,
  });
  const { data: accountsData } = useAccounts();
  const updateTransaction = useUpdateTransaction();
  const deleteTransaction = useDeleteTransaction();

  const accounts = accountsData?.items || [];
  const transactions = data?.items || [];

  const handleEdit = (txn: TransactionWithAsset) => {
    setEditingTransaction(txn);
    setEditForm({
      type: txn.type,
      quantity: txn.quantity,
      price: txn.price,
      fees: txn.fees,
      notes: txn.notes || undefined,
    });
  };

  const handleSaveEdit = async () => {
    if (!editingTransaction) return;

    try {
      await updateTransaction.mutateAsync({
        id: editingTransaction.id,
        data: editForm,
      });
      setEditingTransaction(null);
      setEditForm({});
    } catch {
      // Error handled by hook
    }
  };

  const handleDelete = async () => {
    if (!deletingTransaction) return;

    try {
      await deleteTransaction.mutateAsync(deletingTransaction.id);
      setDeletingTransaction(null);
    } catch {
      // Error handled by hook
    }
  };

  const clearFilters = () => {
    setFilters({});
  };

  const hasFilters = Object.values(filters).some((v) => v);

  // Calculate stats
  const totalBuys = transactions.filter((t) => t.type === "buy").length;
  const totalSells = transactions.filter((t) => t.type === "sell").length;
  const totalDividends = transactions.filter((t) =>
    ["dividend", "jcp", "income"].includes(t.type)
  ).length;

  if (error) {
    return (
      <div className="space-y-8 animate-fade-in">
        <Card variant="elevated">
          <CardContent className="p-8">
            <div className="flex items-center gap-4 text-destructive">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-destructive/10">
                <X className="h-6 w-6" />
              </div>
              <div>
                <p className="font-semibold">Erro ao carregar transações</p>
                <p className="text-sm text-foreground-muted">{error.message}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="space-y-1">
          <h1 className="font-display text-3xl tracking-tight">
            <span className="text-foreground">Transações</span>
          </h1>
          <p className="text-foreground-muted">
            Visualize e gerencie todas as suas transações
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant={hasFilters ? "default" : "outline"}
            size="lg"
            onClick={() => setIsFiltersOpen(!isFiltersOpen)}
          >
            <Filter className="h-4 w-4 mr-2" />
            Filtros
            {hasFilters && (
              <Badge variant="muted" className="ml-2">
                {Object.values(filters).filter((v) => v).length}
              </Badge>
            )}
          </Button>
          <Button variant="outline" size="lg" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Atualizar
          </Button>
        </div>
      </div>

      {/* Filters Panel */}
      {isFiltersOpen && (
        <Card variant="elevated" className="animate-slide-down">
          <CardContent className="p-4">
            <div className="flex flex-wrap gap-4">
              <div className="flex-1 min-w-[200px]">
                <label className="text-sm font-medium mb-1 block">Conta</label>
                <Select
                  value={filters.account_id || "all"}
                  onValueChange={(value) =>
                    setFilters({ ...filters, account_id: value === "all" ? undefined : value })
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Todas as contas" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todas as contas</SelectItem>
                    {accounts.map((account) => (
                      <SelectItem key={account.id} value={account.id}>
                        {account.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex-1 min-w-[200px]">
                <label className="text-sm font-medium mb-1 block">Tipo</label>
                <Select
                  value={filters.type_filter || "all"}
                  onValueChange={(value) =>
                    setFilters({
                      ...filters,
                      type_filter: value === "all" ? undefined : (value as TransactionType),
                    })
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Todos os tipos" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todos os tipos</SelectItem>
                    {Object.entries(TRANSACTION_TYPE_LABELS).map(([value, { label }]) => (
                      <SelectItem key={value} value={value}>
                        {label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex-1 min-w-[150px]">
                <label className="text-sm font-medium mb-1 block">Data início</label>
                <Input
                  type="date"
                  value={filters.start_date || ""}
                  onChange={(e) =>
                    setFilters({ ...filters, start_date: e.target.value || undefined })
                  }
                />
              </div>
              <div className="flex-1 min-w-[150px]">
                <label className="text-sm font-medium mb-1 block">Data fim</label>
                <Input
                  type="date"
                  value={filters.end_date || ""}
                  onChange={(e) =>
                    setFilters({ ...filters, end_date: e.target.value || undefined })
                  }
                />
              </div>
              {hasFilters && (
                <div className="flex items-end">
                  <Button variant="ghost" onClick={clearFilters}>
                    <X className="h-4 w-4 mr-2" />
                    Limpar
                  </Button>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <Card variant="elevated" className="p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-background-surface">
              <TrendingUp className="h-5 w-5 text-foreground" />
            </div>
            <div>
              <p className="text-sm text-foreground-muted">Total</p>
              <p className="font-mono text-2xl font-semibold">
                {isLoading ? "-" : data?.total || 0}
              </p>
            </div>
          </div>
        </Card>
        <Card variant="elevated" className="p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-success/10">
              <ArrowDownLeft className="h-5 w-5 text-success" />
            </div>
            <div>
              <p className="text-sm text-foreground-muted">Compras</p>
              <p className="font-mono text-2xl font-semibold">{totalBuys}</p>
            </div>
          </div>
        </Card>
        <Card variant="elevated" className="p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-destructive/10">
              <ArrowUpRight className="h-5 w-5 text-destructive" />
            </div>
            <div>
              <p className="text-sm text-foreground-muted">Vendas</p>
              <p className="font-mono text-2xl font-semibold">{totalSells}</p>
            </div>
          </div>
        </Card>
        <Card variant="elevated" className="p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-info/10">
              <Calendar className="h-5 w-5 text-info" />
            </div>
            <div>
              <p className="text-sm text-foreground-muted">Proventos</p>
              <p className="font-mono text-2xl font-semibold">{totalDividends}</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Transactions Table */}
      <Card variant="elevated">
        <CardHeader className="pb-4">
          <CardTitle className="font-display text-xl flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-background-surface">
              <TrendingUp className="h-4 w-4 text-foreground" />
            </div>
            HISTÓRICO DE TRANSAÇÕES
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="flex items-center gap-4 p-4">
                  <div className="h-10 w-10 skeleton rounded-lg" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 w-32 skeleton rounded" />
                    <div className="h-3 w-24 skeleton rounded" />
                  </div>
                  <div className="h-4 w-20 skeleton rounded" />
                  <div className="h-4 w-24 skeleton rounded" />
                </div>
              ))}
            </div>
          ) : transactions.length === 0 ? (
            <div className="text-center py-16">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-background-surface mx-auto mb-6">
                <TrendingUp className="h-8 w-8 text-foreground" />
              </div>
              <h3 className="font-display text-xl mb-2">Nenhuma transação</h3>
              <p className="text-foreground-muted max-w-sm mx-auto">
                {hasFilters
                  ? "Nenhuma transação encontrada com os filtros aplicados."
                  : "Importe transações a partir de extratos ou notas de corretagem."}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Data</TableHead>
                    <TableHead>Tipo</TableHead>
                    <TableHead>Ativo</TableHead>
                    <TableHead className="text-right">Quantidade</TableHead>
                    <TableHead className="text-right">Preço</TableHead>
                    <TableHead className="text-right">Total</TableHead>
                    <TableHead className="text-right">Taxas</TableHead>
                    <TableHead className="w-[100px] text-right">Ações</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {transactions.map((txn, index) => {
                    const typeInfo = TRANSACTION_TYPE_LABELS[txn.type] || TRANSACTION_TYPE_LABELS.other;
                    return (
                      <TableRow
                        key={txn.id}
                        style={{ animationDelay: `${index * 30}ms` }}
                      >
                        <TableCell className="font-mono text-sm">
                          {formatDate(txn.executed_at, "medium")}
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant={
                              typeInfo.color === "success"
                                ? "success"
                                : typeInfo.color === "destructive"
                                ? "destructive"
                                : typeInfo.color === "info"
                                ? "info"
                                : typeInfo.color === "warning"
                                ? "warning"
                                : "secondary"
                            }
                          >
                            {typeInfo.label}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div>
                            <p className="font-mono font-semibold">{txn.ticker}</p>
                            <p className="text-xs text-foreground-muted truncate max-w-[150px]">
                              {txn.asset_name}
                            </p>
                          </div>
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {formatQuantity(txn.quantity)}
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {formatCurrency(txn.price)}
                        </TableCell>
                        <TableCell className="text-right font-mono font-semibold">
                          {formatCurrency(txn.total_value)}
                        </TableCell>
                        <TableCell className="text-right font-mono text-foreground-muted">
                          {formatCurrency(txn.fees)}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="icon"
                              aria-label={`Editar transação de ${txn.ticker}`}
                              className="h-8 w-8 hover:bg-background-surface hover:text-foreground"
                              onClick={() => handleEdit(txn)}
                            >
                              <Pencil className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              aria-label={`Excluir transação de ${txn.ticker}`}
                              className="h-8 w-8 hover:bg-destructive/10 hover:text-destructive"
                              onClick={() => setDeletingTransaction(txn)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Edit Transaction Dialog */}
      <Dialog
        open={!!editingTransaction}
        onOpenChange={() => {
          setEditingTransaction(null);
          setEditForm({});
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Editar Transação</DialogTitle>
            <DialogDescription>
              {editingTransaction && (
                <>
                  {editingTransaction.ticker} -{" "}
                  {formatDate(editingTransaction.executed_at, "medium")}
                </>
              )}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <label className="text-sm font-medium mb-1 block">Tipo</label>
              <Select
                value={editForm.type || editingTransaction?.type}
                onValueChange={(value) =>
                  setEditForm({ ...editForm, type: value as TransactionType })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(TRANSACTION_TYPE_LABELS).map(([value, { label }]) => (
                    <SelectItem key={value} value={value}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-1 block">Quantidade</label>
                <Input
                  type="number"
                  step="0.00000001"
                  value={editForm.quantity || ""}
                  onChange={(e) => setEditForm({ ...editForm, quantity: e.target.value })}
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">Preço</label>
                <Input
                  type="number"
                  step="0.01"
                  value={editForm.price || ""}
                  onChange={(e) => setEditForm({ ...editForm, price: e.target.value })}
                />
              </div>
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">Taxas</label>
              <Input
                type="number"
                step="0.01"
                value={editForm.fees || ""}
                onChange={(e) => setEditForm({ ...editForm, fees: e.target.value })}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">Notas</label>
              <Input
                value={editForm.notes || ""}
                onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })}
                placeholder="Observações opcionais"
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setEditingTransaction(null);
                setEditForm({});
              }}
            >
              Cancelar
            </Button>
            <Button
              onClick={handleSaveEdit}
              disabled={updateTransaction.isPending}
            >
              {updateTransaction.isPending ? "Salvando..." : "Salvar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={!!deletingTransaction}
        onOpenChange={() => setDeletingTransaction(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-destructive">Confirmar Exclusão</DialogTitle>
            <DialogDescription>
              Tem certeza que deseja excluir a transação de{" "}
              <strong className="text-foreground">
                {deletingTransaction?.ticker}
              </strong>{" "}
              em{" "}
              <strong className="text-foreground">
                {deletingTransaction && formatDate(deletingTransaction.executed_at, "medium")}
              </strong>
              ? Esta ação irá recalcular as posições automaticamente.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeletingTransaction(null)}>
              Cancelar
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteTransaction.isPending}
            >
              {deleteTransaction.isPending ? "Excluindo..." : "Excluir"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
