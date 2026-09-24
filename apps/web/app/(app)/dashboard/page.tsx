"use client";

import { useQuery } from "@tanstack/react-query";
import { CalendarClock, FileSignature, FileText, Plus } from "lucide-react";
import Link from "next/link";

import { LoadDemoContractButton } from "@/components/clauserisk/load-demo-contract-button";
import { LoadDemoButton } from "@/components/compliance/load-demo-button";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { RiskSeverityBadge } from "@/components/ui/clauserisk-badge";
import { cn } from "@/lib/cn";
import { apiRequest } from "@/lib/api-client";
import { RISK_SEVERITY_ORDER, type DashboardSummary, type UpcomingDeadline } from "@/lib/types";

export default function DashboardPage() {
  const { data: summary, isLoading } = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: () => apiRequest<DashboardSummary>("/api/dashboard/summary"),
  });

  const hasNothing =
    !isLoading && summary && summary.projects_total === 0 && summary.contracts_total === 0;

  return (
    <div className="mx-auto max-w-6xl">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Dashboard</h1>
          <p className="text-sm text-muted-foreground">
            What closes soonest, what needs your decision, and where the risk sits.
          </p>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-3">
          <Link href="/projects">
            <Button variant="secondary">
              <FileText className="h-4 w-4" />
              New tender review
            </Button>
          </Link>
          <Link href="/contracts/new">
            <Button>
              <Plus className="h-4 w-4" />
              New contract review
            </Button>
          </Link>
        </div>
      </div>

      {hasNothing ? (
        <EmptyState />
      ) : (
        <>
          <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
            <ActionStat
              label="Requirements awaiting review"
              value={summary?.requirements_awaiting_review}
              loading={isLoading}
              emphasis={(summary?.requirements_awaiting_review ?? 0) > 0}
            />
            <ActionStat
              label="Critical requirements open"
              value={summary?.critical_requirements}
              loading={isLoading}
              emphasis={(summary?.critical_requirements ?? 0) > 0}
            />
            <ActionStat
              label="Risk findings unreviewed"
              value={summary?.findings_unreviewed}
              loading={isLoading}
              emphasis={(summary?.findings_unreviewed ?? 0) > 0}
              href="/risk-findings?reviewer_status=unreviewed"
            />
            <ActionStat
              label="Deadlines passed"
              value={summary?.overdue_deadlines}
              loading={isLoading}
              emphasis={(summary?.overdue_deadlines ?? 0) > 0}
            />
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Card>
              <CardContent className="p-0">
                <SectionHeader
                  title="Submission deadlines"
                  hint="Open tenders, soonest first"
                  href="/projects"
                />
                {isLoading ? (
                  <Loading />
                ) : !summary || summary.upcoming_deadlines.length === 0 ? (
                  <Empty text="No upcoming submission deadlines on open tenders." />
                ) : (
                  <ul className="divide-y divide-[var(--border)]">
                    {summary.upcoming_deadlines.map((deadline) => (
                      <DeadlineRow key={deadline.project_id} deadline={deadline} />
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-0">
                <SectionHeader
                  title="Contract risk exposure"
                  hint={
                    summary
                      ? `${summary.contracts_analyzed}/${summary.contracts_total} contracts analyzed`
                      : undefined
                  }
                  href="/risk-findings"
                />
                {isLoading ? (
                  <Loading />
                ) : !summary || summary.contracts_total === 0 ? (
                  <Empty text="No contracts added yet." />
                ) : (
                  <SeverityBreakdown counts={summary.findings_by_severity} />
                )}
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}

function DeadlineRow({ deadline }: { deadline: UpcomingDeadline }) {
  const days = deadline.days_remaining;
  // Urgency by weight, not by a traffic-light colour: the closest deadline
  // should stand out without implying the others are "safe".
  const urgency =
    days <= 3
      ? "severity-critical"
      : days <= 7
        ? "severity-high"
        : days <= 14
          ? "severity-medium"
          : "severity-low";

  return (
    <li>
      <Link
        href={`/projects/${deadline.project_id}`}
        className="flex items-center justify-between gap-4 px-5 py-4 hover:bg-gray-50"
      >
        <div className="min-w-0">
          <p className="truncate font-medium text-foreground">{deadline.name}</p>
          <p className="text-sm text-muted-foreground">
            {deadline.client_name ?? "No client specified"}
            {` · closes ${new Date(deadline.submission_deadline).toLocaleDateString()}`}
          </p>
        </div>
        <span
          className={cn(
            "shrink-0 rounded-full border px-2.5 py-0.5 text-xs font-medium whitespace-nowrap",
            urgency
          )}
        >
          {days === 0 ? "Closes today" : days === 1 ? "1 day left" : `${days} days left`}
        </span>
      </Link>
    </li>
  );
}

function SeverityBreakdown({ counts }: { counts: Record<string, number> }) {
  const total = RISK_SEVERITY_ORDER.reduce((sum, key) => sum + (counts[key] ?? 0), 0);

  if (total === 0) {
    return <Empty text="No risk findings yet. Run analysis on a contract version." />;
  }

  return (
    <ul className="divide-y divide-[var(--border)]">
      {RISK_SEVERITY_ORDER.map((severity) => {
        const count = counts[severity] ?? 0;
        const share = total === 0 ? 0 : (count / total) * 100;
        return (
          <li key={severity} className="flex items-center gap-4 px-5 py-3">
            <span className="w-20 shrink-0">
              <RiskSeverityBadge severity={severity} />
            </span>
            <span className="h-2 flex-1 overflow-hidden rounded-full bg-[var(--status-neutral-bg)]">
              <span
                className={cn(
                  "block h-full rounded-full",
                  severity === "critical"
                    ? "bg-[var(--severity-critical-bg)]"
                    : severity === "high"
                      ? "bg-[var(--severity-high-fg)]"
                      : severity === "medium"
                        ? "bg-[var(--severity-medium-fg)]"
                        : "bg-[var(--severity-low-fg)]"
                )}
                style={{ width: `${share}%` }}
              />
            </span>
            <span className="w-8 shrink-0 text-right text-sm tabular-nums text-foreground">
              {count}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

function ActionStat({
  label,
  value,
  loading,
  emphasis,
  href,
}: {
  label: string;
  value: number | undefined;
  loading: boolean;
  emphasis: boolean;
  href?: string;
}) {
  const content = (
    <CardContent>
      <p className="text-sm text-muted-foreground">{label}</p>
      <p
        className={cn(
          "mt-1 text-3xl font-semibold tabular-nums",
          emphasis ? "text-[var(--severity-high-fg)]" : "text-foreground"
        )}
      >
        {loading ? "–" : (value ?? 0)}
      </p>
    </CardContent>
  );

  if (href) {
    return (
      <Link href={href}>
        <Card className="h-full transition-colors hover:border-[var(--severity-medium-border)]">
          {content}
        </Card>
      </Link>
    );
  }
  return <Card className="h-full">{content}</Card>;
}

function SectionHeader({
  title,
  hint,
  href,
}: {
  title: string;
  hint?: string;
  href: string;
}) {
  return (
    <div className="flex items-center justify-between border-b border-[var(--border)] px-5 py-4">
      <div>
        <h2 className="text-sm font-semibold text-foreground">{title}</h2>
        {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
      </div>
      <Link href={href} className="text-xs font-medium text-primary hover:underline">
        View all
      </Link>
    </div>
  );
}

function Loading() {
  return <div className="px-5 py-8 text-center text-sm text-muted-foreground">Loading…</div>;
}

function Empty({ text }: { text: string }) {
  return <div className="px-5 py-10 text-center text-sm text-muted-foreground">{text}</div>;
}

function EmptyState() {
  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
      <Card>
        <CardContent className="flex flex-col items-center px-5 py-12 text-center">
          <FileText className="h-9 w-9 text-muted-foreground" />
          <h3 className="mt-4 text-sm font-semibold text-foreground">Start a tender review</h3>
          <p className="mt-1 max-w-xs text-sm text-muted-foreground">
            Upload a tender package and your draft bid to build an evidence-backed compliance
            matrix before you submit.
          </p>
          <div className="mt-4 flex flex-wrap items-center justify-center gap-3">
            <Link href="/projects">
              <Button size="sm">
                <Plus className="h-4 w-4" />
                New tender review
              </Button>
            </Link>
            <LoadDemoButton />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="flex flex-col items-center px-5 py-12 text-center">
          <FileSignature className="h-9 w-9 text-muted-foreground" />
          <h3 className="mt-4 text-sm font-semibold text-foreground">Review a contract</h3>
          <p className="mt-1 max-w-xs text-sm text-muted-foreground">
            Upload a contract PDF to get clause-by-clause risk scoring, cross-clause analysis, and
            version comparison.
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
        </CardContent>
      </Card>

      <Card className="md:col-span-2">
        <CardContent className="flex items-center gap-3 text-sm text-muted-foreground">
          <CalendarClock className="h-4 w-4 shrink-0" />
          Once a tender has a submission deadline, it appears here ranked by how soon it closes.
        </CardContent>
      </Card>
    </div>
  );
}
