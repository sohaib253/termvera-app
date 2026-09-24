import { cn } from "@/lib/cn";
import type {
  ContractAnalysisStatus,
  ContractStatus,
  FindingReviewerStatus,
  RiskSeverity,
} from "@/lib/types";

const BADGE_BASE =
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium whitespace-nowrap";

const CONTRACT_STATUS_CONFIG: Record<ContractStatus, { label: string; className: string }> = {
  draft: { label: "Draft", className: "status-neutral" },
  under_review: { label: "Under review", className: "status-warning" },
  active: { label: "Active", className: "status-success" },
  superseded: { label: "Superseded", className: "status-neutral" },
  archived: { label: "Archived", className: "status-neutral" },
};

export function ContractStatusBadge({ status }: { status: ContractStatus }) {
  const config = CONTRACT_STATUS_CONFIG[status];
  return <span className={cn(BADGE_BASE, config.className)}>{config.label}</span>;
}

const ANALYSIS_STATUS_CONFIG: Record<ContractAnalysisStatus, { label: string; className: string }> = {
  not_started: { label: "Not started", className: "status-neutral" },
  processing: { label: "Processing", className: "status-warning" },
  completed: { label: "Completed", className: "status-success" },
  failed: { label: "Failed", className: "status-critical" },
};

export function ContractAnalysisStatusBadge({ status }: { status: ContractAnalysisStatus }) {
  const config = ANALYSIS_STATUS_CONFIG[status];
  return <span className={cn(BADGE_BASE, config.className)}>{config.label}</span>;
}

// Severity is ranked by fill weight rather than hue: a solid chip for
// critical, an outlined red chip for high, then progressively quieter
// indigo/slate. See globals.css for why this is not a red/amber/green scale.
const SEVERITY_CONFIG: Record<RiskSeverity, { label: string; className: string }> = {
  critical: { label: "Critical", className: "severity-critical" },
  high: { label: "High", className: "severity-high" },
  medium: { label: "Medium", className: "severity-medium" },
  low: { label: "Low", className: "severity-low" },
  informational: { label: "Info", className: "severity-info" },
};

export function RiskSeverityBadge({ severity }: { severity: RiskSeverity }) {
  const config = SEVERITY_CONFIG[severity];
  return <span className={cn(BADGE_BASE, config.className)}>{config.label}</span>;
}

const REVIEWER_STATUS_CONFIG: Record<FindingReviewerStatus, { label: string; className: string }> = {
  unreviewed: { label: "Unreviewed", className: "status-neutral" },
  accepted: { label: "Accepted", className: "status-success" },
  rejected: { label: "Rejected", className: "status-critical" },
  marked_for_negotiation: { label: "Negotiate", className: "status-warning" },
  reviewed: { label: "Reviewed", className: "status-success" },
};

export function FindingReviewerStatusBadge({ status }: { status: FindingReviewerStatus }) {
  const config = REVIEWER_STATUS_CONFIG[status];
  return <span className={cn(BADGE_BASE, config.className)}>{config.label}</span>;
}

/** Compact 0-100 risk score with a proportional bar, so a register scans
 *  as a ranked list rather than a column of bare numbers. */
export function RiskScoreBar({ score, severity }: { score: number; severity: RiskSeverity }) {
  const barColor =
    severity === "critical"
      ? "bg-[var(--severity-critical-bg)]"
      : severity === "high"
        ? "bg-[var(--severity-high-fg)]"
        : severity === "medium"
          ? "bg-[var(--severity-medium-fg)]"
          : "bg-[var(--severity-low-fg)]";
  return (
    <div className="flex items-center gap-2">
      <span className="w-7 shrink-0 text-right tabular-nums text-foreground">{Math.round(score)}</span>
      <span className="h-1.5 w-16 shrink-0 overflow-hidden rounded-full bg-[var(--status-neutral-bg)]">
        <span
          className={cn("block h-full rounded-full", barColor)}
          style={{ width: `${Math.max(0, Math.min(100, score))}%` }}
        />
      </span>
    </div>
  );
}
