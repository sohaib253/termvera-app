"use client";

import {
  AlertTriangle,
  FileSignature,
  FileText,
  LayoutDashboard,
  LifeBuoy,
  Settings,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { Logo } from "@/components/brand/logo";
import { cn } from "@/lib/cn";

// Grouped by module so it's obvious which discipline a screen belongs to.
// Items that don't exist yet are left out entirely rather than shown
// greyed out: a sidebar of dead links reads as an unfinished product.
const NAV_GROUPS: {
  label: string | null;
  items: { href: string; label: string; icon: typeof LayoutDashboard }[];
}[] = [
  {
    label: null,
    items: [{ href: "/dashboard", label: "Dashboard", icon: LayoutDashboard }],
  },
  {
    label: "Tenders",
    items: [{ href: "/projects", label: "Projects", icon: FileText }],
  },
  {
    label: "Contracts",
    items: [
      { href: "/contracts", label: "Contracts", icon: FileSignature },
      { href: "/risk-findings", label: "Risk Register", icon: AlertTriangle },
    ],
  },
  {
    label: "Workspace",
    items: [
      { href: "/help", label: "Help & how it works", icon: LifeBuoy },
      { href: "/settings", label: "Settings", icon: Settings },
    ],
  },
];

export function SidebarNav() {
  const pathname = usePathname();

  return (
    <nav className="flex h-full flex-col gap-1 p-3">
      <div className="mb-4 px-2 py-2">
        <Logo />
      </div>

      {NAV_GROUPS.map((group, index) => (
        <div key={group.label ?? `group-${index}`} className={group.label ? "mt-4" : undefined}>
          {group.label && (
            <p className="px-3 pb-1 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/70">
              {group.label}
            </p>
          )}
          {group.items.map((item) => {
            const isActive = pathname.startsWith(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.label}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary/10 text-primary"
                    : "text-foreground/80 hover:bg-gray-100 hover:text-foreground"
                )}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </div>
      ))}
    </nav>
  );
}
