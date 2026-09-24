import { cn } from "@/lib/cn";
import type { ProjectStatus } from "@/lib/types";

const STATUS_CONFIG: Record<ProjectStatus, { label: string; className: string }> = {
  draft: { label: "Draft", className: "status-neutral" },
  active: { label: "Active", className: "status-warning" },
  submitted: { label: "Submitted", className: "status-success" },
  archived: { label: "Archived", className: "status-neutral" },
};

export function ProjectStatusBadge({ status }: { status: ProjectStatus }) {
  const config = STATUS_CONFIG[status];
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
