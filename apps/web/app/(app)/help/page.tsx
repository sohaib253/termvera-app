"use client";

import { useQuery } from "@tanstack/react-query";
import {
  ClipboardCheck,
  FileSearch,
  FileUp,
  Lock,
  ScanText,
  Search,
  ShieldAlert,
  UserCheck,
} from "lucide-react";
import { useMemo, useState } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiRequest } from "@/lib/api-client";
import { BRAND } from "@/lib/brand";
import { cn } from "@/lib/cn";

interface ContractCheck {
  id: string;
  title: string;
  severity: string;
  why_it_matters: string;
  what_to_negotiate: string;
}

interface HelpChecklists {
  contract_rule_count: number;
  contract_areas: { area: string; checks: ContractCheck[] }[];
  missing_protections: {
    title: string;
    area: string;
    severity: string;
    why_it_matters: string;
    what_to_negotiate: string;
  }[];
  clause_families: { family: string; clause_types: string[] }[];
  tender_areas: { area: string; summary: string }[];
  tender_evidence_anchors: string[];
}

const SECTIONS = [
  { id: "how", label: "How it works" },
  { id: "tender", label: "Tender & bid checklist" },
  { id: "contract", label: "Contract checklist" },
  { id: "severity", label: "How risk is rated" },
  { id: "privacy", label: "Privacy" },
  { id: "faq", label: "FAQ" },
];

/** Help, and the product's best sales document: exactly what it checks.
 *  The checklists come from the analysis engine (GET /api/help/checklists),
 *  so they are always what the software actually applies. */
export default function HelpPage() {
  const { data } = useQuery({
    queryKey: ["help-checklists"],
    queryFn: () => apiRequest<HelpChecklists>("/api/help/checklists", { auth: false }),
    staleTime: Infinity,
  });

  return (
    <div className="mx-auto max-w-5xl pb-20">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-foreground">Help &amp; how it works</h1>
        <p className="text-sm text-muted-foreground">
          What {BRAND.name} does with your documents, and every check it runs.
        </p>
      </div>

      <nav className="mb-8 flex flex-wrap gap-2">
        {SECTIONS.map((section) => (
          <a
            key={section.id}
            href={`#${section.id}`}
            className="rounded-full border border-[var(--border)] bg-surface px-3 py-1 text-sm text-foreground hover:bg-gray-50"
          >
            {section.label}
          </a>
        ))}
      </nav>

      <HowItWorks ruleCount={data?.contract_rule_count} protectionCount={data?.missing_protections.length} />
      <TenderChecklist data={data} />
      <ContractChecklist data={data} />
      <SeverityGuide />
      <Privacy />
      <Faq />
    </div>
  );
}

