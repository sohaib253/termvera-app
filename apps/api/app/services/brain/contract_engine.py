"""Contract reasoning: classify a clause, extract its terms, judge its risk.

Pure functions over the knowledge base in contract_kb.py. Every finding
names the rule that produced it (in the description's trailing reference)
and quotes a verbatim sentence as evidence, so a reviewer can always see
exactly why the brain said what it said.
"""

import re

from app.schemas.clauserisk_ai import (
    ClauseExtractionOutput,
    MissingProtectionFinding,
    MissingProtectionsOutput,
    RiskAnalysisOutput,
    RiskFindingCandidate,
)
from app.services.brain import text as T
from app.services.brain.contract_kb import LEXICON, PROTECTIONS, RULES, Rule, _x

SEVERITY_ORDER = ["informational", "low", "medium", "high", "critical"]

_OBLIGATION = (
    r"\bshall\b",
    r"\bmust\b",
    r"\bis required to\b",
    r"\bare required to\b",
    r"\bundertakes? to\b",
    r"\bagrees? to\b",
)
_RIGHT = (
    r"\bmay\b",
    r"\bis entitled to\b",
    r"\bshall be entitled\b",
    r"\bhas the right\b",
    r"\breserves? the right\b",
)
_CONDITION = (
    r"\bif\b",
    r"\bwhere\b",
    r"\bprovided that\b",
    r"\bunless\b",
    r"\bsubject to\b",
    r"\bin the event\b",
    r"\bupon\b",
)
_EXCEPTION = (
    r"\bexcept\b",
    r"\bexcluding\b",
    r"\bother than\b",
    r"\bsave (?:for|as)\b",
    r"\bnotwithstanding\b",
    r"\bwith the exception of\b",
)
_VAGUE = (
    r"reasonabl",
    r"\bappropriate\b",
    r"as necessary",
    r"from time to time",
    r"satisfaction of",
    r"including but not limited",
)
_MUTUAL = (r"\beach party\b", r"\beither party\b", r"\bneither party\b", r"\bboth parties\b", r"\bmutual")
_HEADER = re.compile(
    r"^\s*(?:(?:article|section|clause)\s+)?(\d{1,3}(?:\.\d{1,3}){0,4})[.):]?\s+([^\n]{1,120})", re.I
)


def _max_sev(a: str, b: str) -> str:
    return a if SEVERITY_ORDER.index(a) >= SEVERITY_ORDER.index(b) else b


def _min_sev(a: str, b: str) -> str:
    return a if SEVERITY_ORDER.index(a) <= SEVERITY_ORDER.index(b) else b


def _split_title(clause_text: str) -> tuple[str, str]:
    """(title, body). The pipeline hands over clause text starting with
    its "12.3 Limitation of Liability" header line."""
    first_line = clause_text.strip().split("\n", 1)[0]
    m = _HEADER.match(first_line)
    title = m.group(2).strip() if m else ""
    body = T.strip_heading(clause_text, title)
    return title, body


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


def classify(title: str, body: str) -> tuple[str, str]:
    """Best subcategory and a confidence.

    A title hit is strong evidence (a clause headed "Set-Off" is about
    set-off). Ties between title hits go to the longer, more specific
    match: "Liquidated Damages for Delay" is about liquidated damages, not
    delay in general. Body cues accumulate as supporting evidence."""
    title_l = title.lower()
    body_l = body.lower()
    best = ("", 0.0, False)
    for subcategory, (title_cues, body_cues) in LEXICON.items():
        score = 0.0
        title_hit = False
        for cue in title_cues:
            m = re.search(cue, title_l)
            if m:
                score = max(score, 5 + len(m.group(0)) / 100)
                title_hit = True
        score += min(sum(1 for cue in body_cues if re.search(cue, body_l)), 3)
        if score > best[1]:
            best = (subcategory, score, title_hit)
    subcategory, score, title_hit = best
    if score < 1:
        return "", "low"
    if title_hit and score >= 6:
        return subcategory, "high"
    if title_hit or score >= 2:
        return subcategory, "medium"
    return subcategory, "low"


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


