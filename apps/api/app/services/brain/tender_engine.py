"""Tender reasoning: find the requirements, then judge the bid against each.

Every requirement excerpt and every piece of bid evidence is a verbatim
sentence from the source page it cites, so the pipeline's excerpt
verification applies to the brain exactly as it would to a model.
"""

import math
import re
from collections import Counter
from dataclasses import dataclass, field

from app.schemas.ai import ComplianceAssessmentOutput, EvidenceCandidate, ExtractedRequirement
from app.services.brain import tender_kb as KB
from app.services.brain import text as T
from app.services.clauserisk.segmentation import PageText as SegPage
from app.services.clauserisk.segmentation import segment_pages

_WORD = re.compile(r"[a-z][a-z\-]+")
_FORM = re.compile(r"\bForm\s+([A-Z0-9]{1,3})\b")
_ISO = re.compile(r"\bISO\s?(\d{4,5})", re.I)
_EACH = re.compile(r"\b(?:each|every|all|both|per)\b", re.I)


def _stem(word: str) -> str:
    return word[:6] if len(word) > 6 else word


def _tokens(text: str) -> list[str]:
    return [_stem(w) for w in _WORD.findall(text.lower()) if w not in KB.STOPWORDS and len(w) > 2]


def _page_of(sentence: str, pages: list[tuple[int, str]]) -> int | None:
    needle = T.normalize(sentence).lower()
    for number, text in pages:
        if needle in T.normalize(text).lower():
            return number
    return None


# ---------------------------------------------------------------------------
# Requirement extraction
# ---------------------------------------------------------------------------


def _is_requirement_sentence(sentence: str) -> bool:
    if not (T.contains_any(sentence, KB.MANDATORY_CUES) or T.contains_any(sentence, KB.INDICATIVE_CUES)):
        return False
    lowered = sentence.lower().strip()
    addresses_bidder = T.contains_any(lowered, KB.BIDDER_SUBJECT) or T.contains_any(
        lowered, KB.CONTRACTOR_SUBJECT
    )
    if T.contains_any(lowered, KB.CLIENT_SUBJECT) and not addresses_bidder:
        return False
    # A pure consequence ("Tenders received late will be rejected") qualifies
    # the clause but isn't a requirement in its own right.
    if T.contains_any(lowered, KB.CONSEQUENCE_CUES) and not re.search(
        r"\b(?:shall|must)\b(?! be rejected| not be considered)", lowered
    ):
        return False
    return True


def _mandatory_status(requirement_sentences: list[str], clause_body: str) -> str:
    primary = requirement_sentences[0]
    if T.contains_any(primary, KB.MANDATORY_CUES) or T.contains_any(clause_body, KB.CONSEQUENCE_CUES):
        return "conditional" if T.contains_any(primary, KB.CONDITIONAL_CUES) else "mandatory"
    if T.contains_any(primary, KB.CONDITIONAL_CUES):
        return "conditional"
    if T.contains_any(primary, KB.INDICATIVE_CUES):
        return "indicative"
    return "unclear"


def _category(title: str, body: str) -> str:
    for source in (title, body):
        for name, patterns in KB.CATEGORIES:
            if T.contains_any(source, patterns):
                return name
    return "General"


def extract_requirements(pages: list[tuple[int, str]]) -> list[ExtractedRequirement]:
    segments = segment_pages([SegPage(page_number=n, text=t) for n, t in pages])
    requirements: list[ExtractedRequirement] = []
    for segment in segments:
        title = (segment.title or "").strip(" .:")
        body = T.strip_heading(segment.text, title)
        sentences = T.sentences(body)
        requirement_sentences = [s for s in sentences if _is_requirement_sentence(s)]
        if not requirement_sentences:
            continue

        # The cited excerpt must sit on one page to be verifiable; take the
        # first requirement sentence that does.
        excerpt, page = None, None
        for sentence in requirement_sentences:
            page = _page_of(sentence, pages)
            if page is not None:
                excerpt = sentence
                break
        if excerpt is None or page is None:
            continue

        status = _mandatory_status(requirement_sentences, body)
        evidence_sentence = next(
            (
                s
                for s in requirement_sentences
                if re.search(
                    r"\b(?:submit|provide|include|attach|list|state|report|declare|confirm|demonstrate|furnish|enclose)\b",
                    s,
                    re.I,
                )
            ),
            None,
        )
        condition = next((s for s in sentences if T.contains_any(s, KB.CONDITIONAL_CUES)), None)
        requirements.append(
            ExtractedRequirement(
                source_page=page,
                source_clause=segment.clause_number,
                source_excerpt=excerpt,
                title=title or (segment.clause_number or "Requirement"),
                normalized_requirement=body[:900],
                category=_category(title, body),
                mandatory_status=status,  # type: ignore[arg-type]
                conditions=condition,
                required_evidence=evidence_sentence,
                extraction_uncertain=status == "unclear",
            )
        )
    return requirements


