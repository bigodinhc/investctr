"use client";

import { useState } from "react";
import { FileText, Upload, Eye, Trash2, Play, AlertCircle, RefreshCw, Check } from "lucide-react";
import { useDocuments, useDocument, useParseResult, useParseDocument, useDeleteDocument } from "@/hooks/use-documents";
import { useAccounts } from "@/hooks/use-accounts";
import { useCommitDocument } from "@/hooks/use-transactions";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { UploadZone, ParsePreview, DocumentStatusBadge } from "@/components/documents";
import { toast } from "@/components/ui/use-toast";
import { formatFileSize, formatDate } from "@/lib/format";
import type { Document, ParsedTransaction } from "@/lib/api/types";

// Progress stage indicator component
function ProgressStage({
  label,
  isActive,
  isComplete,
}: {
  label: string;
  isActive: boolean;
  isComplete: boolean;
}) {
  return (
    <div className="flex items-center gap-3">
      <div
        className={`flex h-8 w-8 items-center justify-center rounded-full border-2 transition-all ${
          isComplete
            ? "border-success bg-success text-success-foreground"
            : isActive
              ? "border-foreground bg-transparent animate-pulse"
              : "border-border bg-background-surface"
        }`}
      >
        {isComplete ? (
          <Check className="h-4 w-4" />
        ) : isActive ? (
          <div className="h-2 w-2 rounded-full bg-foreground animate-pulse" />
        ) : null}
      </div>
      <span
        className={`text-sm ${
          isComplete
            ? "text-success"
            : isActive
              ? "text-foreground font-medium"
              : "text-foreground-dim"
        }`}
      >
        {label}
      </span>
    </div>
  );
}

const DOCUMENT_TYPE_LABELS: Record<string, string> = {
  statement: "Extrato",
  trade_note: "Nota de Corretagem",
  income_report: "Informe de Rendimentos",
  other: "Outro",
};

