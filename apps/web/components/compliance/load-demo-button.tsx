"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { apiRequest, ApiError } from "@/lib/api-client";
import type { Project } from "@/lib/types";
import { routes } from "@/lib/routes";

export function LoadDemoButton({ variant = "secondary" }: { variant?: "primary" | "secondary" }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => apiRequest<Project>("/api/demo/load", { method: "POST" }),
    onSuccess: (project) => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      router.push(routes.projectCompliance(project.id));
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : "Could not load the sample project.");
    },
  });

  return (
    <div>
      <Button variant={variant} onClick={() => mutation.mutate()} disabled={mutation.isPending}>
        <Sparkles className="h-4 w-4" />
        {mutation.isPending ? "Loading sample…" : "Try the sample project"}
      </Button>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </div>
  );
}
