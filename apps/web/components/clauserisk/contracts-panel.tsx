"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileSignature, Plus } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { ContractStatusBadge } from "@/components/ui/clauserisk-badge";
import { Input } from "@/components/ui/input";
import { apiRequest, ApiError } from "@/lib/api-client";
import type { Contract, ContractCreateInput } from "@/lib/types";

export function ContractsPanel({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data: contracts, isLoading } = useQuery({
    queryKey: ["contracts", "project", projectId],
    queryFn: () => apiRequest<Contract[]>(`/api/projects/${projectId}/contracts`),
  });

  const createMutation = useMutation({
    mutationFn: (data: ContractCreateInput) =>
      apiRequest<Contract>(`/api/projects/${projectId}/contracts`, { method: "POST", body: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contracts", "project", projectId] });
      queryClient.invalidateQueries({ queryKey: ["contracts"] });
      setName("");
      setError(null);
    },
    onError: (err) => {
      setError(
        err instanceof ApiError
          ? err.message
          : "Could not create the contract. ClauseRisk may not be enabled on this license."
      );
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    createMutation.mutate({ name: name.trim() });
  };

  return (
    <div>
      <form onSubmit={handleSubmit} className="mb-4 flex items-end gap-3">
        <div className="flex-1">
          <Input
            placeholder="Contract name, e.g. Offshore Services Agreement"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>
        <Button type="submit" variant="secondary" disabled={createMutation.isPending || !name.trim()}>
          <Plus className="h-4 w-4" />
          Add contract
        </Button>
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
            No contracts added yet. Add one to upload versions and run risk analysis.
          </p>
        </div>
      ) : (
        <ul className="divide-y divide-[var(--border)] rounded-md border border-[var(--border)]">
          {contracts.map((contract) => (
            <li key={contract.id}>
              <Link
                href={`/contracts/${contract.id}`}
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
