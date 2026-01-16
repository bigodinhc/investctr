"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { accountsApi } from "@/lib/api";
import type { AccountCreate, AccountUpdate, PaginationParams } from "@/lib/api";
import { toast } from "@/components/ui/use-toast";

const ACCOUNTS_KEY = ["accounts"];

/**
 * Hook to fetch all accounts
 */
export function useAccounts(params?: PaginationParams) {
  return useQuery({
    queryKey: [...ACCOUNTS_KEY, params],
    queryFn: () => accountsApi.list(params),
  });
}

/**
 * Hook to fetch a single account
 */
export function useAccount(id: string) {
  return useQuery({
    queryKey: [...ACCOUNTS_KEY, id],
    queryFn: () => accountsApi.get(id),
    enabled: !!id,
  });
}

/**
 * Hook to create a new account
 */
export function useCreateAccount() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: AccountCreate) => accountsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ACCOUNTS_KEY });
      toast({
        title: "Conta criada",
        description: "A conta foi criada com sucesso.",
        variant: "default",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Erro ao criar conta",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}

/**
 * Hook to update an account
 */
export function useUpdateAccount() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AccountUpdate }) =>
      accountsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ACCOUNTS_KEY });
      toast({
        title: "Conta atualizada",
        description: "A conta foi atualizada com sucesso.",
        variant: "default",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Erro ao atualizar conta",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}

/**
 * Hook to delete an account
 */
export function useDeleteAccount() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => accountsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ACCOUNTS_KEY });
      toast({
        title: "Conta excluída",
        description: "A conta foi excluída com sucesso.",
        variant: "default",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Erro ao excluir conta",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}
