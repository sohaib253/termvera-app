"""The TenderGuard brain: a deterministic expert engine for contracts,
tenders, and bids.

No model, no API call, no GPU. It reads a document the way a senior bid
or contracts manager does: sentence by sentence, looking for who owes
what to whom, under what condition, by when, for how much, and what
happens if they fail. The knowledge lives in data (contract_kb.py,
tender_kb.py) so extending it means adding a rule, not writing code.

What it trades away against a large language model: it cannot read
drafting it has no rule for. What it gains: every conclusion traces to a
named rule and a verbatim sentence, the same input always gives the same
answer, and a 34-clause contract is analysed in well under a second.
"""