function Section({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
  return (
    <Card id={id} className="mb-6 scroll-mt-6">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

function HowItWorks({ ruleCount, protectionCount }: { ruleCount?: number; protectionCount?: number }) {
  const steps = [
    {
      icon: FileUp,
      title: "1. Upload",
      body: "Drop in tenders, bids and contracts: PDF, scanned PDF, Word, RTF, ODT, text, or photos of pages. Several files at once.",
    },
    {
      icon: ScanText,
      title: "2. Read",
      body: "Text is extracted page by page. Scanned pages are read with OCR, sideways and upside-down scans are straightened, and stamps and signatures are filtered out.",
    },
    {
      icon: FileSearch,
      title: "3. Check",
      body: `Tenders are broken into individual requirements and matched against your bid. Contracts are split into numbered clauses and tested against ${ruleCount ?? "dozens of"} risk rules, plus ${protectionCount ?? "a set of"} protections that should be there but may be missing.`,
    },
    {
      icon: UserCheck,
      title: "4. You decide",
      body: "Every finding shows the exact page and wording behind it. Accept, override, or add notes; every decision is kept in an audit trail. Export to Excel for the team.",
    },
  ];
  return (
    <Section id="how" title="How it works">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {steps.map((step) => (
          <div key={step.title} className="rounded-lg border border-[var(--border)] p-4">
            <step.icon className="h-6 w-6 text-primary" />
            <p className="mt-3 font-semibold text-foreground">{step.title}</p>
            <p className="mt-1 text-sm text-muted-foreground">{step.body}</p>
          </div>
        ))}
      </div>
      <p className="mt-4 text-sm text-muted-foreground">
        {BRAND.name} is a decision-support tool. It finds, cites and ranks; it never approves a bid
        or a contract on its own, and it reports missing evidence as missing rather than guessing.
      </p>
    </Section>
  );
}

const COMPLIANCE_STATUSES = [
  ["Compliant-looking", "The bid contains evidence that addresses the requirement. Still worth a reviewer's glance."],
  ["Partially addressed", "The bid touches the requirement but misses part of it (for example, states a figure without the certificate asked for)."],
  ["Evidence not found", "Nothing in the bid addresses it. The most common cause of a bid being marked non-compliant."],
  ["Potential non-compliance", "The bid says something that appears to contradict the requirement."],
  ["Not applicable (to verify)", "The requirement may not apply to this bid; a reviewer should confirm."],
  ["Human verified / rejected", "A reviewer has made the call; their decision overrides the software's."],
];

function TenderChecklist({ data }: { data?: HelpChecklists }) {
  return (
    <Section id="tender" title="Tender & bid checklist">
      <p className="text-sm text-muted-foreground">
        {BRAND.name} reads the tender and lists every requirement a bidder must meet, then checks your
        draft bid for evidence of each one before you submit.
      </p>

      <h3 className="mt-5 font-semibold text-foreground">What counts as a requirement</h3>
      <ul className="mt-2 grid grid-cols-1 gap-2 text-sm sm:grid-cols-3">
        <li className="rounded-md border border-[var(--border)] p-3">
          <span className="font-medium text-foreground">Mandatory</span>
          <span className="block text-muted-foreground">&quot;shall&quot;, &quot;must&quot;, &quot;is required to&quot;. Missing one can disqualify the bid.</span>
        </li>
        <li className="rounded-md border border-[var(--border)] p-3">
          <span className="font-medium text-foreground">Conditional</span>
          <span className="block text-muted-foreground">Applies only in a stated case (&quot;where applicable&quot;, &quot;if the bidder proposes…&quot;).</span>
        </li>
        <li className="rounded-md border border-[var(--border)] p-3">
          <span className="font-medium text-foreground">Indicative</span>
          <span className="block text-muted-foreground">&quot;should&quot;, &quot;preferably&quot;. Scored, not pass/fail.</span>
        </li>
      </ul>

      <h3 className="mt-5 font-semibold text-foreground">Areas checked</h3>
      <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
        {(data?.tender_areas ?? []).map((area) => (
          <div key={area.area} className="rounded-md border border-[var(--border)] p-3 text-sm">
            <p className="font-medium text-foreground">{area.area}</p>
            <p className="mt-0.5 text-xs text-muted-foreground">{area.summary}</p>
          </div>
        ))}
      </div>

      <h3 className="mt-5 font-semibold text-foreground">Items the bid must explicitly evidence</h3>
      <p className="mt-1 text-sm text-muted-foreground">
        For these, similar wording isn&apos;t enough: if the tender asks for it, the bid must name it,
        or the requirement is flagged as unevidenced.
      </p>
      <div className="mt-2 flex flex-wrap gap-2">
        {(data?.tender_evidence_anchors ?? []).map((anchor) => (
          <span key={anchor} className="rounded-full border border-[var(--border)] px-2.5 py-1 text-xs text-foreground">
            {anchor}
          </span>
        ))}
      </div>

      <h3 className="mt-5 font-semibold text-foreground">What each result means</h3>
      <dl className="mt-2 divide-y divide-[var(--border)] rounded-md border border-[var(--border)] text-sm">
        {COMPLIANCE_STATUSES.map(([status, meaning]) => (
          <div key={status} className="grid grid-cols-1 gap-1 px-3 py-2 sm:grid-cols-3">
            <dt className="font-medium text-foreground">{status}</dt>
            <dd className="text-muted-foreground sm:col-span-2">{meaning}</dd>
          </div>
        ))}
      </dl>
    </Section>
  );
}

const SEVERITY_STYLE: Record<string, string> = {
  critical: "severity-critical",
  high: "severity-high",
  medium: "severity-medium",
  low: "severity-low",
  informational: "severity-info",
};

function SeverityChip({ severity }: { severity: string }) {
  return (
    <span className={cn("rounded-full border px-2 py-0.5 text-[11px] font-semibold capitalize", SEVERITY_STYLE[severity])}>
      {severity}
    </span>
  );
}

function ContractChecklist({ data }: { data?: HelpChecklists }) {
  const [query, setQuery] = useState("");
  const areas = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!data) return [];
    if (!q) return data.contract_areas;
    return data.contract_areas
      .map((area) => ({
        ...area,
        checks: area.checks.filter((check) =>
          [check.id, check.title, check.why_it_matters, check.what_to_negotiate, area.area]
            .join(" ")
            .toLowerCase()
            .includes(q)
        ),
      }))
      .filter((area) => area.checks.length > 0);
  }, [data, query]);

  return (
    <Section id="contract" title="Contract checklist">
      <p className="text-sm text-muted-foreground">
        Every contract is split into its numbered clauses and each clause is classified (payment,
        liquidated damages, indemnity and so on). It is then tested against{" "}
        {data?.contract_rule_count ?? "the"} risk rules written from the contractor&apos;s side of the
        table: what does this clause cost us, and when? Each rule says why the clause matters and
        what to ask for instead.
      </p>

      <div className="relative mt-4">
        <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search the rules, e.g. liquidated damages, indemnity, retention"
          className="pl-9"
        />
      </div>

      <div className="mt-4 space-y-2">
        {areas.map((area) => (
          <details key={area.area} className="rounded-md border border-[var(--border)]" open={!!query}>
            <summary className="cursor-pointer select-none px-4 py-2.5 text-sm font-medium text-foreground">
              {area.area}
              <span className="ml-2 text-xs font-normal text-muted-foreground">{area.checks.length} checks</span>
            </summary>
            <ul className="divide-y divide-[var(--border)] border-t border-[var(--border)]">
              {area.checks.map((check) => (
                <li key={check.id} className="px-4 py-3 text-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs text-muted-foreground">{check.id}</span>
                    <span className="font-medium text-foreground">{check.title}</span>
                    <SeverityChip severity={check.severity} />
                  </div>
                  <p className="mt-1 text-muted-foreground">{check.why_it_matters}</p>
                  <p className="mt-1 text-foreground">
                    <span className="font-medium">Negotiate: </span>
                    {check.what_to_negotiate}
                  </p>
                </li>
              ))}
            </ul>
          </details>
        ))}
        {data && areas.length === 0 && (
          <p className="text-sm text-muted-foreground">No rules match &quot;{query}&quot;.</p>
        )}
      </div>

      <h3 className="mt-6 flex items-center gap-2 font-semibold text-foreground">
        <ShieldAlert className="h-4 w-4 text-primary" />
        Protections that should be there
      </h3>
      <p className="mt-1 text-sm text-muted-foreground">
        What a contract leaves out can cost more than what it says. These are flagged when no clause
        provides them.
      </p>
      <ul className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
        {(data?.missing_protections ?? []).map((p) => (
          <li key={p.title} className="rounded-md border border-[var(--border)] p-3 text-sm">
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium text-foreground">{p.title}</span>
              <SeverityChip severity={p.severity} />
            </div>
            <p className="mt-1 text-muted-foreground">{p.why_it_matters}</p>
          </li>
        ))}
      </ul>

      <h3 className="mt-6 font-semibold text-foreground">Clause types recognised</h3>
      <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
        {(data?.clause_families ?? []).map((family) => (
          <div key={family.family} className="rounded-md border border-[var(--border)] p-3 text-sm">
            <p className="font-medium text-foreground">{family.family}</p>
            <p className="mt-0.5 text-xs text-muted-foreground">{family.clause_types.join(", ")}</p>
          </div>
        ))}
      </div>
    </Section>
  );
}

