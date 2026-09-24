"use client";

import { useQuery } from "@tanstack/react-query";
import { FileSignature, Plus } from "lucide-react";
import Link from "next/link";

import { LoadDemoContractButton } from "@/components/clauserisk/load-demo-contract-button";
import { Button } from "@/components/ui/button";
import { ContractStatusBadge } from "@/components/ui/clauserisk-badge";
import { Card, CardContent } from "@/components/ui/card";
import { apiRequest } from "@/lib/api-client";
import type { ContractListItem } from "@/lib/types";

export default function ContractsPage() {
  const { data: contracts, isLoading } = useQuery({
    queryKey: ["contracts"],
    queryFn: () => apiRequest<ContractListItem[]>("/api/contracts"),
  });

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Contracts</h1>
          <p className="text-sm text-muted-foreground">
            Every contract across your projects, with clause extraction and risk analysis.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <LoadDemoContractButton />
          <Link href="/contracts/new">
            <Button>
              <Plus className="h-4 w-4" />
              New contract review
            </Button>
          </Link>
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="px-5 py-8 text-center text-sm text-muted-foreground">Loading…</div>
          ) : !contracts || contracts.length === 0 ? (
            <div className="flex flex-col items-center px-5 py-12 text-center">
              <FileSignature className="h-10 w-10 text-muted-foreground" />
              <h3 className="mt-4 text-sm font-semibold text-foreground">No contracts yet</h3>
              <p className="mt-1 max-w-sm text-sm text-muted-foreground">
                Upload a contract PDF to get clause-by-clause risk scoring, or load the fictional
                sample contract to see what a finished review looks like.
              </p>
              <div className="mt-4 flex flex-wrap items-center justify-center gap-3">
                <Link href="/contracts/new">
                  <Button size="sm">
                    <Plus className="h-4 w-4" />
                    New contract review
                  </Button>
                </Link>
                <LoadDemoContractButton />
              </div>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wide text-muted-foreground">
                  <th className="px-5 py-3 font-medium">Name</th>
                  <th className="px-5 py-3 font-medium">Project</th>
                  <th className="px-5 py-3 font-medium">Counterparty</th>
                  <th className="px-5 py-3 font-medium">Type</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {contracts.map((contract) => (
                  <tr key={contract.id} className="hover:bg-gray-50">
                    <td className="px-5 py-3">
                      <Link href={`/contracts/${contract.id}`} className="font-medium text-primary hover:underline">
                        {contract.name}
                      </Link>
                    </td>
                    <td className="px-5 py-3 text-muted-foreground">{contract.project_name}</td>
                    <td className="px-5 py-3 text-muted-foreground">{contract.counterparty_name ?? "—"}</td>
                    <td className="px-5 py-3 capitalize text-muted-foreground">
                      {contract.contract_type.replace(/_/g, " ")}
                    </td>
                    <td className="px-5 py-3">
                      <ContractStatusBadge status={contract.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
