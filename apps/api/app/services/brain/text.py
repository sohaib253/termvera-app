"""Text reasoning primitives shared by the contract and tender engines.

Everything that returns text returns it verbatim (modulo whitespace) from
the source, so any excerpt the brain cites passes the same substring
verification an AI-cited excerpt has to pass.
"""

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Normalisation and sentences
# ---------------------------------------------------------------------------

_WS = re.compile(r"\s+")

# Abbreviations that end in a full stop but don't end a sentence. Masked
# before splitting, restored after, so "No. 1" or "e.g. the Contractor"
# doesn't break a clause into fragments.
_ABBREVIATIONS = (
    "No.",
    "no.",
    "Nos.",
    "e.g.",
    "i.e.",
    "etc.",
    "Ltd.",
    "Co.",
    "Inc.",
    "Corp.",
    "plc.",
    "Art.",
    "Cl.",
    "cl.",
    "para.",
    "Para.",
    "approx.",
    "Approx.",
    "U.S.",
    "U.K.",
    "Sch.",
    "Vol.",
    "Rev.",
    "vs.",
    "Messrs.",
    "Mr.",
    "Ms.",
    "Dr.",
    "St.",
    "Pty.",
    "L.L.C.",
)
_MASK = "․"  # one-dot leader: never appears in real contract text
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\"'“])")


def normalize(text: str) -> str:
    return _WS.sub(" ", text).strip()


def sentences(text: str) -> list[str]:
    text = normalize(text)
    for abbreviation in _ABBREVIATIONS:
        text = text.replace(abbreviation, abbreviation.replace(".", _MASK))
    # Decimal points and "1.2"-style clause numbers must not split either.
    text = re.sub(r"(?<=\d)\.(?=\d)", _MASK, text)
    parts = _SENTENCE_BREAK.split(text)
    return [p.replace(_MASK, ".").strip() for p in parts if p.strip()]


_HEADING_LINE = re.compile(
    r"^\s*(?:(?:article|section|clause|part|schedule|annex|appendix)\s+)?\d{1,3}(?:\.\d{1,3}){0,4}[.)]?\s+[^.!?]{1,90}$",
    re.I,
)
_CAPS_LINE = re.compile(r"^\s*[A-Z0-9][A-Z0-9 ,&'/()\-.]{3,90}$")
_PAGE_LINE = re.compile(r"^\s*(?:page\s+)?\d+(?:\s*(?:of|/)\s*\d+)?\s*$", re.I)


def content_blocks(pages: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """(page, block) runs of body text with headings removed.

    PDF text keeps each heading on its own line; flattening whitespace
    first would glue "...on request." to the next clause's heading and
    first sentence, leaking one clause's language into another. Lines that
    repeat on several pages (running headers and footers) are dropped too.
    """
    line_pages: dict[str, set[int]] = {}
    for number, text in pages:
        for line in text.splitlines():
            key = line.strip()
            if key:
                line_pages.setdefault(key, set()).add(number)
    repeated = {line for line, where in line_pages.items() if len(where) >= 2 and len(line) < 120}

    blocks: list[tuple[int, str]] = []
    for number, text in pages:
        current: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            is_heading = (
                not stripped
                or stripped in repeated
                or _PAGE_LINE.match(stripped)
                or (_HEADING_LINE.match(stripped) and len(stripped.split()) <= 10)
                or (
                    _CAPS_LINE.match(stripped)
                    and stripped == stripped.upper()
                    and any(c.isalpha() for c in stripped)
                )
            )
            if is_heading:
                if current:
                    blocks.append((number, " ".join(current)))
                    current = []
                continue
            current.append(stripped)
        if current:
            blocks.append((number, " ".join(current)))
    return blocks


def strip_heading(text: str, title: str | None = None) -> str:
    """Drop a leading "12.3 Limitation of Liability" line from a clause body."""
    text = normalize(text)
    text = re.sub(
        r"^(?:(?:article|section|clause)\s+)?\d{1,3}(?:\.\d{1,3}){0,4}[.):]?\s+", "", text, flags=re.I
    )
    if title and text.lower().startswith(title.lower()):
        text = text[len(title) :].lstrip(" :.-")
    return text


def contains_any(text: str, patterns: tuple[str, ...] | list[str]) -> bool:
    return any(re.search(p, text, re.I) for p in patterns)


def first_match(text: str, patterns: tuple[str, ...] | list[str]) -> re.Match | None:
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            return m
    return None


# ---------------------------------------------------------------------------
# Numbers
# ---------------------------------------------------------------------------

_UNITS_WORDS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
}
_TENS_WORDS = {
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}
_SCALE = {
    "thousand": 1e3,
    "k": 1e3,
    "million": 1e6,
    "m": 1e6,
    "mm": 1e6,
    "mn": 1e6,
    "billion": 1e9,
    "bn": 1e9,
    "b": 1e9,
}
NUMBER_WORD_RE = (
    r"(?:(?:twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)(?:[-\s](?:one|two|three|"
    r"four|five|six|seven|eight|nine))?|zero|one|two|three|four|five|six|seven|eight|nine|ten|"
    r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|hundred)"
)


