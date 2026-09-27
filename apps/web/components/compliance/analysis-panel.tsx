"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Play, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { apiRequest, ApiError } from "@/lib/api-client";
import type { AnalysisStatusResponse, Project } from "@/lib/types";
import { routes } from "@/lib/routes";

export function AnalysisPanel({ project }: { project: Project }) {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const { data: status } = useQuery({
    queryKey: ["analysis-status", project.id],
    queryFn: () => apiRequest<AnalysisStatusResponse>(`/api/projects/${project.id}/analysis`),
    initialData: {
      analysis_status: project.analysis_status,
      analysis_error: project.analysis_error,
      analysis_started_at: null,
      analysis_completed_at: null,
    },
    refetchInterval: (query) => (query.state.data?.analysis_status === "processing" ? 2000 : false),
  });

  const runMutation = useMutation({
    mutationFn: () => apiRequest<AnalysisStatusResponse>(`/api/projects/${project.id}/analysis`, { method: "POST" }),
    onSuccess: (data) => {
      queryClient.setQueryData(["analysis-status", project.id], data);
      setError(null);
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : "Could not start analysis.");
    },
  });

  if (project.is_demo) {
    return (
      <div className="flex items-start gap-3 rounded-md status-success border px-4 py-3 text-sm">
        <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" />
        <div>
          <p className="font-medium">Sample results already loaded</p>
          <p className="mt-1">
            This demo project uses precomputed sample results (see Assumptions & Limitations in
            the export) rather than a live AI call. Open the compliance matrix below.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-foreground">
            Status: <span className="capitalize">{status?.analysis_status.replace("_", " ")}</span>
          </p>
          {status?.analysis_status === "processing" && (
            <p className="text-sm text-muted-foreground">
              Extracting requirements and checking the bid against each one. This usually
              finishes within seconds.
            </p>
          )}
        </div>
        <Button
          onClick={() => runMutation.mutate()}
          disabled={runMutation.isPending || status?.analysis_status === "processing"}
        >
          <Play className="h-4 w-4" />
          {status?.analysis_status === "completed" ? "Re-run analysis" : "Run analysis"}
        </Button>
      </div>

      {(error || status?.analysis_error) && (
        <p className="mt-3 rounded-md status-critical border px-3 py-2 text-sm" role="alert">
          {error ?? status?.analysis_error}
        </p>
      )}

      {status?.analysis_status === "completed" && (
        <Link href={routes.projectCompliance(project.id)} className="mt-4 inline-block">
          <Button variant="secondary">View compliance matrix</Button>
        </Link>
      )}
    </div>
  );
}