def extract_clause(clause_text: str, clause_title: str = "") -> ClauseExtractionOutput:
    title, body = _split_title(clause_text)
    title = clause_title or title
    sentences = T.sentences(body)
    subcategory, confidence = classify(title, body)
    own_number = _HEADER.match(clause_text.strip())
    own = own_number.group(1) if own_number else None
    references = [n for n in dict.fromkeys(m.group(1) for m in T.CLAUSE_REF_RE.finditer(body)) if n != own]
    return ClauseExtractionOutput(
        subcategory=subcategory,
        obligations=[s for s in sentences if T.contains_any(s, _OBLIGATION)][:6],
        rights=[s for s in sentences if T.contains_any(s, _RIGHT)][:4],
        conditions=[s for s in sentences if T.contains_any(s, _CONDITION)][:4],
        exceptions=[s for s in sentences if T.contains_any(s, _EXCEPTION)][:4],
        amounts=T.extract_all(T.AMOUNT_RE, body),
        dates=T.extract_all(T.DATE_RE, body),
        percentages=T.extract_all(T.PERCENT_RE, body),
        time_periods=T.extract_all(T.PERIOD_RE, body),
        referenced_clauses=references,
        confidence=confidence,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# Risk analysis
# ---------------------------------------------------------------------------


def _metric(metric: str, sentence: str) -> float | None:
    if metric == "percent":
        return T.first_percent(sentence)
    days = T.first_period_days(sentence)
    if days is None:
        return None
    return days / 30 if metric == "months" else days


def _band(rule: Rule, evidence: str) -> str | None:
    """Severity after numeric banding, or None if the rule shouldn't fire."""
    if rule.bands is None:
        return rule.severity
    metric, comparison, bands, otherwise = rule.bands
    value = _metric(metric, evidence)
    if value is None:
        return rule.severity
    for limit, severity in bands:
        if (comparison == "ge" and value >= limit) or (comparison == "le" and value <= limit):
            return severity
    return otherwise


def _figure(evidence: str, rule: Rule) -> str:
    metric = rule.bands[0] if rule.bands else None
    periods = T.extract_all(T.PERIOD_RE, evidence)
    percents = T.extract_all(T.PERCENT_RE, evidence)
    amounts = T.extract_all(T.AMOUNT_RE, evidence)
    if metric in ("days", "months") and periods:
        return periods[0]
    if metric == "percent" and percents:
        return percents[0]
    for group in (amounts, percents, periods):
        if group:
            return group[0]
    return {
        "days": "the stated period",
        "months": "the stated period",
        "percent": "the stated percentage",
    }.get(metric or "", "the stated amount")


def _trigger_phrase(evidence: str) -> str:
    m = re.search(
        r"\b(?:if|where|upon|in the event (?:of|that)|should|for each)\s[^,;.]{3,120}", evidence, re.I
    )
    return m.group(0).strip() if m else ""


def _exposure(evidence: str) -> str:
    figures = (
        T.extract_all(T.AMOUNT_RE, evidence)
        + T.extract_all(T.PERCENT_RE, evidence)
        + T.extract_all(T.PERIOD_RE, evidence)
    )
    if re.search(r"without limit|unlimited", evidence, re.I):
        figures.insert(0, "Unlimited")
    return ", ".join(dict.fromkeys(figures))[:240]


def _context_clause(related: list[str], pattern: str) -> str | None:
    for chunk in related:
        if re.search(pattern, chunk, re.I):
            m = re.match(r"\[Clause ([^\]]+)\]", chunk)
            return m.group(1) if m else "a related clause"
    return None


def analyze_clause(clause_text: str, related_clauses_context: list[str] | None = None) -> RiskAnalysisOutput:
    title, body = _split_title(clause_text)
    sentences = T.sentences(body)
    related = related_clauses_context or []
    findings: dict[str, tuple[str, RiskFindingCandidate]] = {}

    for rule in RULES:
        evidence = next(
            (
                s
                for s in sentences
                if T.contains_any(s, rule.triggers)
                and (rule.scope != "sentence" or all(re.search(r, s, re.I) for r in rule.requires))
            ),
            None,
        )
        if evidence is None:
            continue
        if rule.scope == "clause" and not all(re.search(r, body, re.I) for r in rule.requires):
            continue
        if rule.unless and T.contains_any(body, rule.unless):
            continue

        severity = _band(rule, evidence)
        if severity is None:
            continue
        for cue, target in rule.mitigate:
            if re.search(cue, body, re.I):
                severity = _min_sev(severity, target)
        for cue, target in rule.escalate:
            if re.search(cue, body, re.I):
                severity = _max_sev(severity, target)

        description = rule.description.replace("{figure}", _figure(evidence, rule))
        for cue, target in rule.context:
            ref = _context_clause(related, cue)
            if ref:
                severity = _max_sev(severity, target)
                description += (
                    f" Clause {ref} aggravates this: related drafting there undermines the protection."
                )

        finding = RiskFindingCandidate(
            risk_type=rule.risk_type,
            severity_hint=severity,  # type: ignore[arg-type]
            description=f"{description} [rule {rule.id}]",
            contractual_effect=rule.effect,
            potential_exposure=_exposure(evidence),
            trigger=_trigger_phrase(evidence),
            affected_party="both" if T.contains_any(evidence, _MUTUAL) else rule.affected_party,  # type: ignore[arg-type]
            uncertainty="ambiguous" if T.contains_any(evidence, _VAGUE) else "explicit",
            recommended_review_action=rule.action,
            evidence_excerpt=evidence,
        )
        # One finding per risk type per clause: keep the most severe reading.
        existing = findings.get(rule.risk_type)
        if existing is None or SEVERITY_ORDER.index(severity) > SEVERITY_ORDER.index(existing[0]):
            findings[rule.risk_type] = (severity, finding)

    ordered = sorted(findings.values(), key=lambda item: SEVERITY_ORDER.index(item[0]), reverse=True)
    return RiskAnalysisOutput(findings=[f for _, f in ordered])


# ---------------------------------------------------------------------------
# Contract-wide protections
# ---------------------------------------------------------------------------


def missing_protections(full_text: str, categories_present: list[str]) -> MissingProtectionsOutput:
    """Protections a well-drafted contract should contain, checked across
    the whole contract. When the full text isn't available (a provider
    instance that never saw the clauses), fall back to categories alone and
    only report what that can honestly support."""
    results: list[MissingProtectionFinding] = []
    if not full_text.strip():
        for category, label in (
            ("liability", "limitation of liability"),
            ("insurance", "insurance"),
            ("termination", "termination"),
            ("contractual", "governing law and disputes"),
        ):
            if category not in categories_present:
                results.append(
                    MissingProtectionFinding(
                        risk_type="missing_protection",
                        category=category,
                        severity_hint="medium",
                        description=f"No {label} clause was identified.",
                        recommended_review_action=f"Confirm whether {label} is addressed elsewhere.",
                    )
                )
        return MissingProtectionsOutput(missing_protections=results)

    text = T.normalize(full_text)
    for protection in PROTECTIONS:
        only_if = _x(protection.only_if)
        if only_if and not T.contains_any(text, only_if):
            continue
        if T.contains_any(text, _x(protection.present_if)):
            continue
        results.append(
            MissingProtectionFinding(
                risk_type=protection.risk_type,
                category=protection.category,
                severity_hint=protection.severity,  # type: ignore[arg-type]
                description=protection.description,
                recommended_review_action=protection.action,
            )
        )
    return MissingProtectionsOutput(missing_protections=results)
