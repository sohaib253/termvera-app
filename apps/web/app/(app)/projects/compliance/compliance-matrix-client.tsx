"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Search } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import { AssessmentStatusBadge, PriorityBadge } from "@/components/ui/assessment-badge";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiRequest } from "@/lib/api-client";
import type { AssessmentStatusValue, MandatoryStatus, Priority, Project, Requirement } from "@/lib/types";
import { routes } from "@/lib/routes";

const STATUS_OPTIONS: { value: AssessmentStatusValue; label: string }[] = [
  { value: "compliant_looking", label: "Compliant-looking" },
  { value: "partially_addressed", label: "Partially addressed" },
  { value: "evidence_not_found", label: "Evidence not found" },
  { value: "potential_non_compliance", label: "Potential non-compliance" },
  { value: "not_applicable_pending_verification", label: "N/A — pending verification" },
  { value: "human_verified", label: "Human verified" },
  { value: "human_rejected", label: "Human rejected" },
];

const MANDATORY_OPTIONS: { value: MandatoryStatus; label: string }[] = [
  { value: "mandatory", label: "Mandatory" },
  { value: "conditional", label: "Conditional" },
  { value: "indicative", label: "Indicative" },
  { value: "unclear", label: "Unclear" },
];

const PRIORITY_OPTIONS: { value: Priority; label: string }[] = [
  { value: "critical", label: "Critical" },
  { value: "high", label: "High" },
  { value: "medium", label: "Medium" },
  { value: "low", label: "Low" },
  { value: "informational", label: "Informational" },
];

export function ComplianceMatrixClient({ projectId }: { projectId: string }) {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [mandatoryStatus, setMandatoryStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [reviewerStatus, setReviewerStatus] = useState("");

  const { data: project } = useQuery({
    queryKey: ["projects", projectId],
    queryFn: () => apiRequest<Project>(`/api/projects/${projectId}`),
  });

  const queryString = useMemo(() => {
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    if (status) params.set("status", status);
    if (mandatoryStatus) params.set("mandatory_status", mandatoryStatus);
    if (priority) params.set("priority", priority);
    if (reviewerStatus) params.set("reviewer_status", reviewerStatus);
    const qs = params.toString();
    return qs ? `?${qs}` : "";
  }, [search, status, mandatoryStatus, priority, reviewerStatus]);

  const { data: requirements, isLoading } = useQuery({
    queryKey: ["requirements", projectId, queryString],
    queryFn: () =>
      apiRequest<Requirement[]>(`/api/projects/${projectId}/requirements${queryString}`),
  });

  const criticalCount = requirements?.filter((r) => r.assessment?.priority === "critical").length ?? 0;
  const reviewCount = requirements?.filter((r) => r.assessment?.requires_human_review).length ?? 0;

  return (
    <div className="mx-auto max-w-6xl">
      <Link
        href={routes.project(projectId)}
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to project
      </Link>

      <div className="mb-6 mt-4">
        <h1 className="text-2xl font-semibold text-foreground">Compliance matrix</h1>
        <p className="text-sm text-muted-foreground">{project?.name}</p>
        {project?.is_demo && (
          <p className="mt-2 inline-block rounded-md status-warning border px-3 py-1.5 text-xs">
            Sample data — fictional tender and bid, for demonstration only.
          </p>
        )}
      </div>

      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard label="Total requirements" value={requirements?.length ?? 0} />
        <StatCard label="Critical priority" value={criticalCount} tone="critical" />
        <StatCard label="Requiring human review" value={reviewCount} tone="warning" />
      </div>

      <Card className="mb-4">
        <CardContent>
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative min-w-[220px] flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search clause or requirement text…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <FilterSelect
              value={status}
              onChange={setStatus}
              placeholder="All statuses"
              options={STATUS_OPTIONS}
            />
            <FilterSelect
              value={mandatoryStatus}
              onChange={setMandatoryStatus}
              placeholder="All mandatory levels"
              options={MANDATORY_OPTIONS}
            />
            <FilterSelect
              value={priority}
              onChange={setPriority}
              placeholder="All priorities"
              options={PRIORITY_OPTIONS}
            />
            <FilterSelect
              value={reviewerStatus}
              onChange={setReviewerStatus}
              placeholder="All review states"
              options={[
                { value: "unreviewed", label: "Unreviewed" },
                { value: "reviewed", label: "Reviewed" },
              ]}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="px-5 py-8 text-center text-sm text-muted-foreground">Loading…</div>
          ) : !requirements || requirements.length === 0 ? (
            <div className="px-5 py-12 text-center text-sm text-muted-foreground">
              No requirements match the current filters.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wide text-muted-foreground">
                    <th className="px-4 py-3 font-medium">Clause</th>
                    <th className="px-4 py-3 font-medium">Requirement</th>
                    <th className="px-4 py-3 font-medium">Category</th>
                    <th className="px-4 py-3 font-medium">Mandatory</th>
                    <th className="px-4 py-3 font-medium">Status</th>
                    <th className="px-4 py-3 font-medium">Priority</th>
                    <th className="px-4 py-3 font-medium">Review</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)]">
                  {requirements.map((req) => (
                    <tr key={req.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <Link
                          href={routes.requirement(projectId, req.id)}
                          className="font-medium text-primary hover:underline"
                        >
                          {req.source_clause ?? "—"}
                        </Link>
                      </td>
                      <td className="max-w-xs px-4 py-3">
                        <Link href={routes.requirement(projectId, req.id)} className="hover:underline">
                          {req.title}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">{req.category}</td>
                      <td className="px-4 py-3 capitalize text-muted-foreground">{req.mandatory_status}</td>
                      <td className="px-4 py-3">
                        {req.assessment ? (
                          <AssessmentStatusBadge status={req.assessment.status} />
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {req.assessment ? <PriorityBadge priority={req.assessment.priority} /> : "—"}
                      </td>
                      <td className="px-4 py-3 capitalize text-muted-foreground">
                        {req.assessment?.reviewer_status ?? "—"}
                      </td>
                    </tr>
                  ))}
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

function FilterSelect({
  value,
  onChange,
  placeholder,
  options,
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  options: { value: string; label: string }[];
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="h-10 rounded-md border border-[var(--border)] bg-white px-3 text-sm text-foreground"
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
