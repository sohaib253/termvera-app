"use client";

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { SidebarNav } from "@/components/shell/sidebar-nav";
import { Topbar } from "@/components/shell/topbar";
import { useAuth } from "@/lib/auth-context";

export default function AppShellLayout({ children }: { children: ReactNode }) {
  const { me, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !me) {
      router.replace("/login");
    }
  }, [isLoading, me, router]);

  if (isLoading || !me) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-muted-foreground">
        Loading…
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      <aside className="w-60 shrink-0 border-r border-[var(--border)] bg-surface">
        <SidebarNav />
      </aside>
      <div className="flex flex-1 flex-col">
        <Topbar />
        <main className="flex-1 bg-background p-6">{children}</main>
      </div>
    </div>
  );
}
