"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { apiRequest, ApiError } from "@/lib/api-client";
import type { ContractDetail } from "@/lib/types";
import { routes } from "@/lib/routes";

export function LoadDemoContractButton({
  variant = "secondary",
}: {
  variant?: "primary" | "secondary";
}) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => apiRequest<ContractDetail>("/api/clauserisk/demo/load", { method: "POST" }),
    onSuccess: (contract) => {
      queryClient.invalidateQueries({ queryKey: ["contracts"] });
      router.push(routes.contract(contract.id));
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : "Could not load the sample contract.");
    },
  });

  return (
    <div>
      <Button variant={variant} onClick={() => mutation.mutate()} disabled={mutation.isPending}>
        <Sparkles className="h-4 w-4" />
        {mutation.isPending ? "Loading sample…" : "Try the sample contract"}
      </Button>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </div>
  );
}
