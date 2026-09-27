"""Deterministic (non-AI) clause segmentation — pipeline stages 4-5.

Contract text is split into clauses by detecting numbered clause headers
(e.g. "12.3 Limitation of Liability", "Article 5.1", "Clause 14.3:").
This is intentionally simple regex-based heuristics, not an AI call — the
AI should never be deciding what the clause boundaries even are, since
that would make every downstream page/clause citation unverifiable.

Known limitation, stated plainly: this handles conventionally-numbered
clauses well (which is what the generated sample contracts and most
formal commercial/EPC contracts use) but will under-segment contracts
using unconventional structure (lettered sub-clauses, schedules with
their own numbering restarting at 1, purely prose contracts with no
numbering at all). When no headers are found at all, the whole document
becomes one clause rather than failing — see `segment_pages`.
"""

import re
from dataclasses import dataclass

# Only the "Article/Section/Clause" prefix is case-insensitive. The title
# must start with a real capital: that is what separates a clause
# ("4.1 The Contractor ...") from a sentence that merely starts with a
# number ("30 days after signature ..."), now that long lines are allowed.
_HEADER_RE = re.compile(
    r"^(?:(?i:article|section|clause)\s+)?"
    r"(\d{1,3}(?:\.\d{1,3}){0,4})"
    r"[\.\):\-]?\s+"
    # A title may open with a quotation mark: 16.1 "Force Majeure" shall mean...
    r"([\"'“‘(]?[A-Z][^\n]*)$",
)
# Start of a paragraph that could be a clause whose number was lost: a
# capital letter, after any OCR debris a stamp left in the margin ("_ ").
_PARAGRAPH_START = re.compile(r"^[^A-Za-z0-9]{0,3}([A-Z][a-z]+\b.*)$")
_MAX_TITLE_CHARS = 120


@dataclass
class PageText:
    page_number: int
    text: str


@dataclass
class RawClauseSegment:
    sequence_index: int
    clause_number: str | None
    title: str
    text: str
    page_start: int
    page_end: int


def _looks_like_header(line: str) -> re.Match | None:
    # No length cap: PDF text arrives wrapped at page width, but Word, RTF
    # and ODT text arrives one paragraph per line, so a numbered clause
    # ("4.1 The Contractor shall ...") is a single long line there.
    stripped = line.strip()
    if not stripped:
        return None
    return _HEADER_RE.match(stripped)


def _title(text: str) -> str:
    """The clause heading, or, for a clause whose number leads straight into
    its body text, that text's opening words."""
    text = text.strip()
    if len(text) <= _MAX_TITLE_CHARS:
        return text
    return text[:_MAX_TITLE_CHARS].rsplit(" ", 1)[0] + "…"


def segment_pages(pages: list[PageText]) -> list[RawClauseSegment]:
    """Build a flat list of (line_text, page_number) across all pages,
    find header lines, and slice the document into clauses between
    consecutive headers."""
    lines: list[tuple[str, int]] = []
    for page in pages:
        for raw_line in page.text.splitlines():
            lines.append((raw_line, page.page_number))

    header_positions: list[tuple[int, str, str]] = []  # (line_index, number, title)
    for idx, (line, _page) in enumerate(lines):
        match = _looks_like_header(line)
        if match:
            header_positions.append((idx, match.group(1), _title(match.group(2))))

    header_positions = _recover_skipped_numbers(
        _repair_misread_numbers(header_positions), [line for line, _ in lines]
    )

    if not header_positions:
        return _whole_document_as_one_clause(pages)

    segments: list[RawClauseSegment] = []
    for seq, (start_idx, number, title) in enumerate(header_positions):
        end_idx = (
            header_positions[seq + 1][0] if seq + 1 < len(header_positions) else len(lines)
        )
        body_lines = [lines[i][0] for i in range(start_idx, end_idx)]
        page_numbers = [lines[i][1] for i in range(start_idx, end_idx)]
        text = "\n".join(line for line in body_lines if line.strip())
        segments.append(
            RawClauseSegment(
                sequence_index=seq,
                clause_number=number,
                title=title or f"Clause {number}",
                text=text,
                page_start=min(page_numbers),
                page_end=max(page_numbers),
            )
        )
    return segments


def _whole_document_as_one_clause(pages: list[PageText]) -> list[RawClauseSegment]:
    if not pages:
        return []
    full_text = "\n".join(p.text for p in pages)
    return [
        RawClauseSegment(
            sequence_index=0,
            clause_number=None,
            title="Full document (no numbered clauses detected)",
            text=full_text,
            page_start=pages[0].page_number,
            page_end=pages[-1].page_number,
        )
    ]


def _recover_skipped_numbers(
    headers: list[tuple[int, str, str]], lines: list[str]
) -> list[tuple[int, str, str]]:
    """Put back a clause whose number a scan lost.

    On signed contracts a stamp or initials in the margin often cover a
    clause number, so OCR reads "6.1 ..." then the next paragraph with no
    number, then "6.3 ...". Clause 6.2 would silently merge into 6.1, and
    a finding in it would be reported against the wrong clause. When
    sibling numbers skip exactly one (x.k to x.k+2), the first new
    paragraph between them is taken to be the missing x.k+1. Anything less
    certain is left alone.
    """
    recovered: list[tuple[int, str, str]] = []
    for position, (start, number, title) in enumerate(headers):
        recovered.append((start, number, title))
        if position + 1 >= len(headers):
            continue
        next_start, next_number, _ = headers[position + 1]
        parts, next_parts = number.split("."), next_number.split(".")
        if (
            len(parts) < 2
            or len(parts) != len(next_parts)
            or parts[:-1] != next_parts[:-1]
            or int(next_parts[-1]) - int(parts[-1]) != 2
        ):
            continue
        for index in range(start + 2, next_start):
            if lines[index - 1].strip():
                continue  # not the start of a paragraph
            match = _PARAGRAPH_START.match(lines[index].strip())
            if match:
                missing = ".".join(parts[:-1] + [str(int(parts[-1]) + 1)])
                recovered.append((index, missing, _title(match.group(1))))
                break
    return recovered


def _repair_misread_numbers(headers: list[tuple[int, str, str]]) -> list[tuple[int, str, str]]:
    """Fix a clause number OCR misread, when its neighbours make it certain.

    A scan reads "5.3" as "3.3" (or "S.3"): between 5.1 and 5.4, a
    same-depth number with a different section but a fitting last part can
    only be 5.3. Anything the neighbours don't pin down is left as read.
    """
    repaired = list(headers)
    for i in range(1, len(repaired) - 1):
        _, before, _ = repaired[i - 1]
        index, number, title = repaired[i]
        _, after, _ = repaired[i + 1]
        b, n, a = before.split("."), number.split("."), after.split(".")
        if not (len(n) >= 2 and len(b) == len(n) == len(a)):
            continue
        if b[:-1] != a[:-1] or n[:-1] == b[:-1]:
            continue
        if int(b[-1]) < int(n[-1]) < int(a[-1]):
            repaired[i] = (index, ".".join(b[:-1] + [n[-1]]), title)
    return repaired