export default function DocumentsPage() {
  const { data, isLoading, error, refetch } = useDocuments();
  const { data: accountsData } = useAccounts();
  const parseDocument = useParseDocument();
  const deleteDocument = useDeleteDocument();
  const commitDocument = useCommitDocument();

  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);
  const [deletingDocument, setDeletingDocument] = useState<Document | null>(null);
  const [selectedAccountId, setSelectedAccountId] = useState<string>("");

  // Fetch selected document details
  const { data: selectedDocument } = useDocument(selectedDocumentId || "");
  const { data: parseResult, isLoading: isParseLoading } = useParseResult(
    selectedDocumentId || "",
    !!selectedDocumentId && selectedDocument?.parsing_status !== "pending"
  );

  // Set default account when accounts load
  const accounts = accountsData?.items || [];

  const handleUploadSuccess = (documentId: string) => {
    toast({
      title: "Upload concluído",
      description: "O documento foi enviado com sucesso.",
    });
    refetch();
  };

  const handleParse = async (documentId: string) => {
    try {
      await parseDocument.mutateAsync({ documentId, asyncMode: true });
      toast({
        title: "Processamento iniciado",
        description: "O documento está sendo analisado pelo Claude.",
      });
      setSelectedDocumentId(documentId);
    } catch (error) {
      toast({
        title: "Erro ao processar",
        description: (error as Error).message,
        variant: "destructive",
      });
    }
  };

  const handleDelete = async () => {
    if (!deletingDocument) return;
    try {
      await deleteDocument.mutateAsync(deletingDocument.id);
      toast({
        title: "Documento excluído",
        description: "O documento foi removido com sucesso.",
      });
      setDeletingDocument(null);
    } catch (error) {
      toast({
        title: "Erro ao excluir",
        description: (error as Error).message,
        variant: "destructive",
      });
    }
  };

  const handleConfirmTransactions = async (transactions: ParsedTransaction[]) => {
    if (!selectedDocumentId) return;

    if (!selectedAccountId) {
      toast({
        title: "Selecione uma conta",
        description: "É necessário selecionar uma conta para importar as transações.",
        variant: "destructive",
      });
      return;
    }

    try {
      await commitDocument.mutateAsync({
        documentId: selectedDocumentId,
        data: {
          account_id: selectedAccountId,
          transactions: transactions.map((t) => ({
            date: t.date,
            type: t.type,
            ticker: t.ticker,
            quantity: t.quantity,
            price: t.price,
            total: t.total,
            fees: t.fees,
            notes: t.notes,
          })),
        },
      });
      setSelectedDocumentId(null);
      setSelectedAccountId("");
    } catch {
      // Error is handled by the mutation hook
    }
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
                <p className="font-semibold">Erro ao carregar documentos</p>
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
            <span className="text-foreground">Documentos</span>
          </h1>
          <p className="text-foreground-muted">
            Faça upload de extratos e notas de corretagem para importar transações
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="lg" onClick={() => refetch()} aria-label="Atualizar lista">
            <RefreshCw className="h-4 w-4 sm:mr-2" />
            <span className="hidden sm:inline">Atualizar</span>
          </Button>
          <Button size="lg" onClick={() => setIsUploadOpen(true)} aria-label="Novo upload de documento">
            <Upload className="h-4 w-4 sm:mr-2" />
            <span className="hidden sm:inline">Upload</span>
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <Card variant="elevated" className="p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-background-surface">
              <FileText className="h-5 w-5 text-foreground" />
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
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-warning/10">
              <FileText className="h-5 w-5 text-warning" />
            </div>
            <div>
              <p className="text-sm text-foreground-muted">Pendentes</p>
              <p className="font-mono text-2xl font-semibold">
                {isLoading ? "-" : data?.items.filter(d => d.parsing_status === "pending").length || 0}
              </p>
            </div>
          </div>
        </Card>
        <Card variant="elevated" className="p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-success/10">
              <FileText className="h-5 w-5 text-success" />
            </div>
            <div>
              <p className="text-sm text-foreground-muted">Processados</p>
              <p className="font-mono text-2xl font-semibold">
                {isLoading ? "-" : data?.items.filter(d => d.parsing_status === "completed").length || 0}
              </p>
            </div>
          </div>
        </Card>
        <Card variant="elevated" className="p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-destructive/10">
              <FileText className="h-5 w-5 text-destructive" />
            </div>
            <div>
              <p className="text-sm text-foreground-muted">Erros</p>
              <p className="font-mono text-2xl font-semibold">
                {isLoading ? "-" : data?.items.filter(d => d.parsing_status === "failed").length || 0}
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Documents Table */}
      <Card variant="elevated">
        <CardHeader className="pb-4">
          <CardTitle className="font-display text-xl flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-background-surface">
              <FileText className="h-4 w-4 text-foreground" />
            </div>
            MEUS DOCUMENTOS
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-center gap-4 p-4">
                  <div className="h-10 w-10 skeleton rounded-lg" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 w-48 skeleton rounded" />
                    <div className="h-3 w-32 skeleton rounded" />
                  </div>
                  <div className="h-6 w-24 skeleton rounded-full" />
                </div>
              ))}
            </div>
          ) : !data?.items.length ? (
            <div className="text-center py-16">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-background-surface mx-auto mb-6">
                <FileText className="h-8 w-8 text-foreground" />
              </div>
              <h3 className="font-display text-xl mb-2">Nenhum documento</h3>
              <p className="text-foreground-muted mb-6 max-w-sm mx-auto">
                Faça upload do seu primeiro extrato ou nota de corretagem para começar a importar transações.
              </p>
              <Button onClick={() => setIsUploadOpen(true)}>
                <Upload className="h-4 w-4 mr-2" />
                Fazer Upload
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Documento</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Tamanho</TableHead>
                  <TableHead>Data</TableHead>
                  <TableHead className="w-[140px] text-right">Ações</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.items.map((doc, index) => (
                  <TableRow
                    key={doc.id}
                    style={{ animationDelay: `${index * 50}ms` }}
                  >
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-background-surface border border-border">
                          <FileText className="h-5 w-5 text-foreground" />
                        </div>
                        <div>
                          <p className="font-medium truncate max-w-[200px]">
                            {doc.file_name}
                          </p>
                          <p className="text-xs text-foreground-dim">
                            ID: {doc.id.slice(0, 8)}...
                          </p>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary">
                        {DOCUMENT_TYPE_LABELS[doc.doc_type] || doc.doc_type}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <DocumentStatusBadge status={doc.parsing_status} />
                    </TableCell>
                    <TableCell className="font-mono text-sm">
                      {formatFileSize(doc.file_size)}
                    </TableCell>
                    <TableCell className="text-sm text-foreground-muted">
                      {formatDate(doc.created_at, "datetime")}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center justify-end gap-1">
                        {doc.parsing_status === "pending" && (
                          <Button
                            variant="ghost"
                            size="icon"
                            aria-label={`Processar documento ${doc.file_name}`}
                            className="h-8 w-8 hover:bg-success/10 hover:text-success"
                            onClick={() => handleParse(doc.id)}
                            disabled={parseDocument.isPending}
                          >
                            <Play className="h-4 w-4" />
                          </Button>
                        )}
                        {(doc.parsing_status === "completed" || doc.parsing_status === "processing") && (
                          <Button
                            variant="ghost"
                            size="icon"
                            aria-label={`Ver resultado do documento ${doc.file_name}`}
                            className="h-8 w-8 hover:bg-background-surface hover:text-foreground"
                            onClick={() => setSelectedDocumentId(doc.id)}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="icon"
                          aria-label={`Excluir documento ${doc.file_name}`}
                          className="h-8 w-8 hover:bg-destructive/10 hover:text-destructive"
                          onClick={() => setDeletingDocument(doc)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Upload Dialog */}
      <Dialog open={isUploadOpen} onOpenChange={setIsUploadOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Upload de Documentos</DialogTitle>
            <DialogDescription>
              Faça upload de extratos ou notas de corretagem em formato PDF.
              O Claude irá extrair as transações automaticamente.
            </DialogDescription>
          </DialogHeader>
          <UploadZone
            onUploadSuccess={handleUploadSuccess}
            onUploadError={(error) =>
              toast({
                title: "Erro no upload",
                description: error.message,
                variant: "destructive",
              })
            }
          />
        </DialogContent>
      </Dialog>

      {/* Parse Result Dialog */}
      <Dialog
        open={!!selectedDocumentId}
        onOpenChange={() => setSelectedDocumentId(null)}
      >
        <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Resultado do Processamento</DialogTitle>
            <DialogDescription>
              Revise as transações extraídas antes de importar.
              Você pode editar ou remover transações incorretas.
            </DialogDescription>
          </DialogHeader>

          {isParseLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <div className="h-12 w-12 rounded-full border-4 border-foreground-muted/30 border-t-foreground animate-spin mx-auto mb-4" />
                <p className="text-foreground-muted">Processando documento...</p>
              </div>
            </div>
          ) : parseResult?.status === "processing" ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-center w-full max-w-md">
                {/* Progress Stages */}
                <div className="flex flex-col gap-3 mb-6">
                  <ProgressStage
                    label="Baixando documento..."
                    isActive={parseResult.stage === "downloading"}
                    isComplete={parseResult.stage === "processing_ai" || parseResult.stage === "validating"}
                  />
                  <ProgressStage
                    label="Processando com IA..."
                    isActive={parseResult.stage === "processing_ai"}
                    isComplete={parseResult.stage === "validating"}
                  />
                  <ProgressStage
                    label="Validando dados..."
                    isActive={parseResult.stage === "validating"}
                    isComplete={false}
                  />
                </div>
                <p className="text-sm text-foreground-dim">
                  Isso pode levar alguns minutos para documentos grandes.
                </p>
              </div>
            </div>
          ) : parseResult?.status === "failed" ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-destructive/10 mx-auto mb-4">
                  <AlertCircle className="h-8 w-8 text-destructive" />
                </div>
                <h3 className="font-display text-xl mb-2">Erro no processamento</h3>
                <p className="text-foreground-muted max-w-md">
                  {parseResult.error || "Ocorreu um erro ao processar o documento."}
                </p>
              </div>
            </div>
          ) : parseResult?.data ? (
            <div className="space-y-4">
              {/* Account Selector */}
              <div className="p-4 bg-background-elevated rounded-lg border border-border-subtle">
                <label className="text-sm font-medium mb-2 block">
                  Selecione a conta para importar as transações:
                </label>
                <Select
                  value={selectedAccountId}
                  onValueChange={setSelectedAccountId}
                >
                  <SelectTrigger className="w-full max-w-sm">
                    <SelectValue placeholder="Selecione uma conta..." />
                  </SelectTrigger>
                  <SelectContent>
                    {accounts.map((account) => (
                      <SelectItem key={account.id} value={account.id}>
                        {account.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {accounts.length === 0 && (
                  <p className="text-sm text-warning mt-2">
                    Nenhuma conta encontrada. Crie uma conta primeiro.
                  </p>
                )}
              </div>

              <ParsePreview
                data={parseResult.data}
                onConfirm={handleConfirmTransactions}
                onCancel={() => {
                  setSelectedDocumentId(null);
                  setSelectedAccountId("");
                }}
                isLoading={commitDocument.isPending}
              />
            </div>
          ) : null}
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deletingDocument} onOpenChange={() => setDeletingDocument(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-destructive">Confirmar Exclusão</DialogTitle>
            <DialogDescription>
              Tem certeza que deseja excluir o documento{" "}
              <strong className="text-foreground">&quot;{deletingDocument?.file_name}&quot;</strong>?
              Esta ação não pode ser desfeita.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeletingDocument(null)}>
              Cancelar
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteDocument.isPending}
            >
              {deleteDocument.isPending ? "Excluindo..." : "Excluir"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
