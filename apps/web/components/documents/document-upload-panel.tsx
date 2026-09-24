"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileText, Upload } from "lucide-react";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { ExtractionStatusBadge } from "@/components/ui/assessment-badge";
import { Label } from "@/components/ui/label";
import { apiRequest, ApiError } from "@/lib/api-client";
import type { DocumentType, TenderDocument } from "@/lib/types";

const DOCUMENT_TYPE_OPTIONS: { value: DocumentType; label: string }[] = [
  { value: "tender", label: "Tender source" },
  { value: "bid", label: "Bid response" },
  { value: "supporting", label: "Supporting evidence" },
  { value: "reference", label: "Additional reference" },
];

export function DocumentUploadPanel({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [documentType, setDocumentType] = useState<DocumentType>("tender");
  const [error, setError] = useState<string | null>(null);

  const { data: documents, isLoading } = useQuery({
    queryKey: ["documents", projectId],
    queryFn: () => apiRequest<TenderDocument[]>(`/api/projects/${projectId}/documents`),
    refetchInterval: (query) => {
      const docs = query.state.data;
      const hasPending = docs?.some(
        (d) => d.extraction_status === "pending" || d.extraction_status === "processing"
      );
      return hasPending ? 2000 : false;
    },
  });

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("document_type", documentType);
      formData.append("file", file);
      return apiRequest<TenderDocument>(`/api/projects/${projectId}/documents`, {
        method: "POST",
        body: formData,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", projectId] });
      setError(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : "Upload failed.");
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) uploadMutation.mutate(file);
  };

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <div>
          <Label htmlFor="document_type">Document type</Label>
          <select
            id="document_type"
            value={documentType}
            onChange={(e) => setDocumentType(e.target.value as DocumentType)}
            className="h-10 rounded-md border border-[var(--border)] bg-white px-3 text-sm"
          >
            {DOCUMENT_TYPE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
        <Button
          type="button"
          variant="secondary"
          disabled={uploadMutation.isPending}
          onClick={() => fileInputRef.current?.click()}
        >
          <Upload className="h-4 w-4" />
          {uploadMutation.isPending ? "Uploading…" : "Upload PDF"}
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={handleFileChange}
        />
      </div>

      {error && (
        <p className="mb-4 rounded-md status-critical border px-3 py-2 text-sm" role="alert">
          {error}
        </p>
      )}

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading documents…</p>
      ) : !documents || documents.length === 0 ? (
        <div className="flex flex-col items-center py-8 text-center">
          <FileText className="h-8 w-8 text-muted-foreground" />
          <p className="mt-3 text-sm text-muted-foreground">
            No documents uploaded yet. Upload the tender package and your draft bid to begin.
          </p>
        </div>
      ) : (
        <ul className="divide-y divide-[var(--border)] rounded-md border border-[var(--border)]">
          {documents.map((doc) => (
            <li key={doc.id} className="flex items-center justify-between px-4 py-3 text-sm">
              <div className="min-w-0">
                <p className="truncate font-medium text-foreground">{doc.original_filename}</p>
                <p className="text-muted-foreground">
                  {DOCUMENT_TYPE_OPTIONS.find((o) => o.value === doc.document_type)?.label}
                  {doc.page_count ? ` · ${doc.page_count} pages` : ""}
                </p>
                {doc.extraction_status === "failed" && doc.extraction_error && (
                  <p className="mt-1 text-xs text-red-600">{doc.extraction_error}</p>
                )}
              </div>
              <ExtractionStatusBadge status={doc.extraction_status} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
