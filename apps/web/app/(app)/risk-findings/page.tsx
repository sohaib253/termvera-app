"use client";

import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import { Card, CardContent } from "@/components/ui/card";
import {
  FindingReviewerStatusBadge,
  RiskScoreBar,
  RiskSeverityBadge,
} from "@/components/ui/clauserisk-badge";
import { Input } from "@/components/ui/input";
import { apiRequest } from "@/lib/api-client";
import { RISK_CATEGORIES } from "@/lib/clauserisk-categories";
import { findingTitle } from "@/lib/risk-finding-display";
import type { FindingReviewerStatus, RiskFindingListItem, RiskSeverity } from "@/lib/types";
import { routes } from "@/lib/routes";

const SEVERITY_OPTIONS: { value: RiskSeverity; label: string }[] = [
  { value: "critical", label: "Critical" },
  { value: "high", label: "High" },
  { value: "medium", label: "Medium" },
  { value: "low", label: "Low" },
  { value: "informational", label: "Informational" },
];

const REVIEWER_STATUS_OPTIONS: { value: FindingReviewerStatus; label: string }[] = [
  { value: "unreviewed", label: "Unreviewed" },
  { value: "accepted", label: "Accepted" },
  { value: "rejected", label: "Rejected" },
  { value: "marked_for_negotiation", label: "Marked for negotiation" },
  { value: "reviewed", label: "Reviewed" },
];

export default function RiskRegisterPage() {
  const [search, setSearch] = useState("");
  const [severity, setSeverity] = useState("");
  const [category, setCategory] = useState("");
  const [reviewerStatus, setReviewerStatus] = useState("");
  const [contractId, setContractId] = useState("");

  const queryString = useMemo(() => {
    const params = new URLSearchParams();
    if (severity) params.set("severity", severity);
    if (category) params.set("category", category);
    if (reviewerStatus) params.set("reviewer_status", reviewerStatus);
    const qs = params.toString();
    return qs ? `?${qs}` : "";
  }, [severity, category, reviewerStatus]);

  const { data: findings, isLoading } = useQuery({
    queryKey: ["risk-findings", "register", queryString],
    queryFn: () => apiRequest<RiskFindingListItem[]>(`/api/risk-findings${queryString}`),
  });

  // Contract filter and free-text search run client-side: the register is a
  // reviewer's working set (tens to low hundreds of rows), and keeping them
  // local means typing stays instant instead of refetching per keystroke.
  const contractOptions = useMemo(() => {
    const seen = new Map<string, string>();
    for (const finding of findings ?? []) {
      seen.set(finding.contract_id, finding.contract_name);
    }
    return [...seen.entries()].map(([value, label]) => ({ value, label }));
  }, [findings]);

  const visible = useMemo(() => {
    const term = search.trim().toLowerCase();
    return (findings ?? []).filter((finding) => {
      if (contractId && finding.contract_id !== contractId) return false;
      if (!term) return true;
      return [
        finding.risk_type_label,
        finding.risk_description,
        finding.clause_number ?? "",
        finding.contract_name,
        finding.potential_exposure ?? "",
      ]
        .join(" ")
        .toLowerCase()
        .includes(term);
    });
  }, [findings, search, contractId]);

  const criticalCount = visible.filter((f) => f.severity === "critical").length;
  const highCount = visible.filter((f) => f.severity === "high").length;
  const unreviewedCount = visible.filter((f) => f.reviewer_status === "unreviewed").length;

  return (
    <div className="mx-auto max-w-7xl">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-foreground">Risk register</h1>
        <p className="text-sm text-muted-foreground">
          Every risk finding across your contracts, ranked by computed risk score.
        </p>
      </div>

      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Findings shown" value={visible.length} />
        <StatCard label="Critical" value={criticalCount} emphasis={criticalCount > 0} />
        <StatCard label="High" value={highCount} emphasis={highCount > 0} />
        <StatCard label="Unreviewed" value={unreviewedCount} emphasis={unreviewedCount > 0} />
      </div>

      <Card className="mb-4">
        <CardContent>
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative min-w-[240px] flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search risk, clause, or exposure…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <FilterSelect
              value={contractId}
              onChange={setContractId}
              placeholder="All contracts"
              options={contractOptions}
            />
            <FilterSelect
              value={severity}
              onChange={setSeverity}
              placeholder="All severities"
              options={SEVERITY_OPTIONS}
            />
            <FilterSelect
              value={category}
              onChange={setCategory}
              placeholder="All categories"
              options={RISK_CATEGORIES.map((c) => ({ value: c, label: c }))}
              capitalize
            />
            <FilterSelect
              value={reviewerStatus}
              onChange={setReviewerStatus}
              placeholder="All review states"
              options={REVIEWER_STATUS_OPTIONS}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="px-5 py-8 text-center text-sm text-muted-foreground">Loading…</div>
          ) : visible.length === 0 ? (
            <div className="px-5 py-12 text-center text-sm text-muted-foreground">
              No risk findings match the current filters.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wide text-muted-foreground">
                    <th className="px-4 py-3 font-medium">Risk</th>
                    <th className="px-4 py-3 font-medium">Contract</th>
                    <th className="px-4 py-3 font-medium">Clause</th>
                    <th className="px-4 py-3 font-medium">Category</th>
                    <th className="px-4 py-3 font-medium">Exposure</th>
                    <th className="px-4 py-3 font-medium">Severity</th>
                    <th className="px-4 py-3 font-medium">Score</th>
                    <th className="px-4 py-3 font-medium">Review</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)]">
                  {visible.map((finding) => {
                    const { title, subtitle } = findingTitle(finding);
                    return (
                    <tr key={finding.id} className="hover:bg-gray-50">
                      <td className="max-w-sm px-4 py-3">
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
                      <td className="px-4 py-3">
                        <Link
                          href={routes.contract(finding.contract_id)}
                          className="text-muted-foreground hover:underline"
                        >
                          {finding.contract_name}
                        </Link>
                      </td>
                      <td className="px-4 py-3 tabular-nums text-muted-foreground">
                        {finding.clause_number ?? "—"}
                      </td>
                      <td className="px-4 py-3 capitalize text-muted-foreground">
                        {finding.category.replace(/_/g, " ")}
                      </td>
                      <td className="max-w-[14rem] px-4 py-3 text-muted-foreground">
                        <span className="line-clamp-1">{finding.potential_exposure || "—"}</span>
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
    </div>
  );
}

function StatCard({
  label,
  value,
  emphasis,
}: {
  label: string;
  value: number;
  emphasis?: boolean;
}) {
  return (
    <Card>
      <CardContent>
        <p className="text-sm text-muted-foreground">{label}</p>
        <p
          className={
            "mt-1 text-3xl font-semibold tabular-nums " +
            (emphasis ? "text-[var(--severity-high-fg)]" : "text-foreground")
          }
        >
          {value}
        </p>
      </CardContent>
    </Card>
  );
}

function FilterSelect({
  value,
  onChange,
  placeholder,
  options,
  capitalize,
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  options: { value: string; label: string }[];
  capitalize?: boolean;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={
        "h-10 max-w-[13rem] rounded-md border border-[var(--border)] bg-white px-3 text-sm text-foreground " +
        (capitalize ? "capitalize" : "")
      }
    >
      <option value="">{placeholder}</option>
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  );
}
