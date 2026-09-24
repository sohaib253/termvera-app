import { cn } from "@/lib/cn";
import type { AssessmentStatusValue, ExtractionStatus, Priority } from "@/lib/types";

const STATUS_CONFIG: Record<AssessmentStatusValue, { label: string; className: string }> = {
  not_assessed: { label: "Not assessed", className: "status-neutral" },
  compliant_looking: { label: "Compliant-looking", className: "status-success" },
  partially_addressed: { label: "Partially addressed", className: "status-warning" },
  evidence_not_found: { label: "Evidence not found", className: "status-critical" },
  potential_non_compliance: { label: "Potential non-compliance", className: "status-critical" },
  not_applicable_pending_verification: {
    label: "N/A — pending verification",
    className: "status-warning",
  },
  human_verified: { label: "Human verified", className: "status-success" },
  human_rejected: { label: "Human rejected", className: "status-critical" },
};

export function AssessmentStatusBadge({ status }: { status: AssessmentStatusValue }) {
  const config = STATUS_CONFIG[status];
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium whitespace-nowrap",
        config.className
      )}
    >
      {config.label}
    </span>
  );
}

// Same fill-weight ramp as ClauseRisk severity (see globals.css), so a
// critical requirement and a critical risk finding read identically.
const PRIORITY_CONFIG: Record<Priority, { label: string; className: string }> = {
  critical: { label: "Critical", className: "severity-critical" },
  high: { label: "High", className: "severity-high" },
  medium: { label: "Medium", className: "severity-medium" },
  low: { label: "Low", className: "severity-low" },
  informational: { label: "Info", className: "severity-info" },
};

export function PriorityBadge({ priority }: { priority: Priority }) {
  const config = PRIORITY_CONFIG[priority];
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium",
        config.className
      )}
    >
      {config.label}
    </span>
  );
}

const EXTRACTION_CONFIG: Record<ExtractionStatus, { label: string; className: string }> = {
  pending: { label: "Pending", className: "status-neutral" },
  processing: { label: "Processing", className: "status-warning" },
  completed: { label: "Completed", className: "status-success" },
  failed: { label: "Failed", className: "status-critical" },
};

export function ExtractionStatusBadge({ status }: { status: ExtractionStatus }) {
  const config = EXTRACTION_CONFIG[status];
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium",
        config.className
      )}
    >
      {config.label}
    </span>
  );
}
