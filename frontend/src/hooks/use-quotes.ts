/**
 * React Query hooks for quotes
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { syncQuotes } from "@/lib/api/quotes";
import { positionKeys } from "./use-positions";
import { toast } from "@/components/ui/use-toast";

export function useSyncQuotes() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: syncQuotes,
    onSuccess: (result) => {
      // Invalidate all position-related queries to refresh data with new prices
      queryClient.invalidateQueries({ queryKey: positionKeys.all });
      toast({
        title: "Cotacoes atualizadas",
        description: `${result.quotes_updated} cotacoes atualizadas para ${result.assets_synced} ativos.`,
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Erro ao atualizar cotacoes",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}