function SeverityGuide() {
  const rows = [
    ["critical", "Could cost more than the contract is worth, or is typically uninsurable (e.g. uncapped liability, indemnity for the client's own negligence)."],
    ["high", "Material financial or schedule exposure that should be negotiated before signing."],
    ["medium", "Worth raising; acceptable if priced or mitigated elsewhere."],
    ["low", "Minor, or already largely mitigated by other clauses."],
    ["informational", "Noted for completeness; no action needed."],
  ];
  return (
    <Section id="severity" title="How risk is rated">
      <p className="text-sm text-muted-foreground">
        Severity is calculated, not guessed. Each rule starts at a base level, then moves with the
        numbers in the clause (a 20% liquidated damages cap is rated differently from a 5% one), with
        wording elsewhere in the same clause that makes it worse or better, and with related clauses
        (a liability cap matters less if an indemnity elsewhere sits outside it). The same contract
        always produces the same ratings.
      </p>
      <dl className="mt-3 space-y-2 text-sm">
        {rows.map(([severity, meaning]) => (
          <div key={severity} className="flex items-start gap-3">
            <dt className="w-28 shrink-0">
              <SeverityChip severity={severity} />
            </dt>
            <dd className="text-muted-foreground">{meaning}</dd>
          </div>
        ))}
      </dl>
    </Section>
  );
}