# ---------------------------------------------------------------------------
# Assessment
# ---------------------------------------------------------------------------


@dataclass
class BidIndex:
    sentences: list[tuple[int, str]]
    idf: dict[str, float]
    tokens: list[set[str]]

    @classmethod
    def build(cls, pages: list[tuple[int, str]]) -> "BidIndex":
        sentences = [(n, s) for n, block in T.content_blocks(pages) for s in T.sentences(block)]
        tokens = [set(_tokens(s)) for _, s in sentences]
        df = Counter(tok for toks in tokens for tok in toks)
        total = max(len(sentences), 1)
        idf = {tok: math.log(1 + total / (1 + count)) for tok, count in df.items()}
        return cls(sentences, idf, tokens)


@dataclass
class Judgement:
    status: str = "compliant_looking"
    confidence: str = "medium"
    quality: str = "adequate"
    notes: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    conflicts: dict[int, str] = field(default_factory=dict)  # sentence index -> conflict
    evidence: list[int] = field(default_factory=list)
    anchor_hit: bool = False

    _RANK = {
        "compliant_looking": 0,
        "not_applicable_pending_verification": 1,
        "partially_addressed": 2,
        "evidence_not_found": 3,
        "potential_non_compliance": 4,
    }

    def escalate(self, status: str, confidence: str = "high") -> None:
        if self._RANK[status] > self._RANK[self.status]:
            self.status, self.confidence = status, confidence


def _kind(requirement: ExtractedRequirement) -> str:
    """bid (evidence the bid must contain), procedural (how to submit),
    or contract (an obligation on whoever wins)."""
    excerpt = requirement.source_excerpt.lower()
    if T.contains_any(excerpt, KB.PROCEDURAL_CUES):
        return "procedural"
    if T.contains_any(excerpt, KB.CONTRACTOR_SUBJECT) and not T.contains_any(excerpt, KB.BIDDER_SUBJECT):
        return "contract"
    return "bid"


def _rank(index: BidIndex, text: str, extra: tuple[str, ...]) -> list[tuple[float, int]]:
    wanted = set(_tokens(text))
    scored = []
    for i, toks in enumerate(index.tokens):
        score = sum(index.idf.get(t, 0) for t in wanted & toks)
        sentence = index.sentences[i][1]
        score += sum(3.0 for pattern in extra if re.search(pattern, sentence, re.I))
        if score > 0:
            scored.append((score, i))
    scored.sort(reverse=True)
    return scored


def _context(sentence: str, q: T.Quantity) -> tuple[set[str], set[str]]:
    position = T.normalize(sentence).find(q.text)
    if position < 0:
        return set(), set()
    before = _tokens(sentence[max(0, position - 60) : position])[-4:]
    after = _tokens(sentence[position + len(q.text) : position + len(q.text) + 60])[:4]
    return set(before), set(after)


def _fmt(value: float, unit: str) -> str:
    number = f"{value:,.0f}" if value >= 100 or value == int(value) else f"{value:g}"
    if unit == "usd":
        return f"USD {number}"
    if unit == "%":
        return f"{number}%"
    if unit == "rate":
        return number
    return f"{number} {unit}{'s' if value != 1 and unit and not unit.endswith('s') else ''}"


