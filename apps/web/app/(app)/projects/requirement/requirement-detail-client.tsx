"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ExternalLink, History } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { AssessmentStatusBadge, PriorityBadge } from "@/components/ui/assessment-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { apiRequest, ApiError, openDocumentFile } from "@/lib/api-client";
import type { AssessmentStatusValue, RequirementDetail, ReviewActionInput } from "@/lib/types";
import { routes } from "@/lib/routes";

const REVIEW_STATUS_OPTIONS: { value: AssessmentStatusValue; label: string }[] = [
  { value: "compliant_looking", label: "Compliant-looking" },
  { value: "partially_addressed", label: "Partially addressed" },
  { value: "evidence_not_found", label: "Evidence not found" },
  { value: "potential_non_compliance", label: "Potential non-compliance" },
  { value: "not_applicable_pending_verification", label: "N/A — pending verification" },
  { value: "human_verified", label: "Human verified (confirm as-is)" },
  { value: "human_rejected", label: "Human rejected (override)" },
];

const schema = z.object({
  new_status: z.string().optional(),
  comment: z.string().max(4000).optional(),
});
type FormValues = z.infer<typeof schema>;

export function RequirementDetailClient({
  projectId,
  requirementId,
}: {
  projectId: string;
  requirementId: string;
}) {
  const queryClient = useQueryClient();
  const [reviewError, setReviewError] = useState<string | null>(null);

  const { data: requirement, isLoading } = useQuery({
    queryKey: ["requirement", requirementId],
    queryFn: () => apiRequest<RequirementDetail>(`/api/requirements/${requirementId}`),
  });

  const { register, handleSubmit, reset } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const reviewMutation = useMutation({
    mutationFn: (input: ReviewActionInput) =>
      apiRequest<RequirementDetail>(`/api/requirements/${requirementId}/review`, {
        method: "POST",
        body: input,
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["requirement", requirementId], updated);
      queryClient.invalidateQueries({ queryKey: ["requirements", projectId] });
      setReviewError(null);
      reset();
    },
    onError: (err) => {
      setReviewError(err instanceof ApiError ? err.message : "Could not save the review.");
    },
  });

  const onSubmit = (values: FormValues) => {
    reviewMutation.mutate({
      new_status: values.new_status ? (values.new_status as AssessmentStatusValue) : undefined,
      comment: values.comment || undefined,
    });
  };

  const openSource = (documentId: string, page: number) => {
    openDocumentFile(`/api/projects/${projectId}/documents/${documentId}/file`, page).catch(() => {
      /* best-effort — opening the source document is a convenience, not critical path */
    });
  };

  if (isLoading) return <div className="text-sm text-muted-foreground">Loading…</div>;
  if (!requirement) {
    return (
      <div className="mx-auto max-w-3xl">
        <BackLink projectId={projectId} />
        <p className="mt-4 rounded-md status-critical border px-4 py-3 text-sm">Requirement not found.</p>
      </div>
    );
  }

  const assessment = requirement.assessment;

  return (
    <div className="mx-auto max-w-3xl pb-16">
      <BackLink projectId={projectId} />

      <div className="mb-6 mt-4 flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-primary">{requirement.source_clause}</p>
          <h1 className="text-2xl font-semibold text-foreground">{requirement.title}</h1>
        </div>
        <div className="flex flex-col items-end gap-2">
          {assessment && <AssessmentStatusBadge status={assessment.status} />}
          {assessment && <PriorityBadge priority={assessment.priority} />}
        </div>
      </div>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Requirement</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="mb-3 text-sm text-foreground">{requirement.normalized_requirement}</p>
          <dl className="grid grid-cols-2 gap-4 text-sm">
            <Field label="Category" value={requirement.category} />
            <Field label="Mandatory status" value={requirement.mandatory_status} />
            <Field label="Conditions" value={requirement.conditions} />
            <Field label="Required evidence" value={requirement.required_evidence} />
          </dl>
          <div className="mt-4 rounded-md bg-gray-50 p-3 text-sm">
            <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Source excerpt — page {requirement.source_page}
            </p>
            <p className="text-foreground">&ldquo;{requirement.source_excerpt}&rdquo;</p>
            <button
              type="button"
              onClick={() => openSource(requirement.source_document_id, requirement.source_page)}
              className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
            >
              <ExternalLink className="h-3 w-3" />
              Open source document
            </button>
          </div>
        </CardContent>
      </Card>

      {assessment && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Assessment</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-foreground">{assessment.reason}</p>
            <dl className="mt-4 grid grid-cols-2 gap-4 text-sm">
              <Field label="Evidence quality" value={assessment.evidence_quality} />
              <Field label="Assessment confidence" value={assessment.assessment_confidence} />
              <Field label="Requires human review" value={assessment.requires_human_review ? "Yes" : "No"} />
              <Field label="AI provider" value={assessment.ai_provider ?? "Sample data"} />
            </dl>
            {assessment.missing_information.length > 0 && (
              <div className="mt-4">
                <Label>Missing information</Label>
                <ul className="list-inside list-disc text-sm text-foreground">
                  {assessment.missing_information.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Evidence</CardTitle>
        </CardHeader>
        <CardContent>
          {requirement.evidence_records.length === 0 ? (
            <p className="rounded-md status-critical border px-3 py-2 text-sm">
              Evidence not located in the provided documents.
            </p>
          ) : (
            <ul className="space-y-3">
              {requirement.evidence_records.map((ev) => (
                <li key={ev.id} className="rounded-md border border-[var(--border)] p-3 text-sm">
                  <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    Page {ev.page_number} · {ev.evidence_type ?? "evidence"}
                  </p>
                  <p className="text-foreground">&ldquo;{ev.excerpt}&rdquo;</p>
                  {ev.relevance_note && (
                    <p className="mt-2 text-muted-foreground">{ev.relevance_note}</p>
                  )}
                  {ev.potential_conflict && (
                    <p className="mt-2 rounded status-warning border px-2 py-1 text-xs">
                      Potential conflict: {ev.potential_conflict}
                    </p>
                  )}
                  <button
                    type="button"
                    onClick={() => openSource(ev.document_id, ev.page_number)}
                    className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                  >
                    <ExternalLink className="h-3 w-3" />
                    Open source document
                  </button>
                </li>
              ))}
            </ul>
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
                placeholder="Explain your override or add a note for the team…"
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
          {requirement.review_actions.length === 0 ? (
            <p className="text-sm text-muted-foreground">No review actions recorded yet.</p>
          ) : (
            <ul className="space-y-3">
              {[...requirement.review_actions].reverse().map((action) => (
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

function BackLink({ projectId }: { projectId: string }) {
  return (
    <Link
      href={routes.projectCompliance(projectId)}
      className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
    >
      <ArrowLeft className="h-4 w-4" />
      Back to compliance matrix
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
