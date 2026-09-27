"""Where exactly a finding's quoted evidence sits, in terms a reader can use.

"Page 8" alone proved unusable. It was the page the clause *started* on,
not where the quote is. It was the PDF's own page count, which disagrees
with the contract's printed page numbers whenever a cover letter or stamp
paper page comes first: a signed OGDCL contract's PDF page 8 is its
printed "Page 7 of 12". And it gave no clause or section to look for.

So each quote is located by its text, and described three ways: the PDF
page (what the viewer's page box and "open at page" use), the printed page
label found on that page, and the section and clause it belongs to.
"""

import re
from dataclasses import dataclass

from app.services.clauserisk.segmentation import PageText

# "Page 7 of 12", "Page 7/12", "page 7" as printed in a header or footer.
_PAGE_LABEL = re.compile(r"\bpage\s+(\d{1,4})\s*(?:(?:of|/)\s*(\d{1,4}))?\b", re.IGNORECASE)
# Enough of the quote to find it, short enough to survive the quote
# running over a page break or an OCR slip further in.
_PROBE_CHARS = 60


@dataclass(frozen=True)
class ClauseRef:
    clause_number: str | None
    title: str
    text: str
    page_start: int
    page_end: int


@dataclass(frozen=True)
class EvidenceLocation:
    page: int | None
    page_label: str | None
    clause_number: str | None
    clause_title: str | None
    section_title: str | None


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def printed_page_labels(pages: list[PageText]) -> dict[int, str]:
    """PDF page number -> the page number printed on it, where there is one.

    Only an explicit "Page N" counts: a bare number at the foot of a page
    is too easily a clause number or an amount to trust."""
    found: dict[int, tuple[int, int | None]] = {}
    for page in pages:
        lines = [line for line in page.text.splitlines() if line.strip()]
        # Headers and footers: look at the edges of the page first.
        for line in lines[-6:] + lines[:4]:
            match = _PAGE_LABEL.search(line)
            if match:
                number, total = match.groups()
                found[page.page_number] = (int(number), int(total) if total else None)
                break

    labels = {pdf: _label(number, total) for pdf, (number, total) in found.items()}

    # On a scan, a stamp or signature often blots out a footer or two.
    # When most detected labels agree on one offset from the PDF page
    # (cover letter first: printed = PDF page - 1), fill the gaps with it,
    # within the printed page range.
    if len(found) >= 2:
        offsets = [pdf - number for pdf, (number, _) in found.items()]
        offset = max(set(offsets), key=offsets.count)
        if offsets.count(offset) >= 0.75 * len(offsets):
            totals = {total for _, total in found.values() if total}
            total = totals.pop() if len(totals) == 1 else None
            for page in pages:
                number = page.page_number - offset
                if page.page_number not in labels and number >= 1 and (total is None or number <= total):
                    labels[page.page_number] = _label(number, total)
    return labels


def _label(number: int, total: int | None) -> str:
    return f"{number} of {total}" if total else str(number)


def locate_evidence(
    excerpt: str,
    *,
    home_clause: ClauseRef,
    clauses: list[ClauseRef],
    pages: list[PageText],
    labels: dict[int, str],
) -> EvidenceLocation:
    probe = _norm(excerpt)[:_PROBE_CHARS]

    clause = home_clause
    if probe and probe not in _norm(home_clause.text):
        # The quote came from a related clause given as context.
        clause = next((c for c in clauses if probe in _norm(c.text)), home_clause)

    page_number: int | None = clause.page_start
    if probe:
        in_range = [p for p in pages if clause.page_start <= p.page_number <= clause.page_end]
        found = next((p for p in in_range if probe in _norm(p.text)), None)
        if found is None:
            found = next((p for p in pages if probe in _norm(p.text)), None)
        if found is not None:
            page_number = found.page_number

    return EvidenceLocation(
        page=page_number,
        page_label=labels.get(page_number) if page_number is not None else None,
        clause_number=clause.clause_number,
        clause_title=_clean_title(clause.title),
        section_title=_section_title(clause, clauses),
    )


def _clean_title(title: str | None) -> str | None:
    if not title:
        return None
    title = title.strip()
    # An upper-case heading with a scrap of lower-case OCR debris after it
    # ("LIQUIDATED DAMAGES: fs", initials in the margin): drop the scrap.
    heading = re.match(r"^([^a-z]*[A-Z][^a-z]*?)[\s:;.,]+[a-z]{1,3}$", title)
    if heading:
        title = heading.group(1)
    return title.rstrip(":;.,").strip() or None


def _section_title(clause: ClauseRef, clauses: list[ClauseRef]) -> str | None:
    """For clause 10.2, the heading of section 10 ("INDEMNITIES")."""
    if not clause.clause_number:
        return None
    top = clause.clause_number.split(".")[0]
    if top == clause.clause_number:
        return _clean_title(clause.title)
    parent = next((c for c in clauses if c.clause_number == top), None)
    return _clean_title(parent.title) if parent else None
