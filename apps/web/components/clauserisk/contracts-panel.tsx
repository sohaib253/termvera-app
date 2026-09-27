"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileSignature, Plus } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { ContractStatusBadge } from "@/components/ui/clauserisk-badge";
import { FileDropzone } from "@/components/ui/file-dropzone";
import { Input } from "@/components/ui/input";
import { apiRequest, ApiError } from "@/lib/api-client";
import type { Contract, ContractCreateInput } from "@/lib/types";
import { nameFromFilename } from "@/lib/upload";
import { routes } from "@/lib/routes";

/** Contracts inside one project. Adding a contract takes the document in
 *  the same step: drop the file, confirm the name, and it is uploaded and
 *  queued for risk analysis, with no detour to the contract page first. */
export function ContractsPanel({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [runAnalysis, setRunAnalysis] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { data: contracts, isLoading } = useQuery({
    queryKey: ["contracts", "project", projectId],
    queryFn: () => apiRequest<Contract[]>(`/api/projects/${projectId}/contracts`),
  });

  const createMutation = useMutation({
    mutationFn: async ({ data, upload }: { data: ContractCreateInput; upload: File | null }) => {
      const contract = await apiRequest<Contract>(`/api/projects/${projectId}/contracts`, {
        method: "POST",
        body: data,
      });
      if (upload) {
        const formData = new FormData();
        formData.append("version_label", "Original");
        formData.append("file", upload);
        formData.append("run_analysis", runAnalysis ? "true" : "false");
        try {
          await apiRequest(`/api/contracts/${contract.id}/versions`, {
            method: "POST",
            body: formData,
          });
        } catch (err) {
          // The contract exists now; say the upload failed rather than
          // leaving the user to think nothing was created.
          const reason = err instanceof ApiError ? err.message : "Upload failed.";
          throw new Error(
            `"${contract.name}" was created, but the document could not be uploaded: ${reason} Open the contract to try again.`
          );
        }
      }
      return contract;
    },
    onSuccess: () => {
      setName("");
      setFile(null);
      setError(null);
    },
    onError: (err) => {
      setError(
        err instanceof ApiError || err instanceof Error
          ? err.message
          : "Could not create the contract."
      );
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["contracts", "project", projectId] });
      queryClient.invalidateQueries({ queryKey: ["contracts"] });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    createMutation.mutate({ data: { name: name.trim() }, upload: file });
  };

  return (
    <div>
      <form onSubmit={handleSubmit} className="mb-4 space-y-3">
        <FileDropzone
          compact
          selected={file}
          disabled={createMutation.isPending}
          title="Drag the contract document here or click to browse"
          onFiles={([chosen]) => {
            setFile(chosen);
            if (!name.trim()) setName(nameFromFilename(chosen.name));
          }}
        />
        <div className="flex items-end gap-3">
          <div className="flex-1">
            <Input
              placeholder="Contract name, e.g. Offshore Services Agreement"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <Button
            type="submit"
            variant="secondary"
            disabled={createMutation.isPending || !name.trim()}
          >
            <Plus className="h-4 w-4" />
            {createMutation.isPending ? (file ? "Uploading…" : "Adding…") : "Add contract"}
          </Button>
        </div>
        {file && (
          <label className="flex items-center gap-2 text-sm text-foreground">
            <input
              type="checkbox"
              checked={runAnalysis}
              onChange={(e) => setRunAnalysis(e.target.checked)}
            />
            Run risk analysis automatically once the text has been read
          </label>
        )}
      </form>

      {error && (
        <p className="mb-4 rounded-md status-critical border px-3 py-2 text-sm" role="alert">
          {error}
        </p>
      )}

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading contracts…</p>
      ) : !contracts || contracts.length === 0 ? (
        <div className="flex flex-col items-center py-8 text-center">
          <FileSignature className="h-8 w-8 text-muted-foreground" />
          <p className="mt-3 text-sm text-muted-foreground">
            No contracts added yet. Drop a contract document above to add it and run risk
            analysis.
          </p>
        </div>
      ) : (
        <ul className="divide-y divide-[var(--border)] rounded-md border border-[var(--border)]">
          {contracts.map((contract) => (
            <li key={contract.id}>
              <Link
                href={routes.contract(contract.id)}
                className="flex items-center justify-between px-4 py-3 text-sm hover:bg-gray-50"
              >
                <div className="min-w-0">
                  <p className="truncate font-medium text-foreground">{contract.name}</p>
                  <p className="text-muted-foreground">
                    {contract.counterparty_name ?? "No counterparty specified"}
                  </p>
                </div>
                <ContractStatusBadge status={contract.status} />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
