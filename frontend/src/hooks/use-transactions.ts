/**
 * React Query hooks for transactions
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getTransactions,
  getTransaction,
  createTransaction,
  updateTransaction,
  deleteTransaction,
} from "@/lib/api/transactions";
import type {
  TransactionFilters,
  TransactionCreate,
  TransactionUpdate,
} from "@/lib/api/types";
import { toast } from "@/components/ui/use-toast";
import { positionKeys } from "./use-positions";

export const transactionKeys = {
  all: ["transactions"] as const,
  lists: () => [...transactionKeys.all, "list"] as const,
  list: (params?: TransactionFilters) => [...transactionKeys.lists(), params] as const,
  details: () => [...transactionKeys.all, "detail"] as const,
  detail: (id: string) => [...transactionKeys.details(), id] as const,
};

export function useTransactions(params?: TransactionFilters) {
  return useQuery({
    queryKey: transactionKeys.list(params),
    queryFn: () => getTransactions(params),
  });
}

export function useTransaction(id: string) {
  return useQuery({
    queryKey: transactionKeys.detail(id),
    queryFn: () => getTransaction(id),
    enabled: !!id,
  });
}

export function useCreateTransaction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: TransactionCreate) => createTransaction(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: transactionKeys.lists() });
      queryClient.invalidateQueries({ queryKey: positionKeys.all });
      toast({
        title: "Transacao criada",
        description: "A transacao foi criada com sucesso.",
        variant: "success",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Erro ao criar transação",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}

export function useUpdateTransaction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: TransactionUpdate }) =>
      updateTransaction(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: transactionKeys.lists() });
      queryClient.invalidateQueries({
        queryKey: transactionKeys.detail(variables.id),
      });
      queryClient.invalidateQueries({ queryKey: positionKeys.all });
      toast({
        title: "Transacao atualizada",
        description: "A transacao foi atualizada com sucesso.",
        variant: "success",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Erro ao atualizar transação",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}

export function useDeleteTransaction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteTransaction,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: transactionKeys.lists() });
      queryClient.invalidateQueries({ queryKey: positionKeys.all });
      toast({
        title: "Transacao excluida",
        description: "A transacao foi removida com sucesso.",
        variant: "success",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Erro ao excluir transação",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}
