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

_HEADER_RE = re.compile(
    r"^(?:(?:article|section|clause)\s+)?"
    r"(\d{1,3}(?:\.\d{1,3}){0,4})"
    r"[\.\):]?\s+"
    r"([A-Z][^\n]{0,120})$",
    re.IGNORECASE,
)


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
    stripped = line.strip()
    if not stripped or len(stripped) > 160:
        return None
    return _HEADER_RE.match(stripped)


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
            header_positions.append((idx, match.group(1), match.group(2).strip()))

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