def words_to_number(words: str) -> float | None:
    words = words.lower().replace("-", " ").strip()
    if words == "hundred":
        return 100.0
    total = 0
    for token in words.split():
        if token in _UNITS_WORDS:
            total += _UNITS_WORDS[token]
        elif token in _TENS_WORDS:
            total += _TENS_WORDS[token]
        elif token == "hundred":
            total = (total or 1) * 100
        else:
            return None
    return float(total)


def parse_number(raw: str) -> float | None:
    try:
        return float(raw.replace(",", ""))
    except ValueError:
        return None


CURRENCIES = (
    r"(?:USD|US\$|U\.S\.\$|EUR|GBP|QAR|AED|SAR|KWD|OMR|BHD|INR|CNY|JPY|AUD|CAD|NOK|SGD|MYR|NGN|ZAR|\$|€|£)"
)

AMOUNT_RE = re.compile(
    rf"{CURRENCIES}\s?\d[\d,]*(?:\.\d+)?(?:\s?(?:million|billion|thousand|mn|bn|m|k)\b)?"
    r"(?:\s+(?:per|a|each)\s+(?:day|week|month|year|occurrence|event|claim|hour|well|unit|shift))?",
    re.I,
)
PERCENT_RE = re.compile(r"\d+(?:\.\d+)?\s?%")
DATE_RE = re.compile(
    r"\b\d{1,2}(?:st|nd|rd|th)?\s(?:January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s\d{4}\b|\b(?:January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s\d{1,2},?\s\d{4}\b|\b\d{1,2}/\d{1,2}/\d{4}\b",
)
PERIOD_RE = re.compile(
    rf"\b(?:{NUMBER_WORD_RE}\s)?\(?\d{{1,4}}\)?\s(?:calendar\s|business\s|working\s|consecutive\s)?"
    r"(?:days?|weeks?|months?|years?|hours?|minutes?|seconds?)\b"
    rf"|\b{NUMBER_WORD_RE}\s(?:calendar\s|business\s|working\s)?(?:days?|weeks?|months?|years?|hours?)\b",
    re.I,
)
CLAUSE_REF_RE = re.compile(
    r"\b(?:Clauses?|Articles?|Sections?|Paragraphs?|Sub-?clauses?)\s+(\d{1,3}(?:\.\d{1,3}){0,4})",
    re.I,
)


def extract_all(pattern: re.Pattern, text: str) -> list[str]:
    seen: list[str] = []
    for m in pattern.finditer(normalize(text)):
        value = m.group(0).strip()
        if value and value not in seen:
            seen.append(value)
    return seen


# ---------------------------------------------------------------------------
# Quantities with units and comparators
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Quantity:
    value: float
    unit: str
    bound: str  # "min", "max", or "exact"
    text: str


