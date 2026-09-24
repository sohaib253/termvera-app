"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, X } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ProjectStatusBadge } from "@/components/ui/status-badge";
import { apiRequest, ApiError } from "@/lib/api-client";
import { cn } from "@/lib/cn";
import type { Project, ProjectCreateInput } from "@/lib/types";

/** Days until a deadline, using date-only arithmetic so a submission due
 *  later today reads as "today" rather than a fraction of a day. */
function daysUntil(deadline: string): number {
  const due = new Date(`${deadline}T00:00:00`);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((due.getTime() - today.getTime()) / 86_400_000);
}

function DeadlineCell({ project }: { project: Project }) {
  if (!project.submission_deadline) {
    return <span className="text-muted-foreground">—</span>;
  }

  const days = daysUntil(project.submission_deadline);
  const isClosed = project.status === "submitted" || project.status === "archived";
  const formatted = new Date(`${project.submission_deadline}T00:00:00`).toLocaleDateString();

  if (isClosed) {
    return <span className="text-muted-foreground">{formatted}</span>;
  }

  const tone =
    days < 0
      ? "severity-critical"
      : days <= 3
        ? "severity-critical"
        : days <= 7
          ? "severity-high"
          : days <= 14
            ? "severity-medium"
            : "severity-low";

  const text =
    days < 0
      ? `${Math.abs(days)}d overdue`
      : days === 0
        ? "Today"
        : `${days}d left`;

  return (
    <span className="flex items-center gap-2">
      <span className="text-muted-foreground">{formatted}</span>
      <span
        className={cn(
          "rounded-full border px-2 py-0.5 text-xs font-medium whitespace-nowrap",
          tone
        )}
      >
        {text}
      </span>
    </span>
  );
}

const schema = z.object({
  name: z.string().min(1, "Project name is required"),
  client_name: z.string().optional(),
  tender_reference: z.string().optional(),
  sector: z.string().optional(),
  submission_deadline: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

export default function ProjectsPage() {
  const [showCreate, setShowCreate] = useState(false);
  const queryClient = useQueryClient();

  const { data: projects, isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: () => apiRequest<Project[]>("/api/projects"),
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const [serverError, setServerError] = useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: (input: ProjectCreateInput) =>
      apiRequest<Project>("/api/projects", { method: "POST", body: input }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      setShowCreate(false);
      reset();
      setServerError(null);
    },
    onError: (err) => {
      setServerError(err instanceof ApiError ? err.message : "Could not create the project.");
    },
  });

  const onSubmit = (values: FormValues) => {
    // An untouched date input submits "", which the API rejects as an
    // invalid date; omit empty optional fields instead.
    const optional = (value: string | undefined) => (value ? value : undefined);
    createMutation.mutate({
      name: values.name,
      client_name: optional(values.client_name),
      tender_reference: optional(values.tender_reference),
      sector: optional(values.sector),
      submission_deadline: optional(values.submission_deadline),
    });
  };

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Projects</h1>
          <p className="text-sm text-muted-foreground">
            Each project tracks one tender&apos;s compliance review.
          </p>
        </div>
        <Button onClick={() => setShowCreate((v) => !v)}>
          {showCreate ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
          {showCreate ? "Cancel" : "New project"}
        </Button>
      </div>

      {showCreate && (
        <Card className="mb-6">
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
              <div>
                <Label htmlFor="name">Project name</Label>
                <Input
                  id="name"
                  placeholder="North Field Offshore Well Testing Package"
                  {...register("name")}
                />
                {errors.name && (
                  <p className="mt-1 text-sm text-red-600" role="alert">
                    {errors.name.message}
                  </p>
                )}
              </div>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <div>
                  <Label htmlFor="client_name">Client</Label>
                  <Input id="client_name" placeholder="Example Energy Company" {...register("client_name")} />
                </div>
                <div>
                  <Label htmlFor="tender_reference">Tender reference</Label>
                  <Input id="tender_reference" placeholder="ITB-2026-001" {...register("tender_reference")} />
                </div>
                <div>
                  <Label htmlFor="sector">Sector</Label>
                  <Input id="sector" placeholder="Oil & Gas" {...register("sector")} />
                </div>
                <div>
                  <Label htmlFor="submission_deadline">Submission deadline</Label>
                  <Input id="submission_deadline" type="date" {...register("submission_deadline")} />
                </div>
              </div>

              {serverError && (
                <p className="rounded-md status-critical border px-3 py-2 text-sm" role="alert">
                  {serverError}
                </p>
              )}

              <div className="flex justify-end gap-3">
                <Button type="button" variant="secondary" onClick={() => setShowCreate(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={isSubmitting}>
                  {isSubmitting ? "Creating…" : "Create project"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="px-5 py-8 text-center text-sm text-muted-foreground">Loading…</div>
          ) : !projects || projects.length === 0 ? (
            <div className="px-5 py-12 text-center text-sm text-muted-foreground">
              No projects yet. Use &ldquo;New project&rdquo; above to create one.
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wide text-muted-foreground">
                  <th className="px-5 py-3 font-medium">Name</th>
                  <th className="px-5 py-3 font-medium">Client</th>
                  <th className="px-5 py-3 font-medium">Reference</th>
                  <th className="px-5 py-3 font-medium">Submission deadline</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {projects.map((project) => (
                  <tr key={project.id} className="hover:bg-gray-50">
                    <td className="px-5 py-3">
                      <Link href={`/projects/${project.id}`} className="font-medium text-primary hover:underline">
                        {project.name}
                      </Link>
                    </td>
                    <td className="px-5 py-3 text-muted-foreground">{project.client_name ?? "—"}</td>
                    <td className="px-5 py-3 text-muted-foreground">{project.tender_reference ?? "—"}</td>
                    <td className="px-5 py-3">
                      <DeadlineCell project={project} />
                    </td>
                    <td className="px-5 py-3">
                      <ProjectStatusBadge status={project.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
