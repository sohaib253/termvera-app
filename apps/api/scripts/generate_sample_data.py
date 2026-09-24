"""Renders every fictional sample PDF from app/services/sample_content.py.

Not a runtime dependency of the API. Run manually after editing
sample_content.py:

    pip install fpdf2==2.8.2
    python scripts/generate_sample_data.py

Alongside the PDFs it writes sample_data/manifest.json recording the page
each clause landed on. app/services/demo_fixtures.py reads that manifest
instead of hard-coding page numbers, so the demo project's "page N"
citations stay correct when the documents are re-rendered.

Clause blocks are kept whole on a page (see `_ensure_space`): the demo's
excerpt verification checks an excerpt against a single page's extracted
text, so a clause split across a page boundary would be unverifiable
through no fault of the analysis.
"""

import json
import sys
from pathlib import Path

from fpdf import FPDF

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.sample_content import (  # noqa: E402
    AMENDMENT_CLAUSES,
    AMENDMENT_PREAMBLE,
    AMENDMENT_SUBTITLE,
    AMENDMENT_TITLE,
    BID_BIDDER,
    BID_PREAMBLE,
    BID_SECTIONS,
    BID_SUBTITLE,
    BID_TITLE,
    CONTRACT_CLAUSES,
    CONTRACT_PARTIES,
    CONTRACT_REFERENCE,
    CONTRACT_TITLE,
    TENDER_CLIENT,
    TENDER_PREAMBLE,
    TENDER_REFERENCE,
    TENDER_SECTIONS,
    TENDER_SUBTITLE,
    TENDER_TITLE,
    Clause,
    Section,
)

OUT_DIR = Path(__file__).resolve().parent.parent.parent.parent / "sample_data"

TENDER_FILENAME = "offshore-well-testing-tender.pdf"
BID_FILENAME = "apex-well-services-bid.pdf"
CONTRACT_FILENAME = "offshore-well-testing-contract.pdf"
AMENDMENT_FILENAME = "offshore-well-testing-contract-amendment-1.pdf"
MANIFEST_FILENAME = "manifest.json"

BODY_SIZE = 10.5
LINE_HEIGHT = 5.4
BOTTOM_MARGIN = 22


class Document(FPDF):
    def __init__(self, running_header: str) -> None:
        super().__init__(format="A4")
        self.running_header = running_header
        self.set_auto_page_break(auto=True, margin=BOTTOM_MARGIN)
        self.set_margins(22, 20, 22)

    def header(self) -> None:
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "", 8)
        self.set_text_color(120)
        self.cell(0, 6, self.running_header, align="L")
        self.ln(8)
        self.set_text_color(0)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(120)
        self.cell(0, 6, f"Page {self.page_no()}", align="C")
        self.set_text_color(0)


def _write(pdf: FPDF, height: float, text: str) -> None:
    pdf.multi_cell(0, height, text, new_x="LMARGIN", new_y="NEXT")


def _ensure_space(pdf: Document, text: str) -> None:
    """Break to a new page rather than split a clause across two.

    Estimates wrapped height from the usable line width; an overestimate
    only costs a little whitespace, whereas an underestimate would split a
    clause and break excerpt verification."""
    usable_width = pdf.w - pdf.l_margin - pdf.r_margin
    chars_per_line = max(int(usable_width / (BODY_SIZE * 0.20)), 40)
    estimated_lines = len(text) / chars_per_line + 2
    needed = estimated_lines * LINE_HEIGHT + 8
    if pdf.get_y() + needed > pdf.h - BOTTOM_MARGIN:
        pdf.add_page()


def _title_block(pdf: Document, title: str, subtitle: str, meta: str, preamble: str) -> None:
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 17)
    _write(pdf, 8, title)
    pdf.set_font("Helvetica", "B", 12)
    _write(pdf, 7, subtitle)
    pdf.ln(1)
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(90)
    _write(pdf, 5, meta)
    pdf.set_text_color(0)
    pdf.ln(3)
    pdf.set_font("Helvetica", "", BODY_SIZE)
    _write(pdf, LINE_HEIGHT, preamble)
    pdf.ln(4)


