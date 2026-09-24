"use client";

import { useEffect, useState } from "react";

import { cn } from "@/lib/cn";
import type { ContractAnalysisStatusResponse } from "@/lib/types";

/** Progress for a long analysis run.
 *
 *  Shows the stage and a real clause count, plus elapsed time and an
 *  estimate derived from the rate actually observed on this run. No fake
 *  percentage and no estimate until enough clauses have finished to base
 *  one on: a wrong ETA is worse than none when someone is deciding whether
 *  to wait or come back later. */
export function AnalysisProgress({ status }: { status: ContractAnalysisStatusResponse }) {
  const { analysis_stage, analysis_progress_current, analysis_progress_total } = status;
  const hasCount = analysis_progress_total > 0;
  const percent = hasCount
    ? Math.min(100, Math.round((analysis_progress_current / analysis_progress_total) * 100))
    : 0;

  // Elapsed time has to advance on its own: an hour-long run would
  // otherwise show whatever "now" was when the parent last refetched.
  // Reading the clock during render is impure, so tick it in state.
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 30_000);
    return () => clearInterval(id);
  }, []);

  const startedAt = status.analysis_started_at ? new Date(status.analysis_started_at) : null;
  const elapsedMs = startedAt ? now - startedAt.getTime() : 0;
  const remaining = estimateRemaining(elapsedMs, analysis_progress_current, analysis_progress_total);

  return (
    <div className="rounded-md border border-[var(--border)] bg-surface px-4 py-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-sm font-medium text-foreground">
          {analysis_stage ?? "Starting analysis"}
          {hasCount && (
            <span className="ml-2 font-normal text-muted-foreground">
              {analysis_progress_current} of {analysis_progress_total} clauses
            </span>
          )}
        </p>
        <p className="text-xs text-muted-foreground">
          {startedAt && `Running for ${formatDuration(elapsedMs)}`}
          {remaining !== null && ` · about ${formatDuration(remaining)} left`}
        </p>
      </div>

      <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-[var(--status-neutral-bg)]">
        <div
          className={cn(
            "h-full rounded-full bg-primary transition-all duration-500",
            !hasCount && "w-1/4 animate-pulse"
          )}
          style={hasCount ? { width: `${percent}%` } : undefined}
        />
      </div>

      <p className="mt-2 text-xs text-muted-foreground">
        Analysis runs in the background. You can leave this page and come back; progress is saved
        as each clause completes.
      </p>
    </div>
  );
}

function estimateRemaining(elapsedMs: number, current: number, total: number): number | null {
  // Two clauses in is not enough to extrapolate an hour-long run from.
  if (current < 3 || total <= 0 || elapsedMs <= 0) return null;
  const perItem = elapsedMs / current;
  const remainingItems = Math.max(total - current, 0);
  if (remainingItems === 0) return null;
  return perItem * remainingItems;
}

function formatDuration(ms: number): string {
  const minutes = Math.round(ms / 60000);
  if (minutes < 1) return "under a minute";
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest === 0 ? `${hours} hr` : `${hours} hr ${rest} min`;
}
