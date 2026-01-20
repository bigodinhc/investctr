/**
 * React Query hooks for documents
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getDocuments,
  getDocument,
  uploadDocument,
  parseDocument,
  getParseResult,
  deleteDocument,
  commitDocument,
} from "@/lib/api/documents";
import { toast } from "@/components/ui/use-toast";
import type { DocumentType, PaginationParams, CommitDocumentRequest } from "@/lib/api/types";

export const documentKeys = {
  all: ["documents"] as const,
  lists: () => [...documentKeys.all, "list"] as const,
  list: (params?: PaginationParams) => [...documentKeys.lists(), params] as const,
  details: () => [...documentKeys.all, "detail"] as const,
  detail: (id: string) => [...documentKeys.details(), id] as const,
  parseResult: (id: string) => [...documentKeys.all, "parse", id] as const,
};

export function useDocuments(params?: PaginationParams) {
  return useQuery({
    queryKey: documentKeys.list(params),
    queryFn: () => getDocuments(params),
  });
}

export function useDocument(id: string) {
  return useQuery({
    queryKey: documentKeys.detail(id),
    queryFn: () => getDocument(id),
    enabled: !!id,
  });
}

export function useParseResult(id: string, enabled: boolean = true) {
  return useQuery({
    queryKey: documentKeys.parseResult(id),
    queryFn: () => getParseResult(id),
    enabled: !!id && enabled,
    refetchInterval: (query) => {
      const data = query.state.data;
      // Keep polling if status is pending or processing
      if (data?.status === "pending" || data?.status === "processing") {
        return 3000; // Poll every 3 seconds
      }
      return false; // Stop polling when completed or failed
    },
  });
}

export function useUploadDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      file,
      docType,
      accountId,
    }: {
      file: File;
      docType: DocumentType;
      accountId?: string;
    }) => uploadDocument(file, docType, accountId),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: documentKeys.lists() });
      toast({
        title: "Upload concluido",
        description: `Documento "${result.file_name}" enviado com sucesso.`,
        variant: "success",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Erro no upload",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}

export function useParseDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      documentId,
      asyncMode = true,
    }: {
      documentId: string;
      asyncMode?: boolean;
    }) => parseDocument(documentId, asyncMode),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: documentKeys.detail(variables.documentId),
      });
      queryClient.invalidateQueries({
        queryKey: documentKeys.parseResult(variables.documentId),
      });
      toast({
        title: "Processamento iniciado",
        description: "O documento esta sendo processado.",
        variant: "info",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Erro ao processar",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: documentKeys.lists() });
      toast({
        title: "Documento excluido",
        description: "O documento foi removido com sucesso.",
        variant: "success",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Erro ao excluir",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}

export function useCommitDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      documentId,
      data,
    }: {
      documentId: string;
      data: CommitDocumentRequest;
    }) => commitDocument(documentId, data),
    onSuccess: (result, variables) => {
      queryClient.invalidateQueries({ queryKey: documentKeys.lists() });
      queryClient.invalidateQueries({
        queryKey: documentKeys.detail(variables.documentId),
      });
      // Invalidate positions and transactions queries
      queryClient.invalidateQueries({ queryKey: ["positions"] });
      queryClient.invalidateQueries({ queryKey: ["transactions"] });

      const totalCreated =
        result.transactions_created +
        result.fixed_income_created +
        result.cash_flows_created;

      toast({
        title: "Dados importados",
        description: `${totalCreated} registros criados com sucesso.${
          result.errors.length > 0
            ? ` ${result.errors.length} erros encontrados.`
            : ""
        }`,
        variant: result.errors.length > 0 ? "warning" : "success",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Erro ao importar",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}
