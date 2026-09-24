"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Download, Trash2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useAuth } from "@/lib/auth-context";

import { AnalysisPanel } from "@/components/compliance/analysis-panel";
import { ContractsPanel } from "@/components/clauserisk/contracts-panel";
import { DocumentUploadPanel } from "@/components/documents/document-upload-panel";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { ProjectStatusBadge } from "@/components/ui/status-badge";
import { apiRequest, ApiError, downloadFile } from "@/lib/api-client";
import type { Project, ProjectStatus } from "@/lib/types";

const STATUS_OPTIONS: ProjectStatus[] = ["draft", "active", "submitted", "archived"];

export function ProjectDetailClient({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();
  const router = useRouter();
  const { me } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  const deleteMutation = useMutation({
    mutationFn: () => apiRequest<void>(`/api/projects/${projectId}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      queryClient.invalidateQueries({ queryKey: ["contracts"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      router.push("/projects");
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : "Could not delete the project.");
    },
  });

  const handleExport = async () => {
    setIsExporting(true);
    setExportError(null);
    try {
      await downloadFile(
        `/api/projects/${projectId}/exports/compliance-matrix.xlsx`,
        "compliance-matrix.xlsx"
      );
    } catch (err) {
      setExportError(err instanceof ApiError ? err.message : "Export failed.");
    } finally {
      setIsExporting(false);
    }
  };

  const { data: project, isLoading, error: fetchError } = useQuery({
    queryKey: ["projects", projectId],
    queryFn: () => apiRequest<Project>(`/api/projects/${projectId}`),
  });

  const statusMutation = useMutation({
    mutationFn: (status: ProjectStatus) =>
      apiRequest<Project>(`/api/projects/${projectId}`, { method: "PATCH", body: { status } }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["projects", projectId], updated);
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      setError(null);
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : "Could not update status.");
    },
  });

  if (isLoading) {
    return <div className="text-sm text-muted-foreground">Loading…</div>;
  }

  if (fetchError || !project) {
    return (
      <div className="mx-auto max-w-3xl">
        <BackLink />
        <p className="mt-4 rounded-md status-critical border px-4 py-3 text-sm">
          {fetchError instanceof ApiError ? fetchError.message : "Project not found."}
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl">
      <BackLink />

      <div className="mb-6 mt-4 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">{project.name}</h1>
          <p className="text-sm text-muted-foreground">
            {project.client_name ?? "No client specified"}
            {project.tender_reference ? ` · ${project.tender_reference}` : ""}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="secondary" size="sm" onClick={handleExport} disabled={isExporting}>
            <Download className="h-4 w-4" />
            {isExporting ? "Exporting…" : "Export to Excel"}
          </Button>
          <ProjectStatusBadge status={project.status} />
        </div>
      </div>
      {exportError && (
        <p className="mb-4 rounded-md status-critical border px-3 py-2 text-sm" role="alert">
          {exportError}
        </p>
      )}

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Project details</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-2 gap-4 text-sm">
            <Field label="Client" value={project.client_name} />
            <Field label="Tender reference" value={project.tender_reference} />
            <Field label="Sector" value={project.sector} />
            <Field label="Currency" value={project.currency} />
            <Field label="Confidentiality" value={project.confidentiality} />
            <Field label="Submission deadline" value={project.submission_deadline} />
          </dl>
          {project.notes && (
            <div className="mt-4">
              <Label>Notes</Label>
              <p className="text-sm text-foreground">{project.notes}</p>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Status</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {STATUS_OPTIONS.map((status) => (
              <Button
                key={status}
                size="sm"
                variant={status === project.status ? "primary" : "secondary"}
                disabled={statusMutation.isPending}
                onClick={() => statusMutation.mutate(status)}
              >
                {status}
              </Button>
            ))}
          </div>
          {error && (
            <p className="mt-3 rounded-md status-critical border px-3 py-2 text-sm" role="alert">
              {error}
            </p>
          )}
        </CardContent>
      </Card>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Documents</CardTitle>
        </CardHeader>
        <CardContent>
          <DocumentUploadPanel projectId={project.id} />
        </CardContent>
      </Card>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Compliance analysis</CardTitle>
        </CardHeader>
        <CardContent>
          <AnalysisPanel project={project} />
        </CardContent>
      </Card>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Contracts</CardTitle>
        </CardHeader>
        <CardContent>
          <ContractsPanel projectId={project.id} />
        </CardContent>
      </Card>

      {me?.is_admin && (
        <Card>
          <CardHeader>
            <CardTitle>Delete project</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="mb-3 text-sm text-muted-foreground">
              Removes this project and its documents, requirements, contracts, and risk findings
              from every view. Records are retained in the database so an audit trail survives, but
              nothing here will be reachable in the app afterwards.
            </p>
            {confirmingDelete ? (
              <div className="flex flex-wrap items-center gap-3">
                <span className="text-sm font-medium text-foreground">
                  Delete &ldquo;{project.name}&rdquo;?
                </span>
                <Button
                  variant="destructive"
                  size="sm"
                  disabled={deleteMutation.isPending}
                  onClick={() => deleteMutation.mutate()}
                >
                  {deleteMutation.isPending ? "Deleting…" : "Yes, delete it"}
                </Button>
                <Button size="sm" variant="secondary" onClick={() => setConfirmingDelete(false)}>
                  Cancel
                </Button>
              </div>
            ) : (
              <Button variant="secondary" size="sm" onClick={() => setConfirmingDelete(true)}>
                <Trash2 className="h-4 w-4" />
                Delete project
              </Button>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function BackLink() {
  return (
    <Link href="/projects" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
      <ArrowLeft className="h-4 w-4" />
      Back to projects
    </Link>
  );
}

function Field({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="text-foreground">{value ?? "—"}</dd>
    </div>
  );
}
