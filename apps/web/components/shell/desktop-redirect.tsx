"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "@/lib/auth-context";

/** Pages that only make sense on a server install (landing, login,
 *  register) send the desktop app's user where they belong instead:
 *  first-run setup, or straight into their workspace. */
export function DesktopRedirect() {
  const { isDesktop, isLoading, desktopSetupRequired } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (!isLoading && isDesktop) router.replace(desktopSetupRequired ? "/welcome" : "/dashboard");
  }, [isLoading, isDesktop, desktopSetupRequired, router]);
  return null;
}
