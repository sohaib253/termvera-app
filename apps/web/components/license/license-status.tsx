"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, BadgeCheck, Clock, Eye } from "lucide-react";
import Link from "next/link";

import { apiRequest } from "@/lib/api-client";
import { BRAND } from "@/lib/brand";
import { cn } from "@/lib/cn";
import type { License } from "@/lib/types";

export function useLicense() {
  return useQuery({
    queryKey: ["license"],
    queryFn: () => apiRequest<License>("/api/license"),
    // Trial days tick over while the app sits open.
    refetchInterval: 30 * 60 * 1000,
  });
}

function plural(n: number, word: string) {
  return `${n} ${word}${n === 1 ? "" : "s"}`;
}

/** Where the workspace stands, always visible in the top bar. Trial and
 *  renewal prompts get stronger as the end approaches, the pattern
 *  JetBrains and Microsoft 365 use: quiet at first, never blocking,
 *  unmistakable once it matters. */
export function LicenseStatus() {
  const { data: license } = useLicense();
  if (!license) return null;

  const days = license.days_left ?? 0;
  let tone: "neutral" | "attention" | "critical" | "success";
  let icon = Clock;
  let text: string;
  let action: { label: string; href: string; external?: boolean } | null = null;

  switch (license.state) {
    case "free":
      tone = "success";
      icon = BadgeCheck;
      text = "Free · early access";
      break;
    case "trial":
      tone = days <= 3 ? "critical" : days <= 7 ? "attention" : "neutral";
      text = `Free trial · ${plural(days, "day")} left`;
      action = { label: "Buy now", href: BRAND.purchaseUrl, external: true };
      break;
    case "grace":
      tone = "critical";
      icon = AlertTriangle;
      text = `Subscription ended · renew within ${plural(days, "day")}`;
      action = { label: "Renew", href: BRAND.purchaseUrl, external: true };
      break;
    case "other_machine":
      tone = "critical";
      icon = Eye;
      text = "License is for another computer · view-only";
      action = { label: "Get a key for this PC", href: "/settings#license" };
      break;
    case "trial_expired":
    case "expired":
      tone = "critical";
      icon = Eye;
      text = license.state === "trial_expired" ? "Trial ended · view-only" : "Subscription ended · view-only";
      action = { label: "Enter license key", href: "/settings#license" };
      break;
    default:
      tone = "success";
      icon = BadgeCheck;
      text = license.licensed_to
        ? `${capitalise(license.plan)} · licensed to ${license.licensed_to}`
        : capitalise(license.plan);
  }
  const Icon = icon;

  return (
    <span className="flex items-center gap-2">
      <span
        className={cn(
          "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium",
          tone === "neutral" && "status-neutral",
          tone === "attention" && "status-warning",
          tone === "critical" && "status-critical",
          tone === "success" && "status-success"
        )}
      >
        <Icon className="h-3.5 w-3.5" />
        {text}
      </span>
      {action &&
        (action.external ? (
          <a
            href={action.href}
            target="_blank"
            rel="noreferrer"
            className="text-xs font-semibold text-primary hover:underline"
          >
            {action.label}
          </a>
        ) : (
          <Link href={action.href} className="text-xs font-semibold text-primary hover:underline">
            {action.label}
          </Link>
        ))}
      {license.state === "trial" && (
        <Link href="/settings#license" className="text-xs text-muted-foreground hover:underline">
          Have a key?
        </Link>
      )}
    </span>
  );
}

/** Full-width notice on every page once the workspace is view-only, so
 *  nobody meets it for the first time as a failed upload. */
export function ReadOnlyBanner() {
  const { data: license } = useLicense();
  if (!license?.read_only) return null;
  const what =
    license.state === "trial_expired"
      ? "Your free trial has ended"
      : license.state === "other_machine"
        ? "This workspace's license belongs to another computer"
        : "Your subscription has ended";
  return (
    <div className="status-critical border-b px-6 py-2 text-sm">
      <strong>{what}.</strong> Everything you&apos;ve done is safe and you can still open and export
      it. To add or analyse documents again,{" "}
      <a href={BRAND.purchaseUrl} target="_blank" rel="noreferrer" className="font-semibold underline">
        buy a license
      </a>{" "}
      and enter the key in{" "}
      <Link href="/settings#license" className="font-semibold underline">
        Settings
      </Link>
      .
    </div>
  );
}

function capitalise(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}