def _check_quantities(
    requirement: ExtractedRequirement, index: BidIndex, candidates: list[int], j: Judgement, kind: str
) -> None:
    bid_quantities = [
        (i, q, *_context(index.sentences[i][1], q))
        for i in candidates
        for q in T.quantities(index.sentences[i][1])
        if q.unit
    ]
    for sentence in T.sentences(requirement.normalized_requirement):
        for q in T.quantities(sentence):
            if not q.unit or q.unit in ("audited",):
                continue
            # "within the last five (5) years" is a look-back window for
            # counting something else, not a figure the bid must match.
            lead = T.normalize(sentence)[: max(T.normalize(sentence).find(q.text), 0)].lower()
            if re.search(r"(?:last|past|preceding|previous|prior)\s+(?:[a-z-]+\s+)?\(?$", lead):
                continue
            before, after = _context(sentence, q)
            matches = []
            for i, bq, b_before, b_after in bid_quantities:
                if bq.unit != q.unit:
                    continue
                overlap = (
                    len(before & b_before)
                    + 2 * len(after & b_after)
                    + len(after & b_before)
                    + len(before & b_after)
                )
                if overlap:
                    matches.append((overlap, i, bq))
            if not matches:
                if kind == "bid" and q.unit not in ("day", "hour", "month", "year", "week"):
                    j.missing.append(f"Stated figure to compare against the required {_fmt(q.value, q.unit)}")
                continue
            applies_to_all = bool(
                _EACH.search(
                    sentence[
                        max(0, T.normalize(sentence).find(q.text) - 50) : T.normalize(sentence).find(q.text)
                    ]
                )
            )
            checked = matches if applies_to_all else [max(matches, key=lambda m: m[0])]
            for _, i, bq in checked:
                failed = (
                    (q.bound == "min" and bq.value < q.value)
                    or (q.bound == "max" and bq.value > q.value)
                    or (q.bound == "exact" and abs(bq.value - q.value) > 1e-9)
                )
                need = {"min": "at least", "max": "no more than", "exact": "exactly"}[q.bound]
                if failed:
                    j.escalate("potential_non_compliance")
                    j.quality = "strong"
                    stated, required = _fmt(bq.value, bq.unit), _fmt(q.value, q.unit)
                    message = f"The bid states {stated}; the tender requires {need} {required}."
                    j.notes.append(message)
                    j.conflicts[i] = f"Numerical mismatch: {message}"
                else:
                    j.notes.append(
                        f"The bid's {_fmt(bq.value, bq.unit)} satisfies the requirement of "
                        f"{need} {_fmt(q.value, q.unit)}."
                    )
                    j.quality = "strong"
                if i not in j.evidence:
                    j.evidence.append(i)


