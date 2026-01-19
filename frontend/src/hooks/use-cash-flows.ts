"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { cashFlowsApi } from "@/lib/api";
import type { CashFlowCreate, CashFlowUpdate, CashFlowFilters } from "@/lib/api";
import { toast } from "@/components/ui/use-toast";

const CASH_FLOWS_KEY = ["cash-flows"];

/**
 * Hook to fetch all cash flows
 */
export function useCashFlows(params?: CashFlowFilters) {
  return useQuery({
    queryKey: [...CASH_FLOWS_KEY, params],
    queryFn: () => cashFlowsApi.list(params),
  });
}

/**
 * Hook to fetch a single cash flow
 */
export function useCashFlow(id: string) {
  return useQuery({
    queryKey: [...CASH_FLOWS_KEY, id],
    queryFn: () => cashFlowsApi.get(id),
    enabled: !!id,
  });
}

/**
 * Hook to create a new cash flow
 */
export function useCreateCashFlow() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CashFlowCreate) => cashFlowsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CASH_FLOWS_KEY });
      toast({
        title: "Movimentacao criada",
        description: "A movimentacao foi registrada com sucesso.",
        variant: "success",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Erro ao criar movimentacao",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}

/**
 * Hook to update a cash flow
 */
export function useUpdateCashFlow() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: CashFlowUpdate }) =>
      cashFlowsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CASH_FLOWS_KEY });
      toast({
        title: "Movimentacao atualizada",
        description: "A movimentacao foi atualizada com sucesso.",
        variant: "success",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Erro ao atualizar movimentacao",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}

/**
 * Hook to delete a cash flow
 */
export function useDeleteCashFlow() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => cashFlowsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CASH_FLOWS_KEY });
      toast({
        title: "Movimentacao excluida",
        description: "A movimentacao foi excluida com sucesso.",
        variant: "success",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Erro ao excluir movimentacao",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}
