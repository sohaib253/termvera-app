import {
  AlertTriangle,
  ClipboardCheck,
  FileSearch,
  GitCompare,
  History,
  ShieldQuestion,
} from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex items-center justify-between border-b border-[var(--border)] px-6 py-4">
        <div className="flex items-center gap-2">
          <ShieldQuestion className="h-6 w-6 text-primary" />
          <span className="text-lg font-semibold">TenderGuard</span>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/login">
            <Button variant="ghost" size="sm">
              Log in
            </Button>
          </Link>
          <Link href="/register">
            <Button size="sm">Get started free</Button>
          </Link>
        </div>
      </header>

      <main className="flex-1">
        <section className="mx-auto max-w-4xl px-6 pb-16 pt-24 text-center">
          <p className="text-sm font-semibold uppercase tracking-wide text-primary">
            AI-powered tender &amp; contract intelligence
          </p>
          <h1 className="mt-4 text-4xl font-semibold tracking-tight text-foreground sm:text-5xl">
            Know what you&apos;re bidding. Know what you&apos;re signing.
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
            TenderGuard turns a tender package into a traceable compliance
            matrix. ClauseRisk turns a contract into a scored risk register.
            Both cite the exact clause and evidence behind every result, so
            your team makes the call, not the AI.
          </p>
          <div className="mt-8 flex items-center justify-center gap-3">
            <Link href="/register">
              <Button>Get started free</Button>
            </Link>
            <Link href="/login">
              <Button variant="secondary">Log in</Button>
            </Link>
          </div>
          <p className="mt-4 text-xs text-muted-foreground">
            No card required. Try either module instantly with a one-click
            sample dataset once you&apos;re in.
          </p>
        </section>

        <section className="mx-auto max-w-5xl px-6 pb-20">
          <div className="mb-10 text-center">
            <h2 className="text-2xl font-semibold text-foreground">
              Two modules built for the deal lifecycle
            </h2>
            <p className="mt-2 text-muted-foreground">
              From the tender you&apos;re chasing to the contract you&apos;ll sign,
              one platform covers both.
            </p>
          </div>
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            <ModuleCard
              icon={ClipboardCheck}
              accent="primary"
              name="TenderGuard Compliance"
              tagline="Analyze tenders and validate bid readiness."
              description="Upload a tender package and your draft bid. Get a clause-by-clause compliance matrix that flags what's missing, weak, or ambiguous before you submit, with the exact source evidence behind every result."
              points={["Requirement extraction", "Evidence matching", "Compliance matrix export"]}
            />
            <ModuleCard
              icon={AlertTriangle}
              accent="warning"
              name="ClauseRisk"
              tagline="Identify contractual exposure and negotiation issues."
              description="Upload a contract. Get clause-by-clause risk scoring, cross-clause relationships, and a version comparison that catches what changed before you sign, all backed by verifiable evidence."
              points={["Deterministic risk scoring", "Cross-clause analysis", "Version comparison"]}
            />
          </div>
        </section>

        <section className="mx-auto grid max-w-5xl grid-cols-1 gap-6 px-6 pb-24 sm:grid-cols-3">
          <FeatureCard
            icon={FileSearch}
            title="Evidence, not guesses"
            description="Every result traces back to its source document, page, and clause. Missing evidence is reported as exactly that: not located, not applicable, or needing human review, never a false pass."
          />
          <FeatureCard
            icon={GitCompare}
            title="Deterministic scoring"
            description="Risk severity and compliance status are computed from documented, explainable factors. The AI proposes; the scoring engine and your reviewers decide."
          />
          <FeatureCard
            icon={History}
            title="Human in the loop, always"
            description="Reviewers inspect every source clause, override AI assessments, and record why. Every override is captured in a full audit trail."
          />
        </section>
      </main>

      <footer className="border-t border-[var(--border)] px-6 py-6 text-center text-xs text-muted-foreground">
        TenderGuard and ClauseRisk are decision-support tools for bid and
        contracts teams. Neither replaces legal, technical, or commercial
        review before you submit or sign.
      </footer>
    </div>
  );
}

function ModuleCard({
  icon: Icon,
  accent,
  name,
  tagline,
  description,
  points,
}: {
  icon: typeof ClipboardCheck;
  accent: "primary" | "warning";
  name: string;
  tagline: string;
  description: string;
  points: string[];
}) {
  const iconWrapClass =
    accent === "primary"
      ? "bg-primary/10 text-primary"
      : "status-warning border-0";
  return (
    <div className="flex flex-col rounded-xl border border-[var(--border)] bg-surface p-7 text-left shadow-sm">
      <span className={`inline-flex h-11 w-11 items-center justify-center rounded-lg ${iconWrapClass}`}>
        <Icon className="h-5 w-5" />
      </span>
      <h3 className="mt-4 text-xl font-semibold text-foreground">{name}</h3>
      <p className="mt-1 text-sm font-medium text-muted-foreground">{tagline}</p>
      <p className="mt-3 text-sm text-muted-foreground">{description}</p>
      <div className="mt-4 flex flex-wrap gap-2">
        {points.map((point) => (
          <span
            key={point}
            className="rounded-full border border-[var(--border)] px-2.5 py-1 text-xs font-medium text-muted-foreground"
          >
            {point}
          </span>
        ))}
      </div>
    </div>
  );
}

function FeatureCard({
  icon: Icon,
  title,
  description,
}: {
  icon: typeof FileSearch;
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-lg border border-[var(--border)] bg-surface p-6">
      <Icon className="h-6 w-6 text-primary" />
      <h3 className="mt-3 font-semibold text-foreground">{title}</h3>
      <p className="mt-2 text-sm text-muted-foreground">{description}</p>
    </div>
  );
}
