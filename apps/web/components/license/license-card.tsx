"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, Copy, KeyRound } from "lucide-react";
import { useState } from "react";

import { useLicense } from "@/components/license/license-status";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiRequest, ApiError } from "@/lib/api-client";
import { BRAND } from "@/lib/brand";
import type { License, Usage } from "@/lib/types";

const STATE_LABEL: Record<License["state"], string> = {
  free: "Free (early access)",
  trial: "Free trial",
  trial_expired: "Trial ended (view-only)",
  active: "Active",
  grace: "Ended, grace period",
  expired: "Ended (view-only)",
  other_machine: "For another computer (view-only)",
};

function formatLimit(limit: number): string {
  return limit < 0 ? "Unlimited" : String(limit);
}

function formatDate(value: string | null): string {
  // Licence dates are whole days stored as end-of-day UTC; showing them in
  // local time would roll the date forward east of Greenwich.
  return value
    ? new Date(value).toLocaleDateString(undefined, { dateStyle: "medium", timeZone: "UTC" })
    : "—";
}

export function LicenseCard({
  usage,
  isAdmin,
  initialError,
}: {
  usage: Usage | undefined;
  isAdmin: boolean;
  initialError?: string | null;
}) {
  const queryClient = useQueryClient();
  const { data: license } = useLicense();
  const [key, setKey] = useState("");
  const [error, setError] = useState<string | null>(initialError ?? null);
  const [activated, setActivated] = useState(false);
  const [copied, setCopied] = useState(false);

  const copyMachineId = () => {
    if (!license?.machine_id) return;
    navigator.clipboard
      .writeText(license.machine_id)
      .then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      })
      .catch(() => setCopied(false));
  };

  const activate = useMutation({
    mutationFn: (licenseKey: string) =>
      apiRequest<License>("/api/license/activate", { method: "POST", body: { key: licenseKey } }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["license"], updated);
      queryClient.invalidateQueries({ queryKey: ["usage"] });
      setKey("");
      setError(null);
      setActivated(true);
    },
    onError: (err) => {
      setActivated(false);
      setError(err instanceof ApiError ? err.message : "The key could not be activated.");
    },
  });

  return (
    <Card id="license" className="mb-6 scroll-mt-6">
      <CardHeader>
        <CardTitle>License</CardTitle>
      </CardHeader>
      <CardContent>
        {license && (
          <dl className="mb-5 grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
            <Stat label="Status" value={STATE_LABEL[license.state]} />
            <Stat
              label="Plan"
              value={license.plan.charAt(0).toUpperCase() + license.plan.slice(1)}
            />
            <Stat
              label={license.state === "trial" || license.state === "trial_expired" ? "Trial ends" : "Paid until"}
              value={formatDate(license.state === "grace" || license.state === "expired" ? license.expires_at : license.ends_at)}
            />
            <Stat label="Licensed to" value={license.licensed_to ?? "—"} />
            <Stat
              label="Projects"
              value={`${usage?.projects_used ?? 0} / ${formatLimit(license.project_limit)}`}
            />
            <Stat
              label="Contracts"
              value={`${usage?.contracts_used ?? 0} / ${formatLimit(license.monthly_contract_limit)}`}
            />
            <Stat
              label="Contract analyses this month"
              value={`${usage?.clause_analyses_used_this_period ?? 0} / ${formatLimit(license.monthly_clause_analysis_limit)}`}
            />
            <Stat
              label="Key works on"
              value={license.bound_machine_id ? "This computer only" : license.license_id ? "Any computer" : "—"}
            />
          </dl>
        )}

        {/* Per-PC keys are for customers who ask for them; most never need
            this, so it stays folded away rather than cluttering the card. */}
        {license?.machine_id && (
          <details className="mb-5 text-sm">
            <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
              Licensing specific computers? Show this computer&apos;s Machine ID
            </summary>
          <div className="mt-2 flex flex-wrap items-center gap-3 rounded-md border border-[var(--border)] bg-gray-50 px-4 py-3">
            <div>
              <p className="text-xs uppercase tracking-wide text-muted-foreground">This computer&apos;s Machine ID</p>
              <p className="font-mono text-sm font-semibold tracking-wider text-foreground">{license.machine_id}</p>
            </div>
            <Button type="button" size="sm" variant="secondary" onClick={copyMachineId}>
              {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
              {copied ? "Copied" : "Copy"}
            </Button>
            <p className="basis-full text-xs text-muted-foreground">
              Buying for specific computers? Send us this ID with your order and you&apos;ll get a key
              that works on this PC.
            </p>
          </div>
          </details>
        )}

        {license?.state === "free" && (
          <p className="mb-5 rounded-md status-success border px-3 py-2 text-sm">
            {BRAND.name} is free during early access, with every feature and no limits. You
            don&apos;t need a license key.
          </p>
        )}

        {isAdmin ? (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (key.trim()) activate.mutate(key);
            }}
          >
            <label htmlFor="license_key" className="mb-1 block text-sm font-medium text-foreground">
              {license?.state === "active" ? "Replace license key (renewal or upgrade)" : "Enter license key"}
            </label>
            <textarea
              id="license_key"
              rows={3}
              value={key}
              onChange={(e) => setKey(e.target.value)}
              placeholder="Paste the key from your purchase email. It starts with TMV1."
              className="w-full rounded-md border border-[var(--border)] bg-white px-3 py-2 font-mono text-xs"
            />
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <Button type="submit" disabled={activate.isPending || !key.trim()}>
                <KeyRound className="h-4 w-4" />
                {activate.isPending ? "Activating…" : "Activate"}
              </Button>
              <a
                href={BRAND.purchaseUrl}
                target="_blank"
                rel="noreferrer"
                className="text-sm font-medium text-primary hover:underline"
              >
                Buy or renew a license
              </a>
            </div>
          </form>
        ) : (
          <p className="text-sm text-muted-foreground">
            Only a workspace owner or administrator can enter a license key.
          </p>
        )}

        {activated && (
          <p className="mt-4 rounded-md status-success border px-3 py-2 text-sm" role="status">
            License activated. Thank you for choosing {BRAND.name}.
          </p>
        )}
        {error && (
          <p className="mt-4 rounded-md status-critical border px-3 py-2 text-sm" role="alert">
            {error}
          </p>
        )}
        <p className="mt-4 text-xs text-muted-foreground">
          Keys are checked on this computer; nothing is sent anywhere. Questions about your license:{" "}
          <a href={`mailto:${BRAND.supportEmail}`} className="underline">
            {BRAND.supportEmail}
          </a>
          .
        </p>
      </CardContent>
    </Card>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="mt-0.5 font-medium text-foreground">{value}</dd>
    </div>
  );
}
