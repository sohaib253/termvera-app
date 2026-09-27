"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ExternalLink, History } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FindingReviewerStatusBadge, RiskSeverityBadge } from "@/components/ui/clauserisk-badge";
import { Label } from "@/components/ui/label";
import { apiRequest, ApiError, openDocumentFile } from "@/lib/api-client";
import { findingTitle } from "@/lib/risk-finding-display";
import type { FindingReviewerStatus, RiskEvidenceItem, RiskFindingDetail } from "@/lib/types";

const REVIEW_STATUS_OPTIONS: { value: FindingReviewerStatus; label: string }[] = [
  { value: "accepted", label: "Accepted (risk understood, no action needed)" },
  { value: "rejected", label: "Rejected (finding doesn't apply)" },
  { value: "marked_for_negotiation", label: "Marked for negotiation" },
  { value: "reviewed", label: "Reviewed (no status change)" },
];

const schema = z.object({
  new_status: z.string().optional(),
  comment: z.string().max(4000).optional(),
});
type FormValues = z.infer<typeof schema>;

export function RiskFindingDetailClient({ findingId }: { findingId: string }) {
  const queryClient = useQueryClient();
  const [reviewError, setReviewError] = useState<string | null>(null);

  const { data: finding, isLoading } = useQuery({
    queryKey: ["risk-finding", findingId],
    queryFn: () => apiRequest<RiskFindingDetail>(`/api/risk-findings/${findingId}`),
  });

  const { register, handleSubmit, reset } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const reviewMutation = useMutation({
    mutationFn: (input: { new_status?: FindingReviewerStatus; comment?: string }) =>
      apiRequest<RiskFindingDetail>(`/api/risk-findings/${findingId}/review`, {
        method: "POST",
        body: input,
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["risk-finding", findingId], updated);
      queryClient.invalidateQueries({ queryKey: ["risk-findings"] });
      setReviewError(null);
      reset();
    },
    onError: (err) => {
      setReviewError(err instanceof ApiError ? err.message : "Could not save the review.");
    },
  });

  const onSubmit = (values: FormValues) => {
    reviewMutation.mutate({
      new_status: values.new_status ? (values.new_status as FindingReviewerStatus) : undefined,
      comment: values.comment || undefined,
    });
  };

  if (isLoading) return <div className="text-sm text-muted-foreground">Loading…</div>;
  if (!finding) {
    return (
      <div className="mx-auto max-w-3xl">
        <BackLink />
        <p className="mt-4 rounded-md status-critical border px-4 py-3 text-sm">Risk finding not found.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl pb-16">
      <BackLink />

      <div className="mb-6 mt-4 flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium capitalize text-primary">{finding.category.replace(/_/g, " ")}</p>
          <h1 className="text-2xl font-semibold text-foreground">{findingTitle(finding).title}</h1>
        </div>
        <div className="flex flex-col items-end gap-2">
          <RiskSeverityBadge severity={finding.severity} />
          <FindingReviewerStatusBadge status={finding.reviewer_status} />
        </div>
      </div>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Risk description</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-foreground">{finding.risk_description}</p>
          <dl className="mt-4 grid grid-cols-2 gap-4 text-sm">
            <Field label="Contractual effect" value={finding.contractual_effect} />
            <Field label="Potential exposure" value={finding.potential_exposure} />
            <Field label="Trigger" value={finding.trigger} />
            <Field label="Affected party" value={finding.affected_party} />
            <Field label="Uncertainty" value={finding.uncertainty} />
            <Field label="Computed score" value={String(finding.computed_score)} />
          </dl>
          {finding.recommended_review_action && (
            <div className="mt-4">
              <Label>Recommended review action</Label>
              <p className="text-sm text-foreground">{finding.recommended_review_action}</p>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Scoring factors</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="mb-3 text-xs text-muted-foreground">
            The severity and score above are computed deterministically from these factors, not
            asserted directly by the AI model.
          </p>
          <dl className="grid grid-cols-2 gap-2 text-sm">
            {Object.entries(finding.risk_factors).map(([key, value]) => (
              <div key={key} className="flex justify-between gap-2 rounded bg-gray-50 px-2 py-1">
                <dt className="text-muted-foreground">{key.replace(/_/g, " ")}</dt>
                <dd className="font-medium text-foreground">{String(value)}</dd>
              </div>
            ))}
          </dl>
        </CardContent>
      </Card>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Evidence</CardTitle>
        </CardHeader>
        <CardContent>
          {finding.evidence.length === 0 ? (
            <p className="rounded-md status-critical border px-3 py-2 text-sm">
              No verbatim evidence could be confirmed against the source document for this
              finding — treat it as unverified.
            </p>
          ) : (
            <ul className="space-y-3">
              {finding.evidence.map((ev, idx) => (
                <li key={idx} className="rounded-md border border-[var(--border)] p-3 text-sm">
                  <EvidenceWhere
                    evidence={ev}
                    onOpen={
                      ev.page != null
                        ? () =>
                            openDocumentFile(
                              `/api/contract-versions/${finding.contract_version_id}/file`,
                              ev.page ?? undefined
                            ).catch(() => setReviewError("Could not open the contract file."))
                        : undefined
                    }
                  />
                  <blockquote className="border-l-2 border-primary/40 pl-3 text-foreground">
                    &ldquo;{ev.excerpt}&rdquo;
                  </blockquote>
                  {!ev.verified && (
                    <p className="mt-2 rounded status-warning border px-2 py-1 text-xs">
                      Could not be verified verbatim against the source text.
                    </p>
                  )}
                </li>
              ))}
            </ul>
          )}
          {finding.related_clauses.length > 0 && (
            <div className="mt-4">
              <Label>Related clauses</Label>
              <p className="text-sm text-foreground">{finding.related_clauses.join(", ")}</p>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Review</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <Label htmlFor="new_status">Change status (optional)</Label>
              <select
                id="new_status"
                {...register("new_status")}
                className="h-10 w-full rounded-md border border-[var(--border)] bg-white px-3 text-sm"
              >
                <option value="">Keep current status</option>
                {REVIEW_STATUS_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <Label htmlFor="comment">Comment</Label>
              <textarea
                id="comment"
                {...register("comment")}
                rows={3}
                placeholder="Add negotiation notes or context for the team…"
                className="w-full rounded-md border border-[var(--border)] bg-white px-3 py-2 text-sm"
              />
            </div>
            {reviewError && (
              <p className="rounded-md status-critical border px-3 py-2 text-sm" role="alert">
                {reviewError}
              </p>
            )}
            <Button type="submit" disabled={reviewMutation.isPending}>
              {reviewMutation.isPending ? "Saving…" : "Save review"}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>
            <span className="flex items-center gap-2">
              <History className="h-4 w-4" />
              Audit history
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {finding.review_actions.length === 0 ? (
            <p className="text-sm text-muted-foreground">No review actions recorded yet.</p>
          ) : (
            <ul className="space-y-3">
              {[...finding.review_actions].reverse().map((action) => (
                <li key={action.id} className="border-l-2 border-[var(--border)] pl-3 text-sm">
                  <p className="text-xs text-muted-foreground">
                    {new Date(action.created_at).toLocaleString()}
                  </p>
                  {action.new_status && (
                    <p className="text-foreground">
                      Status changed{action.previous_status ? ` from ${action.previous_status}` : ""} to{" "}
                      <strong>{action.new_status}</strong>
                    </p>
                  )}
                  {action.comment && <p className="mt-1 text-foreground">{action.comment}</p>}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function BackLink() {
  return (
    <Link href="/risk-findings" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
      <ArrowLeft className="h-4 w-4" />
      Back to risk register
    </Link>
  );
}

function Field({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="capitalize text-foreground">{value?.replace(/_/g, " ") || "—"}</dd>
    </div>
  );
}

/** Where the quoted evidence is, three ways a reader can find it: the
 *  section and clause, the page number printed on the page, and the PDF
 *  page a viewer shows (they differ when a cover letter comes first). */
function EvidenceWhere({ evidence, onOpen }: { evidence: RiskEvidenceItem; onOpen?: () => void }) {
  const clause = evidence.clause_number
    ? `Clause ${evidence.clause_number}${evidence.clause_title && evidence.clause_title !== evidence.section_title ? ` · ${evidence.clause_title}` : ""}`
    : null;
  const section =
    evidence.section_title && evidence.clause_number
      ? `Section ${evidence.clause_number.split(".")[0]} · ${evidence.section_title}`
      : null;
  const printed = evidence.page_label ? `printed page ${evidence.page_label}` : null;
  const pdf = evidence.page != null ? `PDF page ${evidence.page}` : null;

  return (
    <div className="mb-2 flex flex-wrap items-start justify-between gap-2">
      <div className="min-w-0">
        {(section || clause) && (
          <p className="font-medium text-foreground">
            {section && clause && evidence.clause_number?.includes(".") ? `${section} › ${clause}` : clause ?? section}
          </p>
        )}
        {(printed || pdf) && (
          <p className="text-xs text-muted-foreground">
            {[printed, pdf].filter(Boolean).join(" · ")}
            {printed && pdf ? " (the page number in your PDF viewer)" : ""}
          </p>
        )}
      </div>
      {onOpen && (
        <button
          type="button"
          onClick={onOpen}
          className="inline-flex shrink-0 items-center gap-1 rounded-md border border-[var(--border)] px-2 py-1 text-xs font-medium text-primary hover:bg-gray-50"
        >
          <ExternalLink className="h-3.5 w-3.5" />
          Open at this page
        </button>
      )}
    </div>
  );
}
