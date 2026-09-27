"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileText } from "lucide-react";
import { useState } from "react";

import { ExtractionProgress } from "@/components/documents/extraction-progress";
import { ExtractionStatusBadge } from "@/components/ui/assessment-badge";
import { FileDropzone } from "@/components/ui/file-dropzone";
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

  // A tender package is usually several files, so a drop can carry many;
  // they upload one after another and each failure is reported by name.
  const uploadMutation = useMutation({
    mutationFn: async (files: File[]) => {
      const failures: string[] = [];
      for (const file of files) {
        const formData = new FormData();
        formData.append("document_type", documentType);
        formData.append("file", file);
        try {
          await apiRequest<TenderDocument>(`/api/projects/${projectId}/documents`, {
            method: "POST",
            body: formData,
          });
        } catch (err) {
          failures.push(`${file.name}: ${err instanceof ApiError ? err.message : "upload failed"}`);
        }
        queryClient.invalidateQueries({ queryKey: ["documents", projectId] });
      }
      if (failures.length > 0) throw new Error(failures.join(" "));
    },
    onSuccess: () => setError(null),
    onError: (err) => {
      setError(err instanceof Error ? err.message : "Upload failed.");
    },
  });

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
      </div>
      <FileDropzone
        multiple
        compact
        className="mb-4"
        disabled={uploadMutation.isPending}
        title={
          uploadMutation.isPending
            ? "Uploading…"
            : "Drag tender or bid documents here or click to browse"
        }
        onFiles={(files) => uploadMutation.mutate(files)}
      />

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
                <ExtractionProgress
                  status={doc.extraction_status}
                  pagesDone={doc.extraction_pages_done}
                  pageCount={doc.page_count}
                  error={doc.extraction_error}
                />
              </div>
              <ExtractionStatusBadge status={doc.extraction_status} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