function Privacy() {
  return (
    <Section id="privacy" title="Privacy">
      <div className="flex gap-3 text-sm text-muted-foreground">
        <Lock className="h-5 w-5 shrink-0 text-primary" />
        <p>
          The desktop app runs entirely on your computer. Documents, results and the database stay in
          your Windows profile; nothing is uploaded, and no external AI service is used. The app only
          accepts connections from this computer. License keys are checked offline.
        </p>
      </div>
    </Section>
  );
}

const FAQ = [
  [
    "Which files can I upload?",
    "PDF (digital or scanned), Word .docx, RTF, ODT, plain text, and scanned images (PNG, JPG, TIFF), up to 50MB each. Old Word .doc files work when Microsoft Word is installed; otherwise save them as .docx first.",
  ],
  [
    "How good is it with scanned contracts?",
    "Clean office scans read very accurately, including rotated pages. Handwriting (filled-in dates, initials) isn't read reliably, and heavy stamps over text can blur a line. Every finding links to its page, so check the source when a result looks odd.",
  ],
  [
    "How long does analysis take?",
    "Digital documents: seconds. Scanned documents: about a second per page to read first; a 50-page scanned contract is ready in under a minute.",
  ],
  [
    "Can I trust the results?",
    "Treat them as a thorough first pass by a careful reviewer. Every result cites its evidence and the ratings are deterministic, but the final judgement, especially legal interpretation, stays with your team.",
  ],
  [
    "What happens when the trial or subscription ends?",
    "Nothing is deleted. The workspace becomes view-only: you can still open and export everything, but can't add or analyse new documents until a license key is entered. Subscriptions also get a 7-day grace period.",
  ],
  [
    "Where is my data, and how do I back it up?",
    "In %LOCALAPPDATA%\\Termvera on this computer. Back up that folder with your normal backup tool; copying it to a new computer moves your whole workspace.",
  ],
];

function Faq() {
  return (
    <Section id="faq" title="Frequently asked questions">
      <div className="space-y-2">
        {FAQ.map(([question, answer]) => (
          <details key={question} className="rounded-md border border-[var(--border)]">
            <summary className="flex cursor-pointer select-none items-center gap-2 px-4 py-2.5 text-sm font-medium text-foreground">
              <ClipboardCheck className="h-4 w-4 text-primary" />
              {question}
            </summary>
            <p className="border-t border-[var(--border)] px-4 py-3 text-sm text-muted-foreground">{answer}</p>
          </details>
        ))}
      </div>
      <p className="mt-4 text-sm text-muted-foreground">
        Still stuck? Email{" "}
        <a href={`mailto:${BRAND.supportEmail}`} className="font-medium text-primary hover:underline">
          {BRAND.supportEmail}
        </a>
        .
      </p>
    </Section>
  );
}
