import type { ExtractionStatus } from "@/lib/types";

interface ExtractionProgressProps {
  status: ExtractionStatus;
  pagesDone: number | null;
  pageCount: number | null;
  error: string | null;
}

/** One line on where text extraction has got to. A scanned contract is
 *  OCR'd at roughly a second per page, so a 200-page scan sits here for a
 *  few minutes; a page count shows it is moving rather than stuck. */
export function ExtractionProgress({ status, pagesDone, pageCount, error }: ExtractionProgressProps) {
  if (status === "failed") {
    return (
      <p className="mt-1 text-xs text-[var(--status-critical-fg)]">
        Text could not be read{error ? `: ${error}` : "."}
      </p>
    );
  }
  if (status === "completed") return null;

  const hasCount = !!pageCount && pageCount > 0;
  const percent = hasCount ? Math.min(100, Math.round(((pagesDone ?? 0) / pageCount) * 100)) : 0;
  return (
    <div className="mt-1">
      <p className="text-xs text-muted-foreground">
        {status === "pending"
          ? "Waiting to read text…"
          : hasCount
            ? `Reading text: page ${pagesDone ?? 0} of ${pageCount}. Scanned pages are read with OCR.`
            : "Reading text…"}
      </p>
      {hasCount && (
        <div className="mt-1 h-1 w-48 max-w-full overflow-hidden rounded-full bg-[var(--status-neutral-bg)]">
          <div
            className="h-full rounded-full bg-primary transition-all duration-500"
            style={{ width: `${percent}%` }}
          />
        </div>
      )}
    </div>
  );
}
