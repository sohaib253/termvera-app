"use client";

import { useQuery } from "@tanstack/react-query";
import { LogOut } from "lucide-react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { apiRequest } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { Usage } from "@/lib/types";

/** The API uses -1 to mean "no ceiling" (see services/license.py). Showing
 *  the sentinel as "2/-1 projects" is worse than showing no denominator. */
function formatUsage(used: number, limit: number): string {
  return limit < 0 ? `${used}` : `${used}/${limit}`;
}

export function Topbar() {
  const { me, logout } = useAuth();
  const router = useRouter();

  const { data: usage } = useQuery({
    queryKey: ["usage"],
    queryFn: () => apiRequest<Usage>("/api/usage"),
  });

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  return (
    <header className="flex h-14 items-center justify-between border-b border-[var(--border)] bg-surface px-6">
      <div className="flex items-center text-sm text-muted-foreground">
        {me?.organization.name}
        <span className="mx-2 text-[var(--border)]">|</span>
        <span
          className="rounded-full status-neutral border px-2 py-0.5 text-xs font-medium"
          title="Local development entitlement fixture — not a production license enforcement system"
        >
          {usage
            ? `${usage.license.plan} plan · ${formatUsage(usage.projects_used, usage.license.project_limit)} projects, ` +
              `${formatUsage(usage.contracts_used, usage.license.monthly_contract_limit)} contracts`
            : "Loading license…"}
        </span>
      </div>
      <div className="flex items-center gap-4">
        <div className="text-sm text-foreground">{me?.user.full_name}</div>
        <Button variant="ghost" size="sm" onClick={handleLogout} aria-label="Log out">
          <LogOut className="h-4 w-4" />
        </Button>
      </div>
    </header>
  );
}
