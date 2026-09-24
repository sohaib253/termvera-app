from app.services.clauserisk.segmentation import PageText, segment_pages


def test_segments_numbered_clauses_across_pages():
    pages = [
        PageText(
            page_number=1,
            text=(
                "SERVICES AGREEMENT\n"
                "12.3 Limitation of Liability\n"
                "The Contractor's aggregate liability shall not exceed 20% of the Contract Price.\n"
            ),
        ),
        PageText(
            page_number=2,
            text=(
                "Neither party shall be liable for indirect losses.\n"
                "12.4 Indemnity\n"
                "The Contractor shall indemnify the Client against third-party claims.\n"
            ),
        ),
    ]

    segments = segment_pages(pages)

    assert [s.clause_number for s in segments] == ["12.3", "12.4"]
    assert segments[0].title == "Limitation of Liability"
    assert segments[0].page_start == 1
    assert segments[0].page_end == 2  # clause 12.3's body continues onto page 2
    assert "shall not exceed 20%" in segments[0].text
    assert "Neither party shall be liable" in segments[0].text
    assert segments[1].page_start == 2
    assert segments[1].page_end == 2
    assert "indemnify the Client" in segments[1].text


def test_falls_back_to_whole_document_when_no_headers_found():
    pages = [PageText(page_number=1, text="This is a short prose agreement with no numbering at all.")]

    segments = segment_pages(pages)

    assert len(segments) == 1
    assert segments[0].clause_number is None
    assert "prose agreement" in segments[0].text
    assert segments[0].page_start == 1
    assert segments[0].page_end == 1


def test_empty_pages_produce_no_segments():
    assert segment_pages([]) == []


def test_does_not_treat_arbitrary_numbered_sentence_as_header():
    # A line starting with a number but reading as a long sentence (not a
    # short clause title) should not be picked up as a false header.
    pages = [
        PageText(
            page_number=1,
            text=(
                "1. Introduction\n"
                "30 days after signature the parties shall hold a kickoff meeting to review "
                "the project schedule and confirm resource availability for the duration of "
                "this rather long sentence that is not a clause header at all.\n"
            ),
        )
    ]

    segments = segment_pages(pages)

    assert len(segments) == 1
    assert segments[0].clause_number == "1"
    assert "kickoff meeting" in segments[0].text