def assess(requirement: ExtractedRequirement, index: BidIndex) -> tuple[Judgement, BidIndex]:
    j = Judgement()
    kind = _kind(requirement)
    text = f"{requirement.title}. {requirement.normalized_requirement}"

    if kind == "procedural":
        j.status, j.confidence, j.quality = "not_applicable_pending_verification", "high", "unknown"
        j.notes.append(
            "This is a procedural instruction about how or when to submit. It is met by the act of "
            "submission and cannot be evidenced from the bid's content; confirm it at submission."
        )
        return j, index

    anchors = {name: pats for name, pats in KB.ANCHORS.items() if T.contains_any(text, pats)}
    anchor_patterns = tuple(p for pats in anchors.values() for p in pats)
    ranked = _rank(index, text, anchor_patterns)
    # Only passages scoring close to the best match count as evidence: a
    # loosely related sentence elsewhere in the bid shouldn't be judged
    # (or blamed) as the bid's answer to this requirement.
    best_score = ranked[0][0] if ranked else 0.0
    top = [i for score, i in ranked[:4] if score >= 3.0 and score >= 0.5 * best_score]

    # Mandatory forms: a named form is either in the bid or it isn't.
    forms = list(dict.fromkeys(_FORM.findall(text)))
    if forms:
        present = {
            f for f in forms if any(re.search(rf"\bForm\s+{re.escape(f)}\b", s) for _, s in index.sentences)
        }
        absent = [f for f in forms if f not in present]
        listing = next((i for i, (_, s) in enumerate(index.sentences) if len(_FORM.findall(s)) >= 2), None)
        if absent:
            j.escalate("evidence_not_found")
            j.quality = "none"
            j.missing.extend(f"Form {f}" for f in absent)
            listed = sorted(set(_FORM.findall(index.sentences[listing][1]))) if listing is not None else []
            j.notes.append(
                f"Form {', '.join(absent)} was not found anywhere in the bid."
                + (f" The bid's own list of enclosed forms names Form {', '.join(listed)}." if listed else "")
            )
            if listing is not None:
                j.evidence.append(listing)
                j.conflicts[listing] = f"Form {', '.join(absent)} is absent from the enclosed forms list."
        else:
            j.anchor_hit = True
            j.notes.append(f"Form {', '.join(forms)} is referenced as enclosed in the bid.")
            hit = next(
                (
                    i
                    for i, (_, s) in enumerate(index.sentences)
                    if re.search(rf"\bForm\s+{re.escape(forms[0])}\b", s)
                ),
                None,
            )
            if hit is not None:
                j.evidence.append(hit)
            j.quality, j.confidence = "adequate", "high"

    # Certifications: each named standard must be held now, not planned.
    codes = list(dict.fromkeys(_ISO.findall(text)))
    if codes:
        held, planned, silent = [], [], []
        for code in codes:
            hits = [i for i, (_, s) in enumerate(index.sentences) if re.search(rf"ISO\s?{code}", s, re.I)]
            if not hits:
                silent.append(code)
                continue
            negated = [i for i in hits if T.is_negated(index.sentences[i][1])]
            if negated and len(negated) == len(hits):
                planned.append(code)
                j.conflicts[negated[0]] = f"ISO {code} is described as not yet held."
                j.evidence.append(negated[0])
            else:
                held.append(code)
                j.evidence.append(next(i for i in hits if i not in negated))
        if planned:
            j.escalate("potential_non_compliance")
            j.notes.append(
                f"The bid states ISO {', '.join(planned)} is not yet held; current certification is required."
            )
        if silent:
            j.escalate("partially_addressed" if held or planned else "evidence_not_found")
            j.notes.append(f"No mention of ISO {', '.join(silent)} was found in the bid.")
        if held:
            j.notes.append(f"ISO {', '.join(held)} is confirmed as held.")
        j.missing.extend(f"Current ISO {c} certificate" for c in planned + silent)
        j.quality, j.anchor_hit = "strong", True

    # Anchor concepts the bid never mentions at all.
    missing_anchors = [
        name for name, pats in anchors.items() if not any(T.contains_any(s, pats) for _, s in index.sentences)
    ]
    if anchors and len(missing_anchors) == len(anchors) and not forms and not codes:
        if kind == "contract":
            j.status, j.confidence, j.quality = "not_applicable_pending_verification", "medium", "none"
            j.notes.append(
                f"This is an obligation on the contractor during the contract "
                f"({', '.join(missing_anchors)}). "
                "The bid does not address it, which is normal; confirm the bid takes no exception to it."
            )
            return j, index
        j.escalate("evidence_not_found")
        j.quality = "none"
        j.missing.extend(missing_anchors)
        j.notes.append(f"The bid does not mention {', '.join(missing_anchors)} anywhere.")
        return j, index
    # The anchor named in the title or lead sentence is what the requirement
    # is about. If the bid never mentions that, incidental overlap on
    # secondary terms ("valid", "bank") is not evidence.
    subject = f"{requirement.title}. {requirement.source_excerpt}"
    subject_missing = [n for n in missing_anchors if T.contains_any(subject, anchors[n])]
    if subject_missing and not forms and not codes:
        if kind == "contract":
            j.status, j.confidence, j.quality = "not_applicable_pending_verification", "medium", "none"
            j.notes.append(
                f"This is an obligation on the contractor during the contract "
                f"({', '.join(subject_missing)}). "
                "The bid does not address it; confirm no exception is taken to it."
            )
            return j, index
        j.escalate("evidence_not_found")
        j.quality = "none"
        j.missing.extend(subject_missing)
        j.notes.append(f"The bid does not mention {', '.join(subject_missing)} anywhere.")
        return j, index
    if anchors and len(missing_anchors) < len(anchors):
        j.anchor_hit = True

    if not top and not j.evidence:
        if kind == "contract":
            j.status, j.confidence, j.quality = "not_applicable_pending_verification", "medium", "none"
            j.notes.append(
                "This is an obligation on the contractor during the contract, not a bid submission "
                "requirement. The bid does not address it; confirm no exception is taken to it."
            )
        else:
            j.escalate("evidence_not_found")
            j.quality = "none"
            j.notes.append("No passage in the bid addresses this requirement.")
        return j, index

    for i in top[:2]:
        if i not in j.evidence:
            j.evidence.append(i)

    form_satisfied = bool(forms) and not any(m.startswith("Form ") for m in j.missing)
    if form_satisfied:
        return j, index

    _check_quantities(requirement, index, top, j, kind)

    evidence_text = [index.sentences[i][1] for i in j.evidence]

    # A bid that proposes something else is a deviation, not an omission.
    qualifies = [i for i in top[:3] if T.is_qualified(index.sentences[i][1])]
    needs_acceptance = T.contains_any(text, KB.ACCEPTANCE_CUES) or requirement.category in (
        "Commercial",
        "Insurance & Liability",
    )
    if qualifies and needs_acceptance:
        j.escalate("potential_non_compliance")
        j.quality = "strong"
        i = qualifies[0]
        j.conflicts.setdefault(i, "The bid qualifies or seeks to change this requirement.")
        if i not in j.evidence:
            j.evidence.insert(0, i)
        j.notes.append(
            "The bid qualifies the requirement rather than accepting it, "
            "which evaluators treat as a deviation."
        )

    # Hedged or prospective language ("on request", "working towards").
    hedged = [i for i in j.evidence if T.is_negated(index.sentences[i][1]) and i not in j.conflicts]
    if hedged and kind == "bid":
        j.escalate("partially_addressed", "medium")
        j.notes.append(
            "The bid addresses this only conditionally or prospectively rather than evidencing it."
        )

    # Specific details the tender asked the bidder to state.
    detail = re.search(KB.DETAIL_LIST_CUE, requirement.normalized_requirement, re.I)
    if detail and kind == "bid":
        items = [
            it.strip(" ,.") for it in re.split(r",\s*(?:and\s+)?|\s+and\s+", detail.group(1)) if it.strip()
        ]
        haystack = set(_tokens(" ".join(evidence_text)))
        absent_items = [it for it in items if not (set(_tokens(it)) & haystack)]
        if absent_items:
            j.escalate("partially_addressed", "high")
            j.missing.extend(re.sub(r"^the\s+", "", it) for it in absent_items)
            j.notes.append(f"The bid does not state the {', '.join(absent_items)} the tender asks for.")

    if (
        needs_acceptance
        and kind == "bid"
        and not qualifies
        and not any(T.contains_any(s, KB.AFFIRMATIVE_CUES) for s in evidence_text)
    ):
        j.escalate("partially_addressed", "medium")
        j.notes.append(
            "The tender asks for explicit acceptance; the bid touches on the subject without confirming it."
        )

    if j.status == "compliant_looking":
        if j.anchor_hit or j.quality == "strong":
            j.confidence = "high"
        if not j.notes:
            j.notes.append("The bid addresses this requirement directly.")
        if j.missing and kind != "bid":
            j.notes.append(
                "Some stated figures could not be matched in the bid; they apply during the contract."
            )
    elif j.status == "partially_addressed" and j.quality == "adequate":
        j.quality = "insufficient"
    return j, index


def to_output(j: Judgement, index: BidIndex, document_id: str, category: str) -> ComplianceAssessmentOutput:
    evidence = []
    for i in j.evidence[:3]:
        page, sentence = index.sentences[i]
        evidence.append(
            EvidenceCandidate(
                document_id=document_id,
                page_number=page,
                excerpt=sentence,
                retrieval_method="brain:rules",
                evidence_type=category.lower(),
                relevance_note=next((n for n in j.notes if n), None),
                potential_conflict=j.conflicts.get(i),
            )
        )
    return ComplianceAssessmentOutput(
        status=j.status,  # type: ignore[arg-type]
        evidence_quality=j.quality,  # type: ignore[arg-type]
        assessment_confidence=j.confidence,  # type: ignore[arg-type]
        reason=" ".join(dict.fromkeys(j.notes)) or "Assessed by rule.",
        missing_information=list(dict.fromkeys(j.missing)),
        requires_human_review=True,
        evidence=evidence,
    )
