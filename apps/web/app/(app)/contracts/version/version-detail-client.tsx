"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ChevronDown, ChevronRight, Download } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { AnalysisProgress } from "@/components/clauserisk/analysis-progress";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ContractAnalysisStatusBadge,
  FindingReviewerStatusBadge,
  RiskScoreBar,
  RiskSeverityBadge,
} from "@/components/ui/clauserisk-badge";
import { apiRequest, ApiError, downloadFile } from "@/lib/api-client";
import { findingTitle } from "@/lib/risk-finding-display";
import type {
  Clause,
  ClauseDetail,
  ContractAnalysisStatusResponse,
  RiskFinding,
} from "@/lib/types";
import { routes } from "@/lib/routes";

export function VersionDetailClient({
  contractId,
  versionId,
}: {
  contractId: string;
  versionId: string;
}) {
  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const { data: status } = useQuery({
    queryKey: ["contract-version-analysis", versionId],
    queryFn: () => apiRequest<ContractAnalysisStatusResponse>(`/api/contract-versions/${versionId}/analysis`),
    refetchInterval: (query) => (query.state.data?.analysis_status === "processing" ? 3000 : false),
  });

  const { data: clauses, isLoading: clausesLoading } = useQuery({
    queryKey: ["clauses", versionId],
    queryFn: () => apiRequest<Clause[]>(`/api/contract-versions/${versionId}/clauses`),
    enabled: status?.analysis_status === "completed",
  });

  const { data: findings, isLoading: findingsLoading } = useQuery({
    queryKey: ["risk-findings", "version", versionId],
    queryFn: () => apiRequest<RiskFinding[]>(`/api/contract-versions/${versionId}/risk-findings`),
    enabled: status?.analysis_status === "completed",
  });

  const handleExport = async () => {
    setIsExporting(true);
    setExportError(null);
    try {
      await downloadFile(`/api/contract-versions/${versionId}/exports/risk-report.xlsx`, "risk-report.xlsx");
    } catch (err) {
      setExportError(err instanceof ApiError ? err.message : "Export failed.");
    } finally {
      setIsExporting(false);
    }
  };

  const criticalCount = findings?.filter((f) => f.severity === "critical").length ?? 0;
  const highCount = findings?.filter((f) => f.severity === "high").length ?? 0;
  const unreviewedCount =
    findings?.filter((f) => f.reviewer_status === "unreviewed").length ?? 0;
  const clauseNumbersById = new Map(
    (clauses ?? []).map((clause) => [clause.id, clause.clause_number ?? "—"])
  );

  return (
    <div className="mx-auto max-w-6xl pb-16">
      <Link
        href={routes.contract(contractId)}
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to contract
      </Link>

      <div className="mb-6 mt-4 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Clause &amp; risk analysis</h1>
          {status && (
            <div className="mt-2 flex items-center gap-2">
              <ContractAnalysisStatusBadge status={status.analysis_status} />
            </div>
          )}
        </div>
        {status?.analysis_status === "completed" && (
          <Button variant="secondary" onClick={handleExport} disabled={isExporting}>
            <Download className="h-4 w-4" />
            {isExporting ? "Exporting…" : "Export risk report"}
          </Button>
        )}
      </div>

      {exportError && (
        <p className="mb-4 rounded-md status-critical border px-3 py-2 text-sm" role="alert">
          {exportError}
        </p>
      )}

      {status?.analysis_status === "processing" && (
        <div className="mb-6">
          <AnalysisProgress status={status} />
        </div>
      )}

      {status?.analysis_status === "failed" && status.analysis_error && (
        <p className="mb-6 rounded-md status-critical border px-4 py-3 text-sm">{status.analysis_error}</p>
      )}

      {status?.analysis_status === "not_started" && (
        <p className="mb-6 rounded-md status-neutral border px-4 py-3 text-sm">
          Analysis hasn&apos;t been run yet. Go back to the contract and click &ldquo;Run
          analysis&rdquo; on this version.
        </p>
      )}

      {status?.analysis_status === "completed" && (
        <>
          <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
            <StatCard label="Clauses extracted" value={clauses?.length ?? 0} />
            <StatCard label="Critical findings" value={criticalCount} tone="critical" />
            <StatCard label="High findings" value={highCount} tone="warning" />
            <StatCard label="Unreviewed" value={unreviewedCount} tone="warning" />
          </div>

          <CommercialTermsCard clauses={clauses ?? []} />

          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Risk findings</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {findingsLoading ? (
                <div className="px-5 py-8 text-center text-sm text-muted-foreground">Loading…</div>
              ) : !findings || findings.length === 0 ? (
                <div className="px-5 py-12 text-center text-sm text-muted-foreground">
                  No risk findings recorded for this version.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wide text-muted-foreground">
                        <th className="px-4 py-3 font-medium">Risk</th>
                        <th className="px-4 py-3 font-medium">Clause</th>
                        <th className="px-4 py-3 font-medium">Category</th>
                        <th className="px-4 py-3 font-medium">Severity</th>
                        <th className="px-4 py-3 font-medium">Score</th>
                        <th className="px-4 py-3 font-medium">Review</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--border)]">
                      {findings.map((finding) => {
                        const { title, subtitle } = findingTitle(finding);
                        return (
                        <tr key={finding.id} className="hover:bg-gray-50">
                          <td className="max-w-md px-4 py-3">
                            <Link
                              href={routes.riskFinding(finding.id)}
                              className="line-clamp-1 font-medium text-primary hover:underline"
                            >
                              {title}
                            </Link>
                            {subtitle && (
                              <p className="mt-0.5 line-clamp-1 text-xs text-muted-foreground">
                                {subtitle}
                              </p>
                            )}
                          </td>
                          <td className="px-4 py-3 tabular-nums text-muted-foreground">
                            {clauseNumbersById.get(finding.clause_id ?? "") ?? "—"}
                          </td>
                          <td className="px-4 py-3 capitalize text-muted-foreground">
                            {finding.category.replace(/_/g, " ")}
                          </td>
                          <td className="px-4 py-3">
                            <RiskSeverityBadge severity={finding.severity} />
                          </td>
                          <td className="px-4 py-3">
                            <RiskScoreBar score={finding.computed_score} severity={finding.severity} />
                          </td>
                          <td className="px-4 py-3">
                            <FindingReviewerStatusBadge status={finding.reviewer_status} />
                          </td>
                        </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Clauses</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {clausesLoading ? (
                <div className="px-5 py-8 text-center text-sm text-muted-foreground">Loading…</div>
              ) : !clauses || clauses.length === 0 ? (
                <div className="px-5 py-12 text-center text-sm text-muted-foreground">
                  No clauses were segmented for this version.
                </div>
              ) : (
                <ul className="divide-y divide-[var(--border)]">
                  {clauses.map((clause) => (
                    <ClauseRow key={clause.id} clause={clause} />
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

// The figures a contract manager checks first, pulled from the clauses the
// extraction stage already tagged. Purely a reorganisation of extracted
// data: nothing here is inferred, and a term with no matching clause is
// shown as "not identified" rather than guessed at.
const KEY_TERMS: { label: string; subcategories: string[] }[] = [
  { label: "Liability cap", subcategories: ["liability_cap", "unlimited_liability"] },
  { label: "Indemnity", subcategories: ["indemnity", "third_party_claims"] },
  { label: "Liquidated damages", subcategories: ["liquidated_damages"] },
  { label: "Payment terms", subcategories: ["payment"] },
  { label: "Retention", subcategories: ["retention"] },
  { label: "Insurance", subcategories: ["insurance_limits", "insurance_policy_requirements"] },
  { label: "Termination", subcategories: ["termination_for_convenience", "termination_for_cause"] },
  { label: "Governing law", subcategories: ["governing_law", "jurisdiction", "arbitration"] },
];

function CommercialTermsCard({ clauses }: { clauses: Clause[] }) {
  const rows = KEY_TERMS.map((term) => {
    const clause = clauses.find(
      (c) => c.subcategory && term.subcategories.includes(c.subcategory)
    );
    const figures = clause
      ? [...clause.extracted_percentages, ...clause.extracted_amounts, ...clause.extracted_time_periods]
      : [];
    return { ...term, clause, figures };
  });

  const identified = rows.filter((row) => row.clause);
  if (identified.length === 0) return null;

  return (
    <Card className="mb-6">
      <CardHeader>
        <CardTitle>Key commercial terms</CardTitle>
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-1 gap-x-8 gap-y-3 sm:grid-cols-2">
          {rows.map((row) => (
            <div
              key={row.label}
              className="flex items-baseline justify-between gap-3 border-b border-[var(--border)] pb-2"
            >
              <dt className="text-sm text-muted-foreground">{row.label}</dt>
              <dd className="text-right text-sm">
                {row.clause ? (
                  <>
                    <span className="font-medium text-foreground">
                      {row.figures.length > 0 ? row.figures.slice(0, 2).join(", ") : "Present"}
                    </span>
                    <span className="ml-2 text-xs text-muted-foreground">
                      {row.clause.clause_number ?? ""}
                    </span>
                  </>
                ) : (
                  <span className="text-muted-foreground">Not identified</span>
                )}
              </dd>
            </div>
          ))}
        </dl>
        <p className="mt-3 text-xs text-muted-foreground">
          Drawn from extracted clause data. &ldquo;Not identified&rdquo; means no clause was
          classified under that term, not that the contract is silent on it.
        </p>
      </CardContent>
    </Card>
  );
}

function ClauseRow({ clause }: { clause: Clause }) {
  const [expanded, setExpanded] = useState(false);

  const { data: detail } = useQuery({
    queryKey: ["clause", clause.id],
    queryFn: () => apiRequest<ClauseDetail>(`/api/clauses/${clause.id}`),
    enabled: expanded,
  });

  return (
    <li className="px-4 py-3 text-sm">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center justify-between text-left"
      >
        <div className="flex items-center gap-2">
          {expanded ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          )}
          <span className="font-medium text-foreground">{clause.clause_number ?? "—"}</span>
          <span className="text-foreground">{clause.title}</span>
        </div>
        <span className="text-xs capitalize text-muted-foreground">
          {clause.subcategory?.replace(/_/g, " ") ?? "uncategorized"}
        </span>
      </button>

      {expanded && (
        <div className="mt-3 rounded-md bg-gray-50 p-3">
          <p className="text-foreground">{clause.text}</p>
          {clause.extraction_error && (
            <p className="mt-2 rounded status-warning border px-2 py-1 text-xs">
              Extraction issue: {clause.extraction_error}
            </p>
          )}
          <dl className="mt-3 grid grid-cols-2 gap-3 text-xs">
            <ExtractedList label="Amounts" items={clause.extracted_amounts} />
            <ExtractedList label="Dates" items={clause.extracted_dates} />
            <ExtractedList label="Percentages" items={clause.extracted_percentages} />
            <ExtractedList label="Time periods" items={clause.extracted_time_periods} />
            <ExtractedList label="Obligations" items={clause.extracted_obligations} />
            <ExtractedList label="Conditions" items={clause.extracted_conditions} />
          </dl>
          {detail && detail.links.length > 0 && (
            <div className="mt-3">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Cross-clause links
              </p>
              <ul className="mt-1 list-inside list-disc text-xs text-foreground">
                {detail.links.map((link) => (
                  <li key={link.id}>
                    {link.relationship_type.replace(/_/g, " ")}{" "}
                    <span className="text-muted-foreground">({link.basis.replace(/_/g, " ")})</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </li>
  );
}

function ExtractedList({ label, items }: { label: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div>
      <dt className="font-medium uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="text-foreground">{items.join(", ")}</dd>
    </div>
  );
}

function StatCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone?: "critical" | "warning";
}) {
  return (
    <Card>
      <CardContent>
        <p className="text-sm text-muted-foreground">{label}</p>
        <p
          className={
            "mt-1 text-3xl font-semibold " +
            (tone === "critical" && value > 0
              ? "text-red-600"
              : tone === "warning" && value > 0
                ? "text-amber-600"
                : "text-foreground")
          }
        >
          {value}
        </p>
      </CardContent>
    </Card>
  );
}
