"use client";

import { useState } from "react";
import { Pencil, Trash2, Save, X, AlertCircle, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ParsedTransaction, ParsedDocumentData } from "@/lib/api/types";

const TRANSACTION_TYPES = [
  { value: "buy", label: "Compra", color: "success" },
  { value: "sell", label: "Venda", color: "destructive" },
  { value: "dividend", label: "Dividendo", color: "info" },
  { value: "jcp", label: "JCP", color: "info" },
  { value: "split", label: "Desdobramento", color: "warning" },
  { value: "bonus", label: "Bonificação", color: "warning" },
  { value: "transfer_in", label: "Transferência (entrada)", color: "gold" },
  { value: "transfer_out", label: "Transferência (saída)", color: "gold" },
  { value: "other", label: "Outro", color: "default" },
] as const;

interface EditableTransaction extends ParsedTransaction {
  id: string;
  isEditing?: boolean;
  isSelected?: boolean;
}

interface ParsePreviewProps {
  data: ParsedDocumentData;
  onConfirm?: (transactions: ParsedTransaction[]) => void;
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

  const handleConfirm = () => {
    const selectedTransactions = transactions
      .filter((t) => t.isSelected)
      .map(({ id, isEditing, isSelected, ...rest }) => rest);
    onConfirm?.(selectedTransactions);
  };

  const getTransactionType = (type: string) => {
    return TRANSACTION_TYPES.find((t) => t.value === type) || TRANSACTION_TYPES[8];
  };

  const selectedCount = transactions.filter((t) => t.isSelected).length;

  const formatCurrency = (value: number | null) => {
    if (value === null) return "-";
    return new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: "BRL",
    }).format(value);
  };

  const formatNumber = (value: number | null) => {
    if (value === null) return "-";
    return new Intl.NumberFormat("pt-BR", {
      minimumFractionDigits: 0,
      maximumFractionDigits: 6,
    }).format(value);
  };

  return (
    <Card variant="elevated">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="font-display text-xl flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gold/10">
              <CheckCircle2 className="h-4 w-4 text-gold" />
            </div>
            TRANSAÇÕES EXTRAÍDAS
          </CardTitle>
          <Badge variant="gold">
            {selectedCount} de {transactions.length} selecionadas
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Summary Info */}
        {data.period && (
          <div className="flex flex-wrap gap-4 text-sm text-foreground-muted">
            <div>
              <span className="font-medium">Período:</span>{" "}
              {data.period.start} a {data.period.end}
            </div>
            {data.account_number && (
              <div>
                <span className="font-medium">Conta:</span> {data.account_number}
              </div>
            )}
            <div>
              <span className="font-medium">Tipo:</span> {data.document_type}
            </div>
          </div>
        )}

        {/* Transactions Table */}
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
                      checked={selectedCount === transactions.length}
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
                                txnType.color === "gold" ? "gold" :
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
                                className="h-7 w-7 hover:bg-gold/10 hover:text-gold"
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

        {/* Actions */}
        {transactions.length > 0 && (
          <div className="flex justify-end gap-3 pt-4 border-t border-border-subtle">
            {onCancel && (
              <Button variant="outline" onClick={onCancel} disabled={isLoading}>
                Cancelar
              </Button>
            )}
            {onConfirm && (
              <Button
                onClick={handleConfirm}
                disabled={selectedCount === 0 || isLoading}
              >
                {isLoading ? "Importando..." : `Importar ${selectedCount} transações`}
              </Button>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
