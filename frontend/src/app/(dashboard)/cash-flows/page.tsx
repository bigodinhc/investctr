"use client";

import { useState } from "react";
import {
  ArrowDownLeft,
  ArrowUpRight,
  Calendar,
  Filter,
  Pencil,
  Plus,
  RefreshCw,
  Trash2,
  Wallet,
  X,
  AlertCircle,
} from "lucide-react";
import {
  useCashFlows,
  useCreateCashFlow,
  useUpdateCashFlow,
  useDeleteCashFlow,
} from "@/hooks/use-cash-flows";
import { useAccounts } from "@/hooks/use-accounts";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
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
import { formatCurrency, formatDate } from "@/lib/format";
import type { CashFlow, CashFlowCreate, CashFlowType, CashFlowUpdate } from "@/lib/api/types";

const CASH_FLOW_TYPE_LABELS: Record<CashFlowType, { label: string; color: string }> = {
  deposit: { label: "Aporte", color: "success" },
  withdrawal: { label: "Saque", color: "destructive" },
};

export default function CashFlowsPage() {
  const [filters, setFilters] = useState<{ account_id?: string }>({});
  const [isFiltersOpen, setIsFiltersOpen] = useState(false);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingCashFlow, setEditingCashFlow] = useState<CashFlow | null>(null);
  const [deletingCashFlow, setDeletingCashFlow] = useState<CashFlow | null>(null);

  const { data, isLoading, error, refetch } = useCashFlows({
    ...filters,
    limit: 100,
  });
  const { data: accountsData } = useAccounts();
  const createCashFlow = useCreateCashFlow();
  const updateCashFlow = useUpdateCashFlow();
  const deleteCashFlow = useDeleteCashFlow();

  const accounts = accountsData?.items || [];
  const cashFlows = data?.items || [];

  // Form state
  const [formData, setFormData] = useState<CashFlowCreate>({
    account_id: "",
    type: "deposit",
    amount: "",
    executed_at: new Date().toISOString().slice(0, 16),
    notes: "",
  });

  const resetForm = () => {
    setFormData({
      account_id: accounts[0]?.id || "",
      type: "deposit",
      amount: "",
      executed_at: new Date().toISOString().slice(0, 16),
      notes: "",
    });
  };

  const handleCreate = async () => {
    if (!formData.account_id || !formData.amount) return;

    await createCashFlow.mutateAsync({
      ...formData,
      executed_at: new Date(formData.executed_at).toISOString(),
    });
    setIsCreateOpen(false);
    resetForm();
  };

  const handleEdit = (cf: CashFlow) => {
    setFormData({
      account_id: cf.account_id,
      type: cf.type,
      amount: cf.amount,
      executed_at: cf.executed_at.slice(0, 16),
      notes: cf.notes || "",
    });
    setEditingCashFlow(cf);
  };

  const handleUpdate = async () => {
    if (!editingCashFlow) return;

    const updateData: CashFlowUpdate = {
      type: formData.type,
      amount: formData.amount,
      executed_at: new Date(formData.executed_at).toISOString(),
      notes: formData.notes || undefined,
    };

    await updateCashFlow.mutateAsync({
      id: editingCashFlow.id,
      data: updateData,
    });
    setEditingCashFlow(null);
    resetForm();
  };

  const handleDelete = async () => {
    if (!deletingCashFlow) return;
    await deleteCashFlow.mutateAsync(deletingCashFlow.id);
    setDeletingCashFlow(null);
  };

  const clearFilters = () => {
    setFilters({});
  };

  const hasFilters = Object.values(filters).some((v) => v);

  const getAccountName = (accountId: string) => {
    const account = accounts.find((a) => a.id === accountId);
    return account?.name || "Conta desconhecida";
  };

  // Calculate stats
  const totalDeposits = cashFlows
    .filter((cf) => cf.type === "deposit")
    .reduce((sum, cf) => sum + parseFloat(cf.amount), 0);
  const totalWithdrawals = cashFlows
    .filter((cf) => cf.type === "withdrawal")
    .reduce((sum, cf) => sum + parseFloat(cf.amount), 0);
  const netFlow = totalDeposits - totalWithdrawals;

  if (error) {
    return (
      <div className="space-y-8 animate-fade-in">
        <Card variant="elevated">
          <CardContent className="p-8">
            <div className="flex items-center gap-4 text-destructive">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-destructive/10">
                <AlertCircle className="h-6 w-6" />
              </div>
              <div>
                <p className="font-semibold">Erro ao carregar movimentacoes</p>
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
            <span className="text-foreground">Aportes e Saques</span>
          </h1>
          <p className="text-foreground-muted">
            Gerencie seus aportes e retiradas de capital
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant={hasFilters ? "default" : "outline"}
            size="lg"
            onClick={() => setIsFiltersOpen(!isFiltersOpen)}
            aria-label="Abrir filtros"
          >
            <Filter className="h-4 w-4 sm:mr-2" />
            <span className="hidden sm:inline">Filtros</span>
            {hasFilters && (
              <Badge variant="muted" className="ml-1 sm:ml-2">
                {Object.values(filters).filter((v) => v).length}
              </Badge>
            )}
          </Button>
          <Button variant="outline" size="lg" onClick={() => refetch()} aria-label="Atualizar lista">
            <RefreshCw className="h-4 w-4 sm:mr-2" />
            <span className="hidden sm:inline">Atualizar</span>
          </Button>
          <Button size="lg" onClick={() => {
            resetForm();
            setIsCreateOpen(true);
          }} aria-label="Nova movimentacao">
            <Plus className="h-4 w-4 sm:mr-2" />
            <span className="hidden sm:inline">Nova</span>
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
              <Wallet className="h-5 w-5 text-foreground" />
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
              <p className="text-sm text-foreground-muted">Aportes</p>
              <p className="font-mono text-xl font-semibold text-success">
                {formatCurrency(totalDeposits.toString())}
              </p>
            </div>
          </div>
        </Card>
        <Card variant="elevated" className="p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-destructive/10">
              <ArrowUpRight className="h-5 w-5 text-destructive" />
            </div>
            <div>
              <p className="text-sm text-foreground-muted">Saques</p>
              <p className="font-mono text-xl font-semibold text-destructive">
                {formatCurrency(totalWithdrawals.toString())}
              </p>
            </div>
          </div>
        </Card>
        <Card variant="elevated" className="p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-info/10">
              <Calendar className="h-5 w-5 text-info" />
            </div>
            <div>
              <p className="text-sm text-foreground-muted">Saldo Liquido</p>
              <p className={`font-mono text-xl font-semibold ${netFlow >= 0 ? "text-success" : "text-destructive"}`}>
                {formatCurrency(netFlow.toString())}
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Cash Flows Table */}
      <Card variant="elevated">
        <CardHeader className="pb-4">
          <CardTitle className="font-display text-xl flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-background-surface">
              <Wallet className="h-4 w-4 text-foreground" />
            </div>
            HISTORICO DE MOVIMENTACOES
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
                  <div className="h-4 w-24 skeleton rounded" />
                </div>
              ))}
            </div>
          ) : cashFlows.length === 0 ? (
            <div className="text-center py-16">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-background-surface mx-auto mb-6">
                <Wallet className="h-8 w-8 text-foreground" />
              </div>
              <h3 className="font-display text-xl mb-2">Nenhuma movimentacao</h3>
              <p className="text-foreground-muted max-w-sm mx-auto mb-6">
                {hasFilters
                  ? "Nenhuma movimentacao encontrada com os filtros aplicados."
                  : "Registre seu primeiro aporte ou saque para comecar."}
              </p>
              <Button onClick={() => {
                resetForm();
                setIsCreateOpen(true);
              }}>
                <Plus className="h-4 w-4 mr-2" />
                Primeira Movimentacao
              </Button>
            </div>
          ) : (
            <>
              {/* Mobile Card View */}
              <div className="md:hidden space-y-3">
                {cashFlows.map((cf, index) => {
                  const typeInfo = CASH_FLOW_TYPE_LABELS[cf.type];
                  return (
                    <div
                      key={cf.id}
                      className="p-4 rounded-lg bg-background-surface border border-border-subtle"
                      style={{ animationDelay: `${index * 30}ms` }}
                    >
                      <div className="flex items-start justify-between gap-3 mb-3">
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-foreground">{getAccountName(cf.account_id)}</p>
                          <p className="text-xs text-foreground-muted">{formatDate(cf.executed_at, "medium")}</p>
                        </div>
                        <Badge
                          variant={typeInfo.color === "success" ? "success" : "destructive"}
                        >
                          <span className="flex items-center gap-1">
                            {cf.type === "deposit" ? (
                              <ArrowDownLeft className="h-3 w-3" />
                            ) : (
                              <ArrowUpRight className="h-3 w-3" />
                            )}
                            {typeInfo.label}
                          </span>
                        </Badge>
                      </div>
                      <div className="flex items-center justify-between">
                        <p className={`font-mono text-lg font-semibold ${cf.type === "deposit" ? "text-success" : "text-destructive"}`}>
                          {cf.type === "deposit" ? "+" : "-"}{formatCurrency(cf.amount)}
                        </p>
                        <div className="flex gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            aria-label={`Editar ${cf.type === "deposit" ? "aporte" : "saque"}`}
                            className="h-8 w-8"
                            onClick={() => handleEdit(cf)}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            aria-label={`Excluir ${cf.type === "deposit" ? "aporte" : "saque"}`}
                            className="h-8 w-8 hover:bg-destructive/10 hover:text-destructive"
                            onClick={() => setDeletingCashFlow(cf)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                      {cf.notes && (
                        <p className="text-xs text-foreground-muted mt-2 pt-2 border-t border-border-subtle truncate">
                          {cf.notes}
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Desktop Table View */}
              <div className="hidden md:block overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Data</TableHead>
                      <TableHead>Tipo</TableHead>
                      <TableHead>Conta</TableHead>
                      <TableHead className="text-right">Valor</TableHead>
                      <TableHead>Notas</TableHead>
                      <TableHead className="w-[100px] text-right">Acoes</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {cashFlows.map((cf, index) => {
                      const typeInfo = CASH_FLOW_TYPE_LABELS[cf.type];
                      return (
                        <TableRow
                          key={cf.id}
                          style={{ animationDelay: `${index * 30}ms` }}
                        >
                          <TableCell className="font-mono text-sm">
                            {formatDate(cf.executed_at, "medium")}
                          </TableCell>
                          <TableCell>
                            <Badge
                              variant={typeInfo.color === "success" ? "success" : "destructive"}
                            >
                              <span className="flex items-center gap-1">
                                {cf.type === "deposit" ? (
                                  <ArrowDownLeft className="h-3 w-3" />
                                ) : (
                                  <ArrowUpRight className="h-3 w-3" />
                                )}
                                {typeInfo.label}
                              </span>
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <p className="font-medium">{getAccountName(cf.account_id)}</p>
                          </TableCell>
                          <TableCell className={`text-right font-mono font-semibold ${cf.type === "deposit" ? "text-success" : "text-destructive"}`}>
                            {cf.type === "deposit" ? "+" : "-"}{formatCurrency(cf.amount)}
                          </TableCell>
                          <TableCell className="text-foreground-muted text-sm max-w-[200px] truncate">
                            {cf.notes || "-"}
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center justify-end gap-1">
                              <Button
                                variant="ghost"
                                size="icon"
                                aria-label={`Editar ${cf.type === "deposit" ? "aporte" : "saque"}`}
                                className="h-8 w-8 hover:bg-background-surface hover:text-foreground"
                                onClick={() => handleEdit(cf)}
                              >
                                <Pencil className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                aria-label={`Excluir ${cf.type === "deposit" ? "aporte" : "saque"}`}
                                className="h-8 w-8 hover:bg-destructive/10 hover:text-destructive"
                                onClick={() => setDeletingCashFlow(cf)}
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
            </>
          )}
        </CardContent>
      </Card>

      {/* Create Dialog */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nova Movimentacao</DialogTitle>
            <DialogDescription>
              Registre um novo aporte ou saque na sua conta de investimentos.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="account">Conta</Label>
              <Select
                value={formData.account_id}
                onValueChange={(value) =>
                  setFormData({ ...formData, account_id: value })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Selecione uma conta" />
                </SelectTrigger>
                <SelectContent>
                  {accounts.map((account) => (
                    <SelectItem key={account.id} value={account.id}>
                      {account.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="type">Tipo</Label>
              <Select
                value={formData.type}
                onValueChange={(value: CashFlowType) =>
                  setFormData({ ...formData, type: value })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="deposit">
                    <span className="flex items-center gap-2">
                      <ArrowDownLeft className="h-4 w-4 text-success" />
                      Aporte
                    </span>
                  </SelectItem>
                  <SelectItem value="withdrawal">
                    <span className="flex items-center gap-2">
                      <ArrowUpRight className="h-4 w-4 text-destructive" />
                      Saque
                    </span>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="amount">Valor (R$)</Label>
              <Input
                id="amount"
                type="number"
                step="0.01"
                min="0.01"
                placeholder="0.00"
                value={formData.amount}
                onChange={(e) =>
                  setFormData({ ...formData, amount: e.target.value })
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="executed_at">Data</Label>
              <Input
                id="executed_at"
                type="datetime-local"
                value={formData.executed_at}
                onChange={(e) =>
                  setFormData({ ...formData, executed_at: e.target.value })
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="notes">Notas (opcional)</Label>
              <Textarea
                id="notes"
                placeholder="Observacoes sobre esta movimentacao..."
                value={formData.notes || ""}
                onChange={(e) =>
                  setFormData({ ...formData, notes: e.target.value })
                }
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateOpen(false)}>
              Cancelar
            </Button>
            <Button
              onClick={handleCreate}
              disabled={!formData.account_id || !formData.amount || createCashFlow.isPending}
            >
              {createCashFlow.isPending ? "Criando..." : "Criar Movimentacao"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog
        open={!!editingCashFlow}
        onOpenChange={() => {
          setEditingCashFlow(null);
          resetForm();
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Editar Movimentacao</DialogTitle>
            <DialogDescription>
              Atualize as informacoes da movimentacao.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="edit-type">Tipo</Label>
              <Select
                value={formData.type}
                onValueChange={(value: CashFlowType) =>
                  setFormData({ ...formData, type: value })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="deposit">
                    <span className="flex items-center gap-2">
                      <ArrowDownLeft className="h-4 w-4 text-success" />
                      Aporte
                    </span>
                  </SelectItem>
                  <SelectItem value="withdrawal">
                    <span className="flex items-center gap-2">
                      <ArrowUpRight className="h-4 w-4 text-destructive" />
                      Saque
                    </span>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-amount">Valor (R$)</Label>
              <Input
                id="edit-amount"
                type="number"
                step="0.01"
                min="0.01"
                value={formData.amount}
                onChange={(e) =>
                  setFormData({ ...formData, amount: e.target.value })
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-executed_at">Data</Label>
              <Input
                id="edit-executed_at"
                type="datetime-local"
                value={formData.executed_at}
                onChange={(e) =>
                  setFormData({ ...formData, executed_at: e.target.value })
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-notes">Notas (opcional)</Label>
              <Textarea
                id="edit-notes"
                placeholder="Observacoes..."
                value={formData.notes || ""}
                onChange={(e) =>
                  setFormData({ ...formData, notes: e.target.value })
                }
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setEditingCashFlow(null);
                resetForm();
              }}
            >
              Cancelar
            </Button>
            <Button
              onClick={handleUpdate}
              disabled={updateCashFlow.isPending}
            >
              {updateCashFlow.isPending ? "Salvando..." : "Salvar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={!!deletingCashFlow}
        onOpenChange={() => setDeletingCashFlow(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-destructive">Confirmar Exclusao</DialogTitle>
            <DialogDescription>
              Tem certeza que deseja excluir esta movimentacao de{" "}
              <strong className="text-foreground">
                {deletingCashFlow && formatCurrency(deletingCashFlow.amount)}
              </strong>{" "}
              em{" "}
              <strong className="text-foreground">
                {deletingCashFlow && formatDate(deletingCashFlow.executed_at, "medium")}
              </strong>
              ? Esta acao nao pode ser desfeita.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeletingCashFlow(null)}>
              Cancelar
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteCashFlow.isPending}
            >
              {deleteCashFlow.isPending ? "Excluindo..." : "Excluir"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