_MIN_CUES = (
    r"not less than",
    r"no less than",
    r"at least",
    r"minimum of",
    r"a minimum",
    r"minimum",
    r"in excess of",
    r"or more",
    r"or greater",
    r"greater than",
    r"more than",
    r"exceed(?:s|ing)?\b",
    r"not below",
    r"upwards of",
)
_MAX_CUES = (
    r"not more than",
    r"no more than",
    r"not exceeding",
    r"shall not exceed",
    r"not to exceed",
    r"may not exceed",
    r"up to",
    r"maximum of",
    r"maximum",
    r"within",
    r"no later than",
    r"less than",
    r"below",
    r"at most",
    r"no greater than",
    r"not greater than",
    r"capped at",
    r"limited to",
    r"interval of not more than",
)
_REJECTION_CONSEQUENCE = (
    r"shall not be considered",
    r"will not be considered",
    r"will be rejected",
    r"shall be rejected",
    r"disqualif",
    r"not eligible",
    r"excluded from",
    r"ineligible",
    r"not be accepted",
)
_UNIT_SYNONYMS = {
    "percent": "%",
    "per cent": "%",
    "pct": "%",
    "us$": "usd",
    "$": "usd",
    "u.s.$": "usd",
    "€": "eur",
    "£": "gbp",
    "yrs": "year",
    "yr": "year",
    "hrs": "hour",
    "hr": "hour",
    "mins": "minute",
    "min": "minute",
    "secs": "second",
    "sec": "second",
    "bbl": "barrel",
    "bbls": "barrel",
    "bpd": "barrel",
    "bopd": "barrel",
}
_UNIT_STOPWORDS = {"and", "or", "of", "the", "to", "in", "for", "a", "an", "with", "by", "on", "at", "per"}


def _norm_unit(unit: str) -> str:
    unit = unit.lower().strip(" .,;:()")
    unit = _UNIT_SYNONYMS.get(unit, unit)
    if len(unit) > 3 and unit.endswith("ies"):
        unit = unit[:-3] + "y"
    elif len(unit) > 3 and unit.endswith("s") and not unit.endswith("ss"):
        unit = unit[:-1]
    return unit


def _bound_for(prefix: str, sentence: str) -> str:
    """Floor, ceiling, or exact, judged by the comparator nearest the number.

    "a minimum gas capacity of 50" and "within twenty-one (21) days" both
    put their cue a few words before the figure; picking the closest cue
    (rather than the first one found anywhere) stops "minimum" earlier in a
    long sentence from governing a later "not more than"."""
    window = prefix[-60:].lower()
    best: tuple[int, int, str] | None = None
    for cue in _MIN_CUES + _MAX_CUES:
        for m in re.finditer(cue, window):
            tail = window[m.end() :]
            # A cue governs the next figure only, and only within a short
            # reach: "minimum in-country value of forty percent (40%)".
            if re.search(r"\d", tail) or len(re.findall(r"[a-z]+", tail)) > 7:
                continue
            candidate = (m.end(), len(cue), cue)
            if best is None or candidate > best:
                best = candidate
    if best is None:
        return "exact"
    cue = best[2]
    if cue in _MAX_CUES:
        return "max"
    # "exceeds 0.50 ... shall not be considered" is a ceiling phrased as a
    # disqualification, not a floor.
    if cue in (r"in excess of", r"greater than", r"more than", r"exceed(?:s|ing)?\b") and contains_any(
        sentence, _REJECTION_CONSEQUENCE
    ):
        return "max"
    return "min"


_MONTHS = {
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
}


_QUANTITY_RE = re.compile(
    rf"(?P<cur>{CURRENCIES})?\s?(?:(?P<word>{NUMBER_WORD_RE})\s)?\(?(?P<num>\d[\d,]*(?:\.\d+)?)\)?"
    r"\s?(?P<scale>million|billion|thousand|mn|bn)?\s?(?P<pct>%|percent\b|per cent\b)?"
    r"\s?(?:calendar\s|business\s|working\s|consecutive\s|full\s|clear\s)?(?P<unit>[A-Za-z][A-Za-z\-]*)?",
    re.I,
)
_WORD_QUANTITY_RE = re.compile(
    rf"\b(?P<word>{NUMBER_WORD_RE})\s(?P<unit>days?|weeks?|months?|years?|hours?|minutes?|seconds?)\b",
    re.I,
)


