"""Finding evidence must be findable on paper: right page, printed page
number, section and clause, even on a stamped scan."""

from app.services.clauserisk.evidence_location import ClauseRef, locate_evidence, printed_page_labels
from app.services.clauserisk.segmentation import PageText, segment_pages


def _pages() -> list[PageText]:
    # PDF page 1 is a cover letter; the contract prints "Page N of 3" from
    # PDF page 2. PDF page 3's footer was blotted out by a stamp.
    return [
        PageText(1, "Dear Sir,\nPlease find enclosed the contract."),
        PageText(
            2,
            "SECTION 10. INDEMNITIES:\n"
            "10.1 Neither Party shall be liable for consequential loss.\nPage 1 of 3",
        ),
        PageText(
            3, "10.2 The Contractor shall indemnify the Company against all motions\nand claims.\n~~ stamp ~~"
        ),
        PageText(4, "SECTION 11. PATENTS:\nThe Contractor shall protect the Company.\nPage 3 of 3"),
    ]


def test_printed_page_numbers_are_read_and_gaps_filled():
    labels = printed_page_labels(_pages())

    assert labels == {2: "1 of 3", 3: "2 of 3", 4: "3 of 3"}  # cover letter has none


def test_evidence_is_placed_on_its_real_page_with_section_and_clause():
    pages = _pages()
    refs = [
        ClauseRef(s.clause_number, s.title, s.text, s.page_start, s.page_end) for s in segment_pages(pages)
    ]
    section = next(c for c in refs if c.clause_number == "10")

    # Found through section 10's clause even though the quote is in 10.2.
    where = locate_evidence(
        "The Contractor shall indemnify the Company against all motions",
        home_clause=section,
        clauses=refs,
        pages=pages,
        labels=printed_page_labels(pages),
    )

    assert where.page == 3
    assert where.page_label == "2 of 3"
    assert where.clause_number == "10.2"
    assert where.section_title == "INDEMNITIES"


def test_clause_title_may_open_with_a_quotation_mark():
    segs = segment_pages([PageText(1, '16.1 "Force Majeure" shall mean an unforeseeable event.')])

    assert [s.clause_number for s in segs] == ["16.1"]


def test_misread_and_stamp_covered_clause_numbers_are_recovered():
    text = "\n".join(
        [
            "5.1 Any taxes outside Pakistan are for the Contractor.",
            "",
            "Any taxes in Pakistan are for the Contractor.",  # "5.2" hidden under a stamp
            "",
            "3.3 The Contractor shall pay all taxes on its income.",  # OCR read 5.3 as 3.3
            "",
            "5.4 The Company may deduct tax at source.",
        ]
    )

    segs = segment_pages([PageText(1, text)])

    assert [s.clause_number for s in segs] == ["5.1", "5.2", "5.3", "5.4"]
    assert segs[1].title.startswith("Any taxes in Pakistan")