def _section_heading(pdf: Document, number: str, title: str) -> None:
    _ensure_space(pdf, title * 3)
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 11.5)
    _write(pdf, 6.5, f"{number}. {title.upper()}")
    pdf.set_draw_color(190)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.set_draw_color(0)
    pdf.ln(2.5)


def _clause_block(pdf: Document, clause: Clause, pages: dict[str, int]) -> None:
    _ensure_space(pdf, clause.text)
    pages[clause.number] = pdf.page_no()
    pdf.set_font("Helvetica", "B", BODY_SIZE)
    _write(pdf, LINE_HEIGHT, f"{clause.number} {clause.title}")
    pdf.set_font("Helvetica", "", BODY_SIZE)
    _write(pdf, LINE_HEIGHT, clause.text)
    pdf.ln(2.5)


def _render_sections(
    pdf: Document, sections: tuple[Section, ...], pages: dict[str, int]
) -> None:
    for section in sections:
        _section_heading(pdf, section.number, section.title)
        for clause in section.clauses:
            _clause_block(pdf, clause, pages)


def build_tender() -> tuple[FPDF, dict[str, int]]:
    pdf = Document(f"{TENDER_REFERENCE} - {TENDER_SUBTITLE}")
    pages: dict[str, int] = {}
    _title_block(
        pdf,
        TENDER_TITLE,
        TENDER_SUBTITLE,
        f"Reference: {TENDER_REFERENCE}   |   Issued by: {TENDER_CLIENT}   |   Issue date: 1 April 2026",
        TENDER_PREAMBLE,
    )
    _render_sections(pdf, TENDER_SECTIONS, pages)
    return pdf, pages


def build_bid() -> tuple[FPDF, dict[str, int]]:
    pdf = Document(f"{BID_BIDDER} - Proposal for {TENDER_REFERENCE}")
    pages: dict[str, int] = {}
    _title_block(
        pdf,
        BID_TITLE,
        BID_SUBTITLE,
        f"Submitted by: {BID_BIDDER}   |   In response to: {TENDER_REFERENCE}   |   Date: 28 April 2026",
        BID_PREAMBLE,
    )
    _render_sections(pdf, BID_SECTIONS, pages)
    return pdf, pages


def build_contract() -> tuple[FPDF, dict[str, int]]:
    pdf = Document(f"{CONTRACT_REFERENCE} - {CONTRACT_TITLE.title()}")
    pages: dict[str, int] = {}
    _title_block(
        pdf,
        CONTRACT_TITLE,
        f"Contract Reference {CONTRACT_REFERENCE}",
        "Effective date: 1 June 2026",
        CONTRACT_PARTIES,
    )
    for clause in CONTRACT_CLAUSES:
        _clause_block(pdf, clause, pages)
    return pdf, pages


def build_amendment() -> tuple[FPDF, dict[str, int]]:
    pdf = Document(f"{CONTRACT_REFERENCE} - Amendment No. 1")
    pages: dict[str, int] = {}
    _title_block(
        pdf,
        AMENDMENT_TITLE,
        AMENDMENT_SUBTITLE,
        "Amendment date: 14 May 2026",
        AMENDMENT_PREAMBLE,
    )
    for clause in AMENDMENT_CLAUSES:
        _clause_block(pdf, clause, pages)
    return pdf, pages


if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, dict[str, int]] = {}

    for filename, builder in (
        (TENDER_FILENAME, build_tender),
        (BID_FILENAME, build_bid),
        (CONTRACT_FILENAME, build_contract),
        (AMENDMENT_FILENAME, build_amendment),
    ):
        pdf, pages = builder()
        pdf.output(str(OUT_DIR / filename))
        manifest[filename] = pages
        print(f"Wrote {filename} ({pdf.page_no()} pages, {len(pages)} clauses)")

    (OUT_DIR / MANIFEST_FILENAME).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {MANIFEST_FILENAME}")
