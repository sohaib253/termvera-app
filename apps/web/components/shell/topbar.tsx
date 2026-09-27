"use client";

import { LogOut } from "lucide-react";
import { useRouter } from "next/navigation";

import { LicenseStatus } from "@/components/license/license-status";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";

export function Topbar() {
  const { me, logout, isDesktop } = useAuth();
  const router = useRouter();

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  return (
    <header className="flex h-14 items-center justify-between border-b border-[var(--border)] bg-surface px-6">
      <div className="flex items-center text-sm text-muted-foreground">
        {me?.organization.name}
        <span className="mx-2 text-[var(--border)]">|</span>
        <LicenseStatus />
      </div>
      <div className="flex items-center gap-4">
        <div className="text-sm text-foreground">{me?.user.full_name}</div>
        {/* The desktop app has one local user and signs in by itself, so
            there's nothing to log out of. */}
        {!isDesktop && (
          <Button variant="ghost" size="sm" onClick={handleLogout} aria-label="Log out">
            <LogOut className="h-4 w-4" />
          </Button>
        )}
      </div>
    </header>
  );
}
