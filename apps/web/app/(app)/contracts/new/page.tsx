"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Upload } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FileDropzone } from "@/components/ui/file-dropzone";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiRequest, ApiError } from "@/lib/api-client";
import type { Contract, ContractType, Project } from "@/lib/types";
import { nameFromFilename } from "@/lib/upload";
import { routes } from "@/lib/routes";

const CONTRACT_TYPES: { value: ContractType; label: string }[] = [
  { value: "services", label: "Services" },
  { value: "epc", label: "EPC" },
  { value: "construction", label: "Construction" },
  { value: "engineering", label: "Engineering" },
  { value: "oil_and_gas", label: "Oil & gas" },
  { value: "commercial", label: "Commercial" },
  { value: "other", label: "Other" },
];

/** One screen for what previously took six: pick or create the project,
 *  name the counterparty and contract, upload the document, and start the
 *  analysis. A contracts manager arriving with a PDF in hand should not
 *  have to learn the object model first. */
export default function NewContractReviewPage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const [projectId, setProjectId] = useState("");
  const [newProjectName, setNewProjectName] = useState("");
  const [name, setName] = useState("");
  const [counterparty, setCounterparty] = useState("");
  const [contractType, setContractType] = useState<ContractType>("services");
  const [file, setFile] = useState<File | null>(null);
  const [runAnalysis, setRunAnalysis] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState<string | null>(null);

  const { data: projects } = useQuery({
    queryKey: ["projects"],
    queryFn: () => apiRequest<Project[]>("/api/projects"),
  });

  const creatingNewProject = projectId === "__new__" || (projects?.length ?? 0) === 0;

  const submit = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error("Choose a contract document first.");

      setStep("Creating project…");
      let targetProjectId = projectId;
      if (creatingNewProject) {
        const project = await apiRequest<Project>("/api/projects", {
          method: "POST",
          body: { name: newProjectName.trim() || `${name.trim()} review` },
        });
        targetProjectId = project.id;
      }

      setStep("Creating contract…");
      const contract = await apiRequest<Contract>(`/api/projects/${targetProjectId}/contracts`, {
        method: "POST",
        body: {
          name: name.trim(),
          contract_type: contractType,
          counterparty_name: counterparty.trim() || undefined,
        },
      });

      // Analysis is queued in the same request and starts on the server once
      // text extraction finishes. Requesting it separately here used to fail
      // every time, because extraction (OCR, for a scan) was still running.
      setStep("Uploading…");
      const formData = new FormData();
      formData.append("version_label", "Original");
      formData.append("file", file);
      formData.append("run_analysis", runAnalysis ? "true" : "false");
      await apiRequest(`/api/contracts/${contract.id}/versions`, { method: "POST", body: formData });

      return contract;
    },
    onSuccess: (contract) => {
      queryClient.invalidateQueries({ queryKey: ["contracts"] });
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      router.push(routes.contract(contract.id));
    },
    onError: (err) => {
      setStep(null);
      setError(
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Could not start the contract review."
      );
    },
  });

  const canSubmit =
    !!file && name.trim().length > 0 && (creatingNewProject || projectId.length > 0);

  return (
    <div className="mx-auto max-w-2xl pb-16">
      <Link
        href="/contracts"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to contracts
      </Link>

      <div className="mb-6 mt-4">
        <h1 className="text-2xl font-semibold text-foreground">New contract review</h1>
        <p className="text-sm text-muted-foreground">
          Upload a contract to get clause-by-clause risk scoring, cross-clause analysis, and a
          negotiation issues list.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Contract details</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            className="space-y-5"
            onSubmit={(e) => {
              e.preventDefault();
              setError(null);
              submit.mutate();
            }}
          >
            <div>
              <Label htmlFor="project">Project</Label>
              {projects && projects.length > 0 ? (
                <select
                  id="project"
                  value={projectId}
                  onChange={(e) => setProjectId(e.target.value)}
                  className="h-10 w-full rounded-md border border-[var(--border)] bg-white px-3 text-sm"
                >
                  <option value="">Select a project…</option>
                  {projects.map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.name}
                    </option>
                  ))}
                  <option value="__new__">+ Create a new project</option>
                </select>
              ) : (
                <p className="text-sm text-muted-foreground">
                  You have no projects yet. One will be created for this contract.
                </p>
              )}
              <p className="mt-1 text-xs text-muted-foreground">
                Contracts live inside a project so tender and contract work on the same deal stay
                together.
              </p>
            </div>

            {creatingNewProject && (
              <div>
                <Label htmlFor="new_project_name">New project name</Label>
                <Input
                  id="new_project_name"
                  placeholder="North Field development"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                />
              </div>
            )}

            <div>
              <Label htmlFor="contract_name">Contract name</Label>
              <Input
                id="contract_name"
                placeholder="Offshore Well Testing Services Agreement"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="counterparty">Counterparty</Label>
                <Input
                  id="counterparty"
                  placeholder="Meridian Energy Company"
                  value={counterparty}
                  onChange={(e) => setCounterparty(e.target.value)}
                />
              </div>
              <div>
                <Label htmlFor="contract_type">Contract type</Label>
                <select
                  id="contract_type"
                  value={contractType}
                  onChange={(e) => setContractType(e.target.value as ContractType)}
                  className="h-10 w-full rounded-md border border-[var(--border)] bg-white px-3 text-sm"
                >
                  {CONTRACT_TYPES.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <Label>Contract document</Label>
              <FileDropzone
                selected={file}
                title="Drag the contract here or click to browse"
                hint="PDF (scanned or digital), Word, RTF, ODT, TXT, or scanned images, up to 50MB. Scanned pages are read with OCR. No sample contract to hand? Download one from Settings."
                onFiles={([chosen]) => {
                  setFile(chosen);
                  if (!name.trim()) setName(nameFromFilename(chosen.name));
                }}
              />
            </div>

            <label className="flex items-start gap-2 text-sm">
              <input
                type="checkbox"
                checked={runAnalysis}
                onChange={(e) => setRunAnalysis(e.target.checked)}
                className="mt-0.5"
              />
              <span>
                <span className="font-medium text-foreground">Start risk analysis immediately</span>
                <span className="block text-xs text-muted-foreground">
                  Runs in the background with the built-in analysis engine once the text has been
                  read. Scanned contracts take about a second per page to read first.
                </span>
              </span>
            </label>

            {error && (
              <p className="rounded-md status-critical border px-3 py-2 text-sm" role="alert">
                {error}
              </p>
            )}

            <div className="flex items-center gap-3">
              <Button type="submit" disabled={!canSubmit || submit.isPending}>
                <Upload className="h-4 w-4" />
                {submit.isPending ? (step ?? "Working…") : "Start contract review"}
              </Button>
              <Link href="/contracts">
                <Button type="button" variant="secondary">
                  Cancel
                </Button>
              </Link>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
