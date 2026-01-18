"use client";

import { useState } from "react";
import { Plus, Pencil, Trash2, Building2, Wallet, Globe, AlertCircle } from "lucide-react";
import {
  useAccounts,
  useCreateAccount,
  useUpdateAccount,
  useDeleteAccount,
} from "@/hooks/use-accounts";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { Account, AccountCreate, AccountType, Currency } from "@/lib/api";

const ACCOUNT_TYPES: { value: AccountType; label: string; color: string }[] = [
  { value: "btg_personal", label: "BTG Pactual (PF)", color: "secondary" },
  { value: "btg_corporate", label: "BTG Pactual (PJ)", color: "info" },
  { value: "xp", label: "XP Investimentos", color: "success" },
  { value: "btg_cayman", label: "BTG Cayman", color: "warning" },
  { value: "other", label: "Outra", color: "default" },
];

const CURRENCIES: { value: Currency; label: string; flag: string }[] = [
  { value: "BRL", label: "Real Brasileiro", flag: "🇧🇷" },
  { value: "USD", label: "Dólar Americano", flag: "🇺🇸" },
  { value: "EUR", label: "Euro", flag: "🇪🇺" },
];

export default function AccountsPage() {
  const { data, isLoading, error } = useAccounts();
  const createAccount = useCreateAccount();
  const updateAccount = useUpdateAccount();
  const deleteAccount = useDeleteAccount();

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingAccount, setEditingAccount] = useState<Account | null>(null);
  const [deletingAccount, setDeletingAccount] = useState<Account | null>(null);

  // Form state
  const [formData, setFormData] = useState<AccountCreate>({
    name: "",
    type: "btg_personal",
    currency: "BRL",
  });

  const resetForm = () => {
    setFormData({ name: "", type: "btg_personal", currency: "BRL" });
  };

  const handleCreate = async () => {
    await createAccount.mutateAsync(formData);
    setIsCreateOpen(false);
    resetForm();
  };

  const handleUpdate = async () => {
    if (!editingAccount) return;
    await updateAccount.mutateAsync({
      id: editingAccount.id,
      data: formData,
    });
    setEditingAccount(null);
    resetForm();
  };

  const handleDelete = async () => {
    if (!deletingAccount) return;
    await deleteAccount.mutateAsync(deletingAccount.id);
    setDeletingAccount(null);
  };

  const openEdit = (account: Account) => {
    setFormData({
      name: account.name,
      type: account.type as AccountType,
      currency: account.currency as Currency,
    });
    setEditingAccount(account);
  };

  const getAccountType = (type: string) => {
    return ACCOUNT_TYPES.find((t) => t.value === type) || ACCOUNT_TYPES[4];
  };

  const getCurrency = (currency: string) => {
    return CURRENCIES.find((c) => c.value === currency) || CURRENCIES[0];
  };

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
                <p className="font-semibold">Erro ao carregar contas</p>
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
            <span className="text-foreground">Contas</span>
          </h1>
          <p className="text-foreground-muted">
            Gerencie suas contas de investimento
          </p>
        </div>
        <Button size="lg" onClick={() => setIsCreateOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Nova Conta
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card variant="elevated" className="p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-background-surface">
              <Wallet className="h-5 w-5 text-foreground" />
            </div>
            <div>
              <p className="text-sm text-foreground-muted">Total de Contas</p>
              <p className="font-mono text-2xl font-semibold">
                {isLoading ? "-" : data?.items.length || 0}
              </p>
            </div>
          </div>
        </Card>
        <Card variant="elevated" className="p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-info/10">
              <Building2 className="h-5 w-5 text-info" />
            </div>
            <div>
              <p className="text-sm text-foreground-muted">Corretoras</p>
              <p className="font-mono text-2xl font-semibold">
                {isLoading ? "-" : new Set(data?.items.map(a => a.type)).size || 0}
              </p>
            </div>
          </div>
        </Card>
        <Card variant="elevated" className="p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-success/10">
              <Globe className="h-5 w-5 text-success" />
            </div>
            <div>
              <p className="text-sm text-foreground-muted">Moedas</p>
              <p className="font-mono text-2xl font-semibold">
                {isLoading ? "-" : new Set(data?.items.map(a => a.currency)).size || 0}
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Accounts Table */}
      <Card variant="elevated">
        <CardHeader className="pb-4">
          <CardTitle className="font-display text-xl flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-background-surface">
              <Building2 className="h-4 w-4 text-foreground" />
            </div>
            MINHAS CONTAS
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-center gap-4 p-4">
                  <div className="h-10 w-10 skeleton rounded-lg" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 w-32 skeleton rounded" />
                    <div className="h-3 w-24 skeleton rounded" />
                  </div>
                  <div className="h-6 w-20 skeleton rounded-full" />
                </div>
              ))}
            </div>
          ) : !data?.items.length ? (
            <div className="text-center py-16">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-background-surface mx-auto mb-6">
                <Building2 className="h-8 w-8 text-foreground" />
              </div>
              <h3 className="font-display text-xl mb-2">Nenhuma conta cadastrada</h3>
              <p className="text-foreground-muted mb-6 max-w-sm mx-auto">
                Adicione sua primeira conta de investimentos para começar a organizar seu patrimônio.
              </p>
              <Button onClick={() => setIsCreateOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Criar Primeira Conta
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Conta</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Moeda</TableHead>
                  <TableHead className="w-[100px] text-right">Ações</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.items.map((account, index) => {
                  const accountType = getAccountType(account.type);
                  const currency = getCurrency(account.currency);
                  return (
                    <TableRow
                      key={account.id}
                      className="cursor-pointer"
                      style={{ animationDelay: `${index * 50}ms` }}
                    >
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-background-surface border border-border">
                            <span className="font-mono text-xs font-semibold text-foreground">
                              {account.name.slice(0, 2).toUpperCase()}
                            </span>
                          </div>
                          <div>
                            <p className="font-semibold">{account.name}</p>
                            <p className="text-xs text-foreground-dim">
                              ID: {account.id.slice(0, 8)}...
                            </p>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            accountType.color === "info" ? "info" :
                            accountType.color === "success" ? "success" :
                            accountType.color === "warning" ? "warning" :
                            "secondary"
                          }
                        >
                          {accountType.label}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <span className="text-lg">{currency.flag}</span>
                          <span className="font-mono text-sm">{account.currency}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            aria-label={`Editar conta ${account.name}`}
                            onClick={() => openEdit(account)}
                            className="h-8 w-8 hover:bg-background-surface hover:text-foreground"
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            aria-label={`Excluir conta ${account.name}`}
                            onClick={() => setDeletingAccount(account)}
                            className="h-8 w-8 hover:bg-destructive/10 hover:text-destructive"
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
          )}
        </CardContent>
      </Card>

      {/* Create Dialog */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nova Conta</DialogTitle>
            <DialogDescription>
              Adicione uma nova conta de investimentos para organizar seu patrimônio.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">Nome da Conta</Label>
              <Input
                id="name"
                placeholder="Ex: BTG Principal"
                value={formData.name}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="type">Corretora</Label>
              <Select
                value={formData.type}
                onValueChange={(value: AccountType) =>
                  setFormData({ ...formData, type: value })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ACCOUNT_TYPES.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="currency">Moeda Base</Label>
              <Select
                value={formData.currency}
                onValueChange={(value: Currency) =>
                  setFormData({ ...formData, currency: value })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CURRENCIES.map((currency) => (
                    <SelectItem key={currency.value} value={currency.value}>
                      <span className="flex items-center gap-2">
                        <span>{currency.flag}</span>
                        <span>{currency.value} - {currency.label}</span>
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateOpen(false)}>
              Cancelar
            </Button>
            <Button
              onClick={handleCreate}
              disabled={!formData.name || createAccount.isPending}
            >
              {createAccount.isPending ? "Criando..." : "Criar Conta"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={!!editingAccount} onOpenChange={() => setEditingAccount(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Editar Conta</DialogTitle>
            <DialogDescription>
              Atualize as informações da conta.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="edit-name">Nome da Conta</Label>
              <Input
                id="edit-name"
                value={formData.name}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-type">Corretora</Label>
              <Select
                value={formData.type}
                onValueChange={(value: AccountType) =>
                  setFormData({ ...formData, type: value })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ACCOUNT_TYPES.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-currency">Moeda Base</Label>
              <Select
                value={formData.currency}
                onValueChange={(value: Currency) =>
                  setFormData({ ...formData, currency: value })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CURRENCIES.map((currency) => (
                    <SelectItem key={currency.value} value={currency.value}>
                      <span className="flex items-center gap-2">
                        <span>{currency.flag}</span>
                        <span>{currency.value} - {currency.label}</span>
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditingAccount(null)}>
              Cancelar
            </Button>
            <Button
              onClick={handleUpdate}
              disabled={!formData.name || updateAccount.isPending}
            >
              {updateAccount.isPending ? "Salvando..." : "Salvar Alterações"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deletingAccount} onOpenChange={() => setDeletingAccount(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-destructive">Confirmar Exclusão</DialogTitle>
            <DialogDescription>
              Tem certeza que deseja excluir a conta <strong className="text-foreground">&quot;{deletingAccount?.name}&quot;</strong>?
              Esta ação não pode ser desfeita e todos os dados associados serão perdidos.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeletingAccount(null)}>
              Cancelar
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteAccount.isPending}
            >
              {deleteAccount.isPending ? "Excluindo..." : "Excluir Conta"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
