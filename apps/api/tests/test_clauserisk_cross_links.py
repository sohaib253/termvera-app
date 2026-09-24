from app.services.clauserisk.cross_links import ClauseForLinking, build_cross_clause_links


def test_explicit_reference_creates_link():
    clauses = [
        ClauseForLinking(
            id="a", clause_number="5.1", text="Payment shall be made per Clause 5.1.", subcategory="payment"
        ),
        ClauseForLinking(
            id="b",
            clause_number="5.2",
            text="As set out in Clause 5.1, invoices are due net 30.",
            subcategory="payment",
        ),
    ]

    links = build_cross_clause_links(clauses)

    explicit = [link for link in links if link.basis == "explicit_reference"]
    assert len(explicit) == 1
    assert {explicit[0].clause_a_id, explicit[0].clause_b_id} == {"a", "b"}


def test_self_reference_is_ignored():
    clauses = [
        ClauseForLinking(
            id="a",
            clause_number="5.1",
            text="Under Clause 5.1, payment is due monthly.",
            subcategory="payment",
        ),
    ]

    links = build_cross_clause_links(clauses)

    assert links == []


def test_reference_to_nonexistent_clause_is_ignored():
    clauses = [
        ClauseForLinking(
            id="a", clause_number="5.1", text="See Clause 99.9 for details.", subcategory="payment"
        ),
    ]

    links = build_cross_clause_links(clauses)

    assert links == []


def test_category_pair_links_liability_and_indemnity():
    clauses = [
        ClauseForLinking(
            id="a", clause_number="12.3", text="Liability capped at 20%.", subcategory="liability_cap"
        ),
        ClauseForLinking(
            id="b",
            clause_number="12.4",
            text="Contractor shall indemnify Client.",
            subcategory="indemnity",
        ),
    ]

    links = build_cross_clause_links(clauses)

    category_links = [link for link in links if link.basis == "category_pattern"]
    assert len(category_links) == 1
    assert category_links[0].relationship_type == "liability_linked_to_indemnity"


def test_category_pair_links_ld_and_milestones():
    clauses = [
        ClauseForLinking(
            id="a",
            clause_number="8.1",
            text="Liquidated damages of $5,000/day.",
            subcategory="liquidated_damages",
        ),
        ClauseForLinking(
            id="b",
            clause_number="8.2",
            text="Milestone completion by 30 June.",
            subcategory="milestones",
        ),
    ]

    links = build_cross_clause_links(clauses)

    assert any(link.relationship_type == "ld_linked_to_completion" for link in links)


def test_unrelated_categories_produce_no_category_link():
    clauses = [
        ClauseForLinking(
            id="a",
            clause_number="1",
            text="Governing law is England and Wales.",
            subcategory="governing_law",
        ),
        ClauseForLinking(
            id="b",
            clause_number="2",
            text="Confidentiality obligations apply.",
            subcategory="confidentiality",
        ),
    ]

    links = build_cross_clause_links(clauses)

    assert links == []


def test_no_duplicate_links_for_same_pair():
    clauses = [
        ClauseForLinking(
            id="a",
            clause_number="12.3",
            text="Liability capped at 20%. See Clause 12.4 for indemnity terms.",
            subcategory="liability_cap",
        ),
        ClauseForLinking(
            id="b",
            clause_number="12.4",
            text="Contractor shall indemnify Client.",
            subcategory="indemnity",
        ),
    ]

    links = build_cross_clause_links(clauses)

    # Both an explicit reference AND a category-pattern match exist between
    # the same pair — they're different relationship types/bases, so both
    # are kept, but neither should be duplicated.
    keys = [(link.clause_a_id, link.clause_b_id, link.relationship_type) for link in links]
    assert len(keys) == len(set(keys))
    assert len(links) == 2
