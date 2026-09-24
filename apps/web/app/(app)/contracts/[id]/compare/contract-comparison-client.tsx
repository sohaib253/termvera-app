"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowLeft, GitCompare } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { apiRequest, ApiError } from "@/lib/api-client";
import type { ContractComparison, ContractDetail } from "@/lib/types";

export function ContractComparisonClient({ contractId }: { contractId: string }) {
  const [baseVersionId, setBaseVersionId] = useState("");
  const [comparedVersionId, setComparedVersionId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data: contract, isLoading } = useQuery({
    queryKey: ["contracts", contractId],
    queryFn: () => apiRequest<ContractDetail>(`/api/contracts/${contractId}`),
  });

  const compareMutation = useMutation({
    mutationFn: () =>
      apiRequest<ContractComparison>(`/api/contracts/${contractId}/comparisons`, {
        method: "POST",
        body: { base_version_id: baseVersionId, compared_version_id: comparedVersionId },
      }),
    onSuccess: () => setError(null),
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : "Could not compare these versions.");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!baseVersionId || !comparedVersionId || baseVersionId === comparedVersionId) return;
    compareMutation.mutate();
  };

  if (isLoading) return <div className="text-sm text-muted-foreground">Loading…</div>;
  if (!contract) {
    return (
      <div className="mx-auto max-w-4xl">
        <BackLink contractId={contractId} />
        <p className="mt-4 rounded-md status-critical border px-4 py-3 text-sm">Contract not found.</p>
      </div>
    );
  }

  const comparison = compareMutation.data;
  const materialChanges = comparison?.changes.filter((c) => c.materiality === "material") ?? [];
  const minorChanges = comparison?.changes.filter((c) => c.materiality === "minor") ?? [];

  return (
    <div className="mx-auto max-w-4xl pb-16">
      <BackLink contractId={contractId} />

      <div className="mb-6 mt-4">
        <h1 className="text-2xl font-semibold text-foreground">Contract comparison</h1>
        <p className="text-sm text-muted-foreground">{contract.name}</p>
      </div>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Choose versions</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-4">
            <div>
              <Label htmlFor="base_version">Base version</Label>
              <select
                id="base_version"
                value={baseVersionId}
                onChange={(e) => setBaseVersionId(e.target.value)}
                className="h-10 min-w-[220px] rounded-md border border-[var(--border)] bg-white px-3 text-sm"
              >
                <option value="">Select a version…</option>
                {contract.versions.map((v) => (
                  <option key={v.id} value={v.id}>
                    v{v.version_number} — {v.version_label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <Label htmlFor="compared_version">Compared version</Label>
              <select
                id="compared_version"
                value={comparedVersionId}
                onChange={(e) => setComparedVersionId(e.target.value)}
                className="h-10 min-w-[220px] rounded-md border border-[var(--border)] bg-white px-3 text-sm"
              >
                <option value="">Select a version…</option>
                {contract.versions.map((v) => (
                  <option key={v.id} value={v.id}>
                    v{v.version_number} — {v.version_label}
                  </option>
                ))}
              </select>
            </div>
            <Button
              type="submit"
              disabled={
                compareMutation.isPending ||
                !baseVersionId ||
                !comparedVersionId ||
                baseVersionId === comparedVersionId
              }
            >
              <GitCompare className="h-4 w-4" />
              {compareMutation.isPending ? "Comparing…" : "Compare"}
            </Button>
          </form>
          <p className="mt-3 text-xs text-muted-foreground">
            Both versions must have completed clause analysis — the comparison diffs extracted
            clauses, it doesn&apos;t re-read the raw PDFs.
          </p>
          {error && (
            <p className="mt-3 rounded-md status-critical border px-3 py-2 text-sm" role="alert">
              {error}
            </p>
          )}
        </CardContent>
      </Card>

      {comparison && (
        <>
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Material changes</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {materialChanges.length === 0 ? (
                <div className="px-5 py-8 text-center text-sm text-muted-foreground">
                  No material changes detected between these versions.
                </div>
              ) : (
                <ChangesTable changes={materialChanges} />
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Minor changes</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {minorChanges.length === 0 ? (
                <div className="px-5 py-8 text-center text-sm text-muted-foreground">
                  No minor changes detected between these versions.
                </div>
              ) : (
                <ChangesTable changes={minorChanges} />
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

function ChangesTable({ changes }: { changes: ContractComparison["changes"] }) {
  const CHANGE_LABEL: Record<string, string> = {
    added: "Added",
    deleted: "Deleted",
    modified: "Modified",
  };
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wide text-muted-foreground">
            <th className="px-4 py-3 font-medium">Clause</th>
            <th className="px-4 py-3 font-medium">Category</th>
            <th className="px-4 py-3 font-medium">Change</th>
            <th className="px-4 py-3 font-medium">Description</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--border)]">
          {changes.map((change) => (
            <tr key={change.id}>
              <td className="px-4 py-3 font-medium text-foreground">{change.clause_number ?? "—"}</td>
              <td className="px-4 py-3 capitalize text-muted-foreground">
                {change.category?.replace(/_/g, " ") ?? "—"}
              </td>
              <td className="px-4 py-3 text-muted-foreground">{CHANGE_LABEL[change.change_type]}</td>
              <td className="px-4 py-3 text-foreground">
                {change.description}
                {change.financial_delta && (
                  <span className="ml-2 rounded status-warning border px-1.5 py-0.5 text-xs">
                    {change.financial_delta}
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function BackLink({ contractId }: { contractId: string }) {
  return (
    <Link
      href={`/contracts/${contractId}`}
      className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
    >
      <ArrowLeft className="h-4 w-4" />
      Back to contract
    </Link>
  );
}