def quantities(sentence: str) -> list[Quantity]:
    """Numbers in a sentence with their unit and whether the sentence sets
    a floor, a ceiling, or an exact value for them."""
    found: list[Quantity] = []
    text = normalize(sentence)
    for m in _QUANTITY_RE.finditer(text):
        value = parse_number(m.group("num"))
        if value is None:
            continue
        # Clause references ("Clause 8.1") and years ("2026") are not quantities.
        before = text[max(0, m.start() - 12) : m.start()].lower()
        if re.search(r"(clause|article|section|paragraph|form|iso|appendix|schedule|annex)\s*$", before):
            continue
        if m.group("scale"):
            value *= _SCALE[m.group("scale").lower()]
        if m.group("cur"):
            unit = _norm_unit(m.group("cur"))
        elif m.group("pct"):
            unit = "%"
        else:
            raw_unit = (m.group("unit") or "").lower()
            # "0.50 per 200,000 man-hours": the figure is a rate.
            unit = "rate" if raw_unit == "per" else _norm_unit(raw_unit)
            if unit in _UNIT_STOPWORDS or unit in _MONTHS:
                unit = ""
        if not m.group("cur") and not m.group("pct") and 1900 <= value <= 2100 and unit == "":
            continue
        found.append(Quantity(value, unit, _bound_for(text[: m.start()], text), m.group(0).strip()))
    for m in _WORD_QUANTITY_RE.finditer(text):
        value = words_to_number(m.group("word"))
        if value is None or any(q.text.lower().startswith(m.group(0).lower()) for q in found):
            continue
        found.append(
            Quantity(value, _norm_unit(m.group("unit")), _bound_for(text[: m.start()], text), m.group(0))
        )
    return found


def to_days(q: Quantity) -> float | None:
    factors = {"day": 1, "week": 7, "month": 30, "year": 365, "hour": 1 / 24}
    return q.value * factors[q.unit] if q.unit in factors else None


def first_period_days(text: str) -> float | None:
    for q in quantities(text):
        days = to_days(q)
        if days is not None:
            return days
    return None


def first_percent(text: str) -> float | None:
    for q in quantities(text):
        if q.unit == "%":
            return q.value
    return None


# ---------------------------------------------------------------------------
# Negation and hedging
# ---------------------------------------------------------------------------

NEGATIVE_CUES = (
    r"\bnot yet\b",
    r"working towards",
    r"work towards",
    r"\bpending\b",
    r"in progress",
    r"\bexpected\b",
    r"\bintends? to\b",
    r"\bwill (?:obtain|apply|seek|pursue)\b",
    r"applied for",
    r"\bunable to\b",
    r"\bcannot\b",
    r"\bdoes not\b",
    r"\bdo not\b",
    r"\bdid not\b",
    r"\bis not\b",
    r"\bare not\b",
    r"\bno longer\b",
    r"\bnot currently\b",
    r"\bnot held\b",
    r"\bexpired\b",
    r"\blapsed\b",
    r"\bunder review\b",
    r"\bplanned\b",
    r"\bto be provided\b",
    r"\bto follow\b",
    r"\bupon request\b",
    r"on request",
    r"\bnot included\b",
    r"\bnot attached\b",
    r"\bexcluded\b",
    r"\bexempt",
)

QUALIFICATION_CUES = (
    r"\bproposes?\b",
    r"\brequests? that\b",
    r"\bamended\b",
    r"\bsubject to (?:agreement|negotiation|clarification)\b",
    r"\bexcept(?:ion)?s?\b.*\b(?:clause|term|condition)",
    r"\bdeviation",
    r"\bqualif(?:y|ied|ication)",
    r"\bnot accept",
    r"\breserves? the right\b",
    r"\bin lieu of\b",
    r"\binstead of\b",
    r"\bto be agreed\b",
    r"\bnegotiable\b",
    r"\bassumption\b",
    r"\bclarification\b",
    r"\bsubject to\b",
)


def is_negated(sentence: str) -> bool:
    return contains_any(sentence, NEGATIVE_CUES)


def is_qualified(sentence: str) -> bool:
    return contains_any(sentence, QUALIFICATION_CUES)
