"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, ShieldCheck } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiRequest, ApiError, downloadFile } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { License, LicensePlan, SampleDocument, Usage } from "@/lib/types";

const PLANS: { value: LicensePlan; label: string; detail: string }[] = [
  { value: "demo", label: "Demo", detail: "3 projects, 10 contracts, 10 analyses per month" },
  { value: "trial", label: "Trial", detail: "10 projects, 25 contracts, 25 analyses per month" },
  {
    value: "professional",
    label: "Professional",
    detail: "100 projects, 250 contracts, 250 analyses per month",
  },
  { value: "enterprise", label: "Enterprise", detail: "Unlimited projects, contracts, and analyses" },
];

function formatLimit(limit: number): string {
  return limit < 0 ? "Unlimited" : String(limit);
}

export default function SettingsPage() {
  const { me } = useAuth();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const { data: usage } = useQuery({
    queryKey: ["usage"],
    queryFn: () => apiRequest<Usage>("/api/usage"),
  });

  const { data: samples } = useQuery({
    queryKey: ["samples"],
    queryFn: () => apiRequest<SampleDocument[]>("/api/samples"),
  });

  const planMutation = useMutation({
    mutationFn: (plan: LicensePlan) =>
      apiRequest<License>("/api/license", { method: "PATCH", body: { plan } }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["usage"] });
      setError(null);
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : "Could not change the plan.");
    },
  });

  const license = usage?.license;

  return (
    <div className="mx-auto max-w-4xl pb-16">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-foreground">Settings</h1>
        <p className="text-sm text-muted-foreground">
          {me?.organization.name}
          {me ? ` · signed in as ${me.user.full_name} (${me.role})` : ""}
        </p>
      </div>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Sample documents</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="mb-4 text-sm text-muted-foreground">
            Fictional but realistic documents you can download, read, and then upload through the
            normal flow. Nothing about them is special-cased, so running them is a fair test of
            what the product does with your own files.
          </p>
          <ul className="divide-y divide-[var(--border)] rounded-md border border-[var(--border)]">
            {(samples ?? []).map((sample) => (
              <li key={sample.key} className="flex items-start justify-between gap-4 px-4 py-3">
                <div>
                  <p className="text-sm font-medium text-foreground">{sample.title}</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">{sample.description}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {sample.module === "tenderguard" ? "Compliance" : "ClauseRisk"} ·{" "}
                    {Math.round(sample.size_bytes / 1024)} KB
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() =>
                    downloadFile(`/api/samples/${sample.key}/file`, sample.filename).catch(() => {
                      setError("Could not download that sample document.");
                    })
                  }
                >
                  <Download className="h-4 w-4" />
                  Download
                </Button>
              </li>
            ))}
            {samples?.length === 0 && (
              <li className="px-4 py-6 text-center text-sm text-muted-foreground">
                No sample documents are available on this server.
              </li>
            )}
          </ul>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Plan and limits</CardTitle>
        </CardHeader>
        <CardContent>
          {license && (
            <dl className="mb-5 grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
              <Stat label="Plan" value={license.plan} capitalize />
              <Stat
                label="Projects"
                value={`${usage?.projects_used ?? 0} / ${formatLimit(license.project_limit)}`}
              />
              <Stat
                label="Contracts"
                value={`${usage?.contracts_used ?? 0} / ${formatLimit(license.monthly_contract_limit)}`}
              />
              <Stat
                label="Analyses this month"
                value={`${usage?.analyses_used_this_period ?? 0} / ${formatLimit(license.monthly_analysis_limit)}`}
              />
            </dl>
          )}

          {me?.is_admin ? (
            <>
              <p className="mb-3 text-sm text-muted-foreground">
                There is no payment provider wired up, so as a workspace administrator you set the
                plan directly here. Enterprise removes the project, contract, and analysis ceilings.
              </p>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {PLANS.map((plan) => {
                  const isCurrent = license?.plan === plan.value;
                  return (
                    <button
                      key={plan.value}
                      type="button"
                      disabled={planMutation.isPending || isCurrent}
                      onClick={() => planMutation.mutate(plan.value)}
                      className={
                        "rounded-lg border px-4 py-3 text-left transition-colors " +
                        (isCurrent
                          ? "border-[var(--severity-medium-border)] bg-[var(--severity-medium-bg)]"
                          : "border-[var(--border)] hover:bg-gray-50")
                      }
                    >
                      <span className="flex items-center gap-2 text-sm font-medium text-foreground">
                        {plan.label}
                        {isCurrent && (
                          <span className="inline-flex items-center gap-1 text-xs font-normal text-primary">
                            <ShieldCheck className="h-3 w-3" />
                            Current
                          </span>
                        )}
                      </span>
                      <span className="mt-0.5 block text-xs text-muted-foreground">
                        {plan.detail}
                      </span>
                    </button>
                  );
                })}
              </div>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">
              Only a workspace owner or administrator can change the plan.
            </p>
          )}

          {error && (
            <p className="mt-4 rounded-md status-critical border px-3 py-2 text-sm" role="alert">
              {error}
            </p>
          )}

          <p className="mt-4 text-xs text-muted-foreground">
            Usage limits are enforced for real, but this is a local entitlement fixture: no signed
            licence, no remote validation, no payment integration.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

function Stat({
  label,
  value,
  capitalize,
}: {
  label: string;
  value: string;
  capitalize?: boolean;
}) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className={"text-foreground " + (capitalize ? "capitalize" : "")}>{value}</dd>
    </div>
  );
}
