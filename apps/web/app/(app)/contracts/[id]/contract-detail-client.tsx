"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, GitCompare, Play, Upload } from "lucide-react";
import Link from "next/link";
import { useRef, useState } from "react";

import { AnalysisProgress } from "@/components/clauserisk/analysis-progress";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ContractAnalysisStatusBadge, ContractStatusBadge } from "@/components/ui/clauserisk-badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiRequest, ApiError } from "@/lib/api-client";
import type { ContractDetail, ContractStatus, ContractVersion } from "@/lib/types";

const STATUS_OPTIONS: ContractStatus[] = ["draft", "under_review", "active", "superseded", "archived"];

export function ContractDetailClient({ contractId }: { contractId: string }) {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [versionLabel, setVersionLabel] = useState("");
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);

  const { data: contract, isLoading, error: fetchError } = useQuery({
    queryKey: ["contracts", contractId],
    queryFn: () => apiRequest<ContractDetail>(`/api/contracts/${contractId}`),
    refetchInterval: (query) => {
      const versions = query.state.data?.versions ?? [];
      return versions.some((v) => v.analysis_status === "processing") ? 3000 : false;
    },
  });

  const statusMutation = useMutation({
    mutationFn: (status: ContractStatus) =>
      apiRequest<ContractDetail>(`/api/contracts/${contractId}`, { method: "PATCH", body: { status } }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["contracts", contractId], updated);
      queryClient.invalidateQueries({ queryKey: ["contracts"] });
      setStatusError(null);
    },
    onError: (err) => {
      setStatusError(err instanceof ApiError ? err.message : "Could not update status.");
    },
  });

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("version_label", versionLabel || `Version ${(contract?.versions.length ?? 0) + 1}`);
      formData.append("file", file);
      return apiRequest<ContractVersion>(`/api/contracts/${contractId}/versions`, {
        method: "POST",
        body: formData,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contracts", contractId] });
      setVersionLabel("");
      setUploadError(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    },
    onError: (err) => {
      setUploadError(err instanceof ApiError ? err.message : "Upload failed.");
    },
  });

  const analysisMutation = useMutation({
    mutationFn: (versionId: string) =>
      apiRequest(`/api/contract-versions/${versionId}/analysis`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contracts", contractId] });
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) uploadMutation.mutate(file);
  };

  if (isLoading) return <div className="text-sm text-muted-foreground">Loading…</div>;

  if (fetchError || !contract) {
    return (
      <div className="mx-auto max-w-3xl">
        <BackLink />
        <p className="mt-4 rounded-md status-critical border px-4 py-3 text-sm">
          {fetchError instanceof ApiError ? fetchError.message : "Contract not found."}
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl pb-16">
      <BackLink />

      <div className="mb-6 mt-4 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">{contract.name}</h1>
          <p className="text-sm text-muted-foreground">
            {contract.counterparty_name ?? "No counterparty specified"}
          </p>
        </div>
        <ContractStatusBadge status={contract.status} />
      </div>

      {contract.is_demo && (
        <p className="mb-6 rounded-md status-warning border px-3 py-2 text-xs">
          Sample data — fictional contract, for demonstration only.
        </p>
      )}

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Contract details</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-2 gap-4 text-sm">
            <Field label="Contract type" value={contract.contract_type.replace(/_/g, " ")} />
            <Field label="Counterparty" value={contract.counterparty_name} />
            <Field label="Effective date" value={contract.effective_date} />
          </dl>
          {contract.notes && (
            <div className="mt-4">
              <Label>Notes</Label>
              <p className="text-sm text-foreground">{contract.notes}</p>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Status</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {STATUS_OPTIONS.map((status) => (
              <Button
                key={status}
                size="sm"
                variant={status === contract.status ? "primary" : "secondary"}
                disabled={statusMutation.isPending}
                onClick={() => statusMutation.mutate(status)}
              >
                {status.replace(/_/g, " ")}
              </Button>
            ))}
          </div>
          {statusError && (
            <p className="mt-3 rounded-md status-critical border px-3 py-2 text-sm" role="alert">
              {statusError}
            </p>
          )}
        </CardContent>
      </Card>

      <Card className="mb-6">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Versions</CardTitle>
            {contract.versions.length >= 2 && (
              <Link href={`/contracts/${contract.id}/compare`}>
                <Button size="sm" variant="secondary">
                  <GitCompare className="h-4 w-4" />
                  Compare versions
                </Button>
              </Link>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className="mb-4 flex items-end gap-3">
            <div className="flex-1">
              <Label htmlFor="version_label">Version label</Label>
              <Input
                id="version_label"
                placeholder="e.g. Amendment 1"
                value={versionLabel}
                onChange={(e) => setVersionLabel(e.target.value)}
              />
            </div>
            <Button
              type="button"
              variant="secondary"
              disabled={uploadMutation.isPending}
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload className="h-4 w-4" />
              {uploadMutation.isPending ? "Uploading…" : "Upload version PDF"}
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf"
              className="hidden"
              onChange={handleFileChange}
            />
          </div>

          {uploadError && (
            <p className="mb-4 rounded-md status-critical border px-3 py-2 text-sm" role="alert">
              {uploadError}
            </p>
          )}

          {contract.versions.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No versions uploaded yet. Upload a contract PDF to begin.
            </p>
          ) : (
            <ul className="divide-y divide-[var(--border)] rounded-md border border-[var(--border)]">
              {contract.versions.map((version) => (
                <li key={version.id} className="px-4 py-3 text-sm">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <Link
                        href={`/contracts/${contract.id}/versions/${version.id}`}
                        className="font-medium text-primary hover:underline"
                      >
                        v{version.version_number} — {version.version_label}
                      </Link>
                      {version.analysis_status === "failed" && version.analysis_error && (
                        <p className="mt-1 text-xs text-[var(--status-critical-fg)]">
                          {version.analysis_error}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-3">
                      <ContractAnalysisStatusBadge status={version.analysis_status} />
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={
                          analysisMutation.isPending || version.analysis_status === "processing"
                        }
                        onClick={() => analysisMutation.mutate(version.id)}
                      >
                        <Play className="h-4 w-4" />
                        {version.analysis_status === "completed" ? "Re-run" : "Run analysis"}
                      </Button>
                    </div>
                  </div>
                  {version.analysis_status === "processing" && (
                    <div className="mt-3">
                      <AnalysisProgress
                        status={{
                          analysis_status: version.analysis_status,
                          analysis_error: version.analysis_error,
                          analysis_started_at: version.analysis_started_at,
                          analysis_completed_at: version.analysis_completed_at,
                          analysis_stage: version.analysis_stage,
                          analysis_progress_current: version.analysis_progress_current,
                          analysis_progress_total: version.analysis_progress_total,
                        }}
                      />
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function BackLink() {
  return (
    <Link href="/contracts" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
      <ArrowLeft className="h-4 w-4" />
      Back to contracts
    </Link>
  );
}

function Field({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="capitalize text-foreground">{value ?? "—"}</dd>
    </div>
  );
}
