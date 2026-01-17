"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, FileText, X, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useUploadDocument } from "@/hooks/use-documents";
import { useAccounts } from "@/hooks/use-accounts";
import type { DocumentType } from "@/lib/api/types";

const DOCUMENT_TYPES: { value: DocumentType; label: string; description: string }[] = [
  { value: "statement", label: "Extrato", description: "Extrato mensal de conta" },
  { value: "trade_note", label: "Nota de Corretagem", description: "Nota de operações" },
  { value: "income_report", label: "Informe de Rendimentos", description: "Para IR" },
  { value: "other", label: "Outro", description: "Documento genérico" },
];

interface UploadZoneProps {
  onUploadSuccess?: (documentId: string) => void;
  onUploadError?: (error: Error) => void;
  className?: string;
}

interface UploadingFile {
  file: File;
  docType: DocumentType;
  accountId?: string;
  status: "pending" | "uploading" | "success" | "error";
  error?: string;
  documentId?: string;
}

export function UploadZone({ onUploadSuccess, onUploadError, className }: UploadZoneProps) {
  const [files, setFiles] = useState<UploadingFile[]>([]);
  const [selectedDocType, setSelectedDocType] = useState<DocumentType>("statement");
  const [selectedAccountId, setSelectedAccountId] = useState<string | undefined>();

  const uploadDocument = useUploadDocument();
  const { data: accountsData } = useAccounts();

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles: UploadingFile[] = acceptedFiles.map((file) => ({
      file,
      docType: selectedDocType,
      accountId: selectedAccountId,
      status: "pending" as const,
    }));
    setFiles((prev) => [...prev, ...newFiles]);
  }, [selectedDocType, selectedAccountId]);

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
    },
    maxSize: 20 * 1024 * 1024, // 20MB
    multiple: true,
  });

  const uploadFile = async (index: number) => {
    const fileData = files[index];
    if (fileData.status !== "pending") return;

    setFiles((prev) =>
      prev.map((f, i) => (i === index ? { ...f, status: "uploading" } : f))
    );

    try {
      const result = await uploadDocument.mutateAsync({
        file: fileData.file,
        docType: fileData.docType,
        accountId: fileData.accountId,
      });

      setFiles((prev) =>
        prev.map((f, i) =>
          i === index ? { ...f, status: "success", documentId: result.id } : f
        )
      );

      onUploadSuccess?.(result.id);
    } catch (error) {
      const err = error as Error;
      setFiles((prev) =>
        prev.map((f, i) =>
          i === index ? { ...f, status: "error", error: err.message } : f
        )
      );
      onUploadError?.(err);
    }
  };

  const uploadAll = async () => {
    const pendingIndices = files
      .map((f, i) => (f.status === "pending" ? i : -1))
      .filter((i) => i >= 0);

    for (const index of pendingIndices) {
      await uploadFile(index);
    }
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const clearCompleted = () => {
    setFiles((prev) => prev.filter((f) => f.status !== "success"));
  };

  const pendingCount = files.filter((f) => f.status === "pending").length;
  const uploadingCount = files.filter((f) => f.status === "uploading").length;
  const successCount = files.filter((f) => f.status === "success").length;

  return (
    <div className={cn("space-y-4", className)}>
      {/* Upload Configuration */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="flex-1">
          <label className="text-sm font-medium text-foreground-muted mb-2 block">
            Tipo de Documento
          </label>
          <Select
            value={selectedDocType}
            onValueChange={(value: DocumentType) => setSelectedDocType(value)}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {DOCUMENT_TYPES.map((type) => (
                <SelectItem key={type.value} value={type.value}>
                  <div className="flex flex-col">
                    <span>{type.label}</span>
                    <span className="text-xs text-foreground-muted">{type.description}</span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex-1">
          <label className="text-sm font-medium text-foreground-muted mb-2 block">
            Conta (opcional)
          </label>
          <Select
            value={selectedAccountId || "none"}
            onValueChange={(value) => setSelectedAccountId(value === "none" ? undefined : value)}
          >
            <SelectTrigger>
              <SelectValue placeholder="Selecione uma conta" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">Nenhuma conta</SelectItem>
              {accountsData?.items.map((account) => (
                <SelectItem key={account.id} value={account.id}>
                  {account.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={cn(
          "relative rounded-xl border-2 border-dashed p-8 transition-all duration-200 cursor-pointer",
          "hover:border-gold/50 hover:bg-gold/5",
          isDragActive && "border-gold bg-gold/10",
          isDragReject && "border-destructive bg-destructive/10",
          !isDragActive && !isDragReject && "border-border-subtle bg-background-subtle"
        )}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center justify-center text-center">
          <div
            className={cn(
              "flex h-16 w-16 items-center justify-center rounded-2xl mb-4 transition-colors",
              isDragActive ? "bg-gold/20" : "bg-gold/10"
            )}
          >
            <Upload
              className={cn(
                "h-8 w-8 transition-colors",
                isDragActive ? "text-gold" : "text-gold/70"
              )}
            />
          </div>
          <p className="font-medium text-lg">
            {isDragActive
              ? "Solte os arquivos aqui"
              : "Arraste e solte seus PDFs aqui"}
          </p>
          <p className="text-sm text-foreground-muted mt-1">
            ou clique para selecionar arquivos
          </p>
          <p className="text-xs text-foreground-dim mt-2">
            Apenas arquivos PDF até 20MB
          </p>
        </div>
      </div>

      {/* File List */}
      {files.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="font-medium">
              Arquivos ({files.length})
            </h4>
            <div className="flex gap-2">
              {successCount > 0 && (
                <Button variant="ghost" size="sm" onClick={clearCompleted}>
                  Limpar concluídos
                </Button>
              )}
              {pendingCount > 0 && (
                <Button
                  size="sm"
                  onClick={uploadAll}
                  disabled={uploadingCount > 0}
                >
                  {uploadingCount > 0 ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Enviando...
                    </>
                  ) : (
                    <>
                      <Upload className="h-4 w-4 mr-2" />
                      Enviar todos ({pendingCount})
                    </>
                  )}
                </Button>
              )}
            </div>
          </div>

          <div className="space-y-2">
            {files.map((fileData, index) => (
              <div
                key={`${fileData.file.name}-${index}`}
                className={cn(
                  "flex items-center gap-3 p-3 rounded-lg border transition-colors",
                  fileData.status === "success" && "bg-success/5 border-success/20",
                  fileData.status === "error" && "bg-destructive/5 border-destructive/20",
                  fileData.status === "uploading" && "bg-gold/5 border-gold/20",
                  fileData.status === "pending" && "bg-background-subtle border-border-subtle"
                )}
              >
                <div
                  className={cn(
                    "flex h-10 w-10 items-center justify-center rounded-lg",
                    fileData.status === "success" && "bg-success/10",
                    fileData.status === "error" && "bg-destructive/10",
                    fileData.status === "uploading" && "bg-gold/10",
                    fileData.status === "pending" && "bg-gold/10"
                  )}
                >
                  {fileData.status === "uploading" ? (
                    <Loader2 className="h-5 w-5 text-gold animate-spin" />
                  ) : fileData.status === "success" ? (
                    <CheckCircle2 className="h-5 w-5 text-success" />
                  ) : fileData.status === "error" ? (
                    <AlertCircle className="h-5 w-5 text-destructive" />
                  ) : (
                    <FileText className="h-5 w-5 text-gold" />
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate">{fileData.file.name}</p>
                  <p className="text-xs text-foreground-muted">
                    {(fileData.file.size / 1024 / 1024).toFixed(2)} MB
                    {" • "}
                    {DOCUMENT_TYPES.find((t) => t.value === fileData.docType)?.label}
                    {fileData.error && (
                      <span className="text-destructive"> • {fileData.error}</span>
                    )}
                  </p>
                </div>

                {fileData.status === "pending" && (
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => uploadFile(index)}
                    >
                      <Upload className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 hover:bg-destructive/10 hover:text-destructive"
                      onClick={() => removeFile(index)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                )}

                {fileData.status === "error" && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 hover:bg-destructive/10 hover:text-destructive"
                    onClick={() => removeFile(index)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
