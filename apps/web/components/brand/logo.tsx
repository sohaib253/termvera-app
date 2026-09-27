import { BRAND } from "@/lib/brand";
import { cn } from "@/lib/cn";

/** The Termvera mark: a T and V monogram (Term + vera) on an indigo tile.
 *  The white bar is the T; the teal stroke is both the V and a check mark,
 *  so the tile reads "terms, verified". Drawn on a 32-unit grid so it stays
 *  crisp at 16px (tab, taskbar). apps/desktop/make_icon.py and the website
 *  (apps/site/page.html) draw the same shape. */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={cn("h-7 w-7 shrink-0", className)} aria-hidden="true">
      <defs>
        <linearGradient id="tv-tile" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#5b5bf0" />
          <stop offset="1" stopColor="#2e2a9c" />
        </linearGradient>
      </defs>
      <rect width="32" height="32" rx="8.5" fill="url(#tv-tile)" />
      <rect x="7" y="7.2" width="18" height="4.2" rx="2.1" fill="#ffffff" />
      <path
        d="M13.9 11.2 L16.2 23.2 L23.6 13.8"
        fill="none"
        stroke="#2dd4bf"
        strokeWidth="3.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Mark plus the lowercase wordmark: "term" in ink, "vera" in brand indigo. */
export function Logo({ className, size = "md" }: { className?: string; size?: "md" | "lg" }) {
  const name = BRAND.name.toLowerCase();
  return (
    <span className={cn("inline-flex items-center gap-2", className)}>
      <LogoMark className={size === "lg" ? "h-9 w-9" : undefined} />
      <span
        className={cn(
          "font-bold tracking-tight text-foreground",
          size === "lg" ? "text-2xl" : "text-lg"
        )}
      >
        {name.slice(0, 4)}
        <span className="text-primary">{name.slice(4)}</span>
      </span>
    </span>
  );
}
