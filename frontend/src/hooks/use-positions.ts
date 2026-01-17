/**
 * React Query hooks for positions
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getPositions,
  getPosition,
  getConsolidatedPositions,
  getPortfolioSummary,
  recalculatePositions,
} from "@/lib/api/positions";
import type { PositionFilters, AssetType } from "@/lib/api/types";
import { toast } from "@/components/ui/use-toast";

export const positionKeys = {
  all: ["positions"] as const,
  lists: () => [...positionKeys.all, "list"] as const,
  list: (params?: PositionFilters) => [...positionKeys.lists(), params] as const,
  details: () => [...positionKeys.all, "detail"] as const,
  detail: (id: string) => [...positionKeys.details(), id] as const,
  consolidated: (assetType?: AssetType) =>
    [...positionKeys.all, "consolidated", assetType] as const,
  summary: (accountId?: string) =>
    [...positionKeys.all, "summary", accountId] as const,
};

export function usePositions(params?: PositionFilters) {
  return useQuery({
    queryKey: positionKeys.list(params),
    queryFn: () => getPositions(params),
  });
}

export function usePosition(id: string) {
  return useQuery({
    queryKey: positionKeys.detail(id),
    queryFn: () => getPosition(id),
    enabled: !!id,
  });
}

export function useConsolidatedPositions(assetType?: AssetType) {
  return useQuery({
    queryKey: positionKeys.consolidated(assetType),
    queryFn: () => getConsolidatedPositions(assetType),
  });
}

export function usePortfolioSummary(accountId?: string) {
  return useQuery({
    queryKey: positionKeys.summary(accountId),
    queryFn: () => getPortfolioSummary(accountId),
  });
}

export function useRecalculatePositions() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: recalculatePositions,
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: positionKeys.all });
      toast({
        title: "Posições recalculadas",
        description: result.message,
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Erro ao recalcular posições",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}
