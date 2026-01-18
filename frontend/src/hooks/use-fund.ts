/**
 * React Query hooks for fund data
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getCurrentNAV,
  getFundShares,
  getLatestFundShare,
  getFundPerformance,
  calculateDailyShare,
} from "@/lib/api/fund";
import type { FundShareFilters } from "@/lib/api/types";
import { toast } from "@/components/ui/use-toast";

export const fundKeys = {
  all: ["fund"] as const,
  nav: (date?: string) => [...fundKeys.all, "nav", date] as const,
  shares: () => [...fundKeys.all, "shares"] as const,
  sharesList: (params?: FundShareFilters) =>
    [...fundKeys.shares(), "list", params] as const,
  latestShare: () => [...fundKeys.shares(), "latest"] as const,
  performance: () => [...fundKeys.all, "performance"] as const,
};

export function useNAV(targetDate?: string) {
  return useQuery({
    queryKey: fundKeys.nav(targetDate),
    queryFn: () => getCurrentNAV(targetDate),
  });
}

export function useFundShares(params?: FundShareFilters) {
  return useQuery({
    queryKey: fundKeys.sharesList(params),
    queryFn: () => getFundShares(params),
  });
}

export function useLatestFundShare() {
  return useQuery({
    queryKey: fundKeys.latestShare(),
    queryFn: getLatestFundShare,
    retry: false, // Don't retry if no data exists
  });
}

export function useFundPerformance() {
  return useQuery({
    queryKey: fundKeys.performance(),
    queryFn: getFundPerformance,
    retry: false, // Don't retry if no data exists
  });
}

export function useCalculateDailyShare() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: calculateDailyShare,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: fundKeys.all });
      toast({
        title: "Sucesso",
        description: "Cota diária calculada com sucesso",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Erro",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}
