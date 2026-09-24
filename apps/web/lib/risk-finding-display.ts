import type { RiskFinding } from "@/lib/types";

/** Title and supporting line for a finding in a list.
 *
 *  When the risk type resolves to the catch-all ("other"), the label adds
 *  nothing a reviewer can act on, so the description becomes the title
 *  instead. Findings analysed before the risk-type taxonomy existed store
 *  free-text values that no longer map to anything, and they all land
 *  here, so the fallback isn't a rare edge case. */
export function findingTitle(finding: Pick<RiskFinding, "risk_type" | "risk_type_label" | "risk_description">): {
  title: string;
  subtitle: string | null;
} {
  if (finding.risk_type && finding.risk_type !== "other") {
    return { title: finding.risk_type_label, subtitle: finding.risk_description };
  }

  const description = finding.risk_description.trim();
  const firstSentence = description.split(/(?<=[.!?])\s/)[0] ?? description;
  return {
    title: firstSentence || "Unclassified risk",
    subtitle: description.length > firstSentence.length ? description.slice(firstSentence.length).trim() : null,
  };
}
