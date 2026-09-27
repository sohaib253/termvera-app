"use client";

import { useQuery } from "@tanstack/react-query";
import { Download } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LicenseCard } from "@/components/license/license-card";
import { apiRequest, downloadFile } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { BRAND } from "@/lib/brand";
import type { SampleDocument, Usage } from "@/lib/types";

export default function SettingsPage() {
  const { me } = useAuth();
  const [error, setError] = useState<string | null>(null);
  // A key that failed during first-run setup arrives here to be retried.
  const [keyError] = useState<string | null>(() =>
    typeof window === "undefined" ? null : new URLSearchParams(window.location.search).get("keyError")
  );

  const { data: usage } = useQuery({
    queryKey: ["usage"],
    queryFn: () => apiRequest<Usage>("/api/usage"),
  });

  const { data: samples } = useQuery({
    queryKey: ["samples"],
    queryFn: () => apiRequest<SampleDocument[]>("/api/samples"),
  });

  return (
    <div className="mx-auto max-w-4xl pb-16">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-foreground">Settings</h1>
        <p className="text-sm text-muted-foreground">
          {me?.organization.name}
          {me ? ` · signed in as ${me.user.full_name} (${me.role})` : ""}
        </p>
      </div>

      <LicenseCard usage={usage} isAdmin={!!me?.is_admin} initialError={keyError} />

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
                    {sample.module === "tenderguard" ? BRAND.modules.compliance : BRAND.modules.contractRisk} ·{" "}
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
          {error && (
            <p className="mt-4 rounded-md status-critical border px-3 py-2 text-sm" role="alert">
              {error}
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
