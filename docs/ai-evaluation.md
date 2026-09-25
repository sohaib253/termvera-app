# AI evaluation (current state)

## Default engine: the built-in brain (no external AI)

Both modules now default to a deterministic expert engine in
`apps/api/app/services/brain/` (`TENDERGUARD_AI_PROVIDER=brain`,
`CLAUSERISK_AI_PROVIDER=brain`). It calls no model and no API and needs no
GPU, so it runs on any host, including free tiers. Claude and Ollama
remain selectable through the same provider protocol.

**What it is:** a knowledge base written from the contractor's side of the
table (`contract_kb.py`: 91 risk rules across 81 clause types and 79 risk
types, plus 17 contract-wide "missing protection" checks; `tender_kb.py`:
requirement language, categories, and anchor concepts), driven by a
reasoning layer (`text.py`) that reads numbers with their units and
comparators ("not less than USD 10,000,000", "exceeds 0.50 ... shall not be
considered"), tells a look-back window ("within the last 5 years") from a
figure to match, detects hedged or prospective language ("working
towards", "on request"), and detects qualifications ("proposes", "requests
that ... be amended").

**Measured on the sample documents** (`tests/test_brain.py`):

| | Local LLM (mistral 7B) | Brain |
|---|---|---|
| 34-clause contract, end to end | 1 hr 56 min | 2.4 s (live server) |
| Distinct risk types in findings | collapsed (41 of 61 on one type) | 44 |
| Citations failing verbatim check | some, kept but flagged | 0 |
| Tender assessments matching the expert fixtures | not measured | 15 of 15 |
| Unchanged clause flagged as modified in comparison | yes (8.2) | no |

It also makes distinctions experienced bid teams make and a naive keyword
match wouldn't: a procedural instruction (submission deadline) is marked
pending verification rather than failed; a contract-stage obligation
(incident reporting during the works) isn't treated as a bid gap; a bid
that proposes a different payment term is a deviation, not an omission.

**Honest limits:** it only understands drafting it has a rule for. Unusual
wording for a familiar risk can be missed, and it has no judgement beyond
its rules. Every finding names its rule (`[rule LIA-05]`) so a miss or a
false positive can be traced and the rule fixed, and extending coverage
means adding a rule to the knowledge base, not retraining anything. The
15/15 agreement is against the same sample documents the rules were tuned
on; it is a regression guard, not an accuracy claim for unseen contracts.
Before claiming accuracy on real documents, build a labelled set from real
tenders and contracts as described below.

## What has been verified

- **Deterministic validation logic is tested**: the excerpt-verification
  check in `app/services/analysis.py` (`_excerpt_is_verifiable`) — which
  discards any AI-cited excerpt that isn't an actual substring of the
  source document text — is exercised by the demo data pipeline, since
  every demo excerpt was verified against real PyMuPDF-extracted text
  before being hand-authored (see `app/services/demo_fixtures.py`'s
  module docstring and `scripts/print_sample_pdf_text.py`).
- **The structured-output schemas** (`app/schemas/ai.py`,
  `app/services/ai/schemas_json.py`) are validated by Pydantic on every
  use; a response that doesn't match is rejected and retried once
  (`ClaudeProvider._call`), then surfaces as a clear `analysis_status:
  failed` with an error message rather than a silent bad result.

## What has NOT been verified — no ANTHROPIC_API_KEY was available in this environment

- **`ClaudeProvider` has never made a real API call.** The code follows
  the documented Claude API structured-output pattern
  (`output_config: {format: {type: "json_schema", ...}}` on
  `client.messages.create`, per the current `anthropic` 1.7.0 SDK), and
  `mypy` type-checks the call against the SDK's actual overloads — but
  that is not the same as confirming real extraction/assessment quality.
- **No accuracy metrics exist.** Requirement recall/precision, evidence
  citation accuracy, unsupported-evidence rate, and numerical-mismatch
  detection (brief §19) all require running against real tender/bid
  documents with a real API key and manually-labeled expected output.
  None of that has happened yet.

## Before claiming real-project AI accuracy

1. Set `ANTHROPIC_API_KEY` (and optionally `ANTHROPIC_MODEL`, default
   `claude-opus-5`) in `apps/api/.env`.
2. Upload a real (or realistic non-fictional-but-non-confidential) tender
   + bid pair to a project and run `POST /api/projects/{id}/analysis`.
3. Manually review every extracted requirement and assessment against the
   source PDFs — specifically checking: did it invent anything not in the
   text; did it correctly flag numeric mismatches; did ambiguous clauses
   get marked `extraction_uncertain` / `requires_human_review` rather than
   forced into a confident answer.
4. Build a small labeled evaluation set from that review (expected
   extraction, expected mandatory classification, expected assessment per
   requirement) before making any accuracy claim to a customer, per
   brief §19.

Do not advertise an accuracy percentage until step 4 has actually been
done against a defined evaluation dataset.

## ClauseRisk — verified live against a real local Ollama model

Unlike the TenderGuard path above, ClauseRisk's local-model path (the
default: `CLAUSERISK_AI_PROVIDER=ollama`, `mistral:7b-instruct` via
`http://localhost:11434`) **has** been run end-to-end against a real,
running model — not a fake/fixture provider — during this build. What
that verification actually found, and how the pipeline was shaped in
response:

- **Latency**: roughly 60-90 seconds per AI call on this local hardware.
  The pipeline makes two calls per clause (extraction, then risk
  analysis) plus one contract-wide "missing protections" call, so a
  10-clause contract takes ~15-17 minutes end to end. This is why the
  pipeline makes two *separate, simpler* calls per clause rather than one
  combined call — an earlier combined-schema version regularly exceeded a
  90-second timeout.
- **Structured-output quality with a 7B local model needed real tuning**,
  found empirically, not assumed:
  - A bare JSON schema produced garbage in `dates`/`percentages` fields
    (clause fragments instead of real values). Fixed with per-field
    `description`s in the schema and `temperature: 0.1`.
  - Independent `category` + `subcategory` AI fields produced mismatched
    pairs. Fixed by removing `category` from the AI schema entirely and
    deriving it deterministically from `subcategory`
    (`risk_categories.py::category_for_subcategory`) — see
    `docs/architecture.md` §7.
  - The `insurance_limits` subcategory was still confused with
    `liability_cap` after that fix, because both are triggered by "shall
    not exceed X" language. Fixed by renaming the subcategory (it was
    `limits`) to be lexically distinct and adding explicit disambiguation
    text to the prompt (`prompts/clause_extraction/v1.md`).
  - Evidence excerpts from the local model aren't always strictly
    verbatim (light paraphrasing, inserted "..."). The pipeline keeps the
    finding but marks its evidence unverified (empty `evidence` list,
    surfaced honestly in the UI) rather than dropping the finding
    outright — the same "prefer transparency over deletion" instinct as
    TenderGuard's evidence-drop-with-a-note behavior, adapted because
    ClauseRisk findings are worth surfacing even when their cited excerpt
    can't be confirmed.
- **A real correctness bug was caught by this live run, not by the fake-
  provider test suite**: re-running analysis on an already-analyzed
  contract version duplicated every clause and finding, because the
  pipeline only ever appended rows. This surfaced because a real 15-17
  minute run got interrupted by a server restart and was re-triggered —
  the fake-provider tests, which always start from an empty database,
  never exercised the re-run path. Fixed in both ClauseRisk's and
  TenderGuard's pipelines; see `docs/architecture.md` §7 for the full
  writeup and regression tests. **This is the concrete argument for
  testing against a real, slow model at least once** — deterministic
  fixture-based tests are fast and necessary but will not catch every
  class of bug, particularly ones that only appear at real latency or on
  a second run.
- **Contract comparison, verified against two real analyzed versions of
  the sample contract**: the deterministic diff correctly caught every
  genuine change (a payment-term date change, a liability-cap percentage
  change with `financial_delta` populated, an added insurance clause, and
  five clauses present only in the base version) and correctly showed
  zero change for the two clauses whose text is identical between
  versions. It also surfaced one honest limitation: a clause whose text
  is byte-for-byte identical between versions (8.2, Liquidated Damages)
  was flagged as "modified" anyway, because the two independent AI
  extraction passes (v1's and v2's) didn't format the same dollar amount
  identically (`"5,000"` extracted as an amount in one pass, not the
  other). The comparison itself is fully deterministic — this is AI
  extraction inconsistency leaking into a downstream deterministic step,
  not a bug in the diff logic. Worth knowing before trusting a "no
  changes" or "N changes" count at face value on a real contract.
- **A realistic 34-clause contract took 1 hour 56 minutes** end to end on
  this hardware (69 model calls). All 34 clauses segmented, and clause
  classification was mostly sound: mobilisation, weather, client-furnished
  items, tax, currency, and milestones all landed on the right
  subcategory. Misses were real but localised (Scope of Services read as
  `termination_for_cause`, Set-Off as `liability_cap`). Practical
  consequence: a local 7B model is fine for evaluating the pipeline, but a
  contract review that takes two hours is not a workflow a reviewer will
  wait on. A cloud provider is the answer for real use, which is why the
  provider abstraction exists.
- **Enum-constrained output guarantees valid values, not discriminating
  ones.** Constraining `risk_type` to a 50-value enum fixed the garbage
  ("explicit", "uncertainty") described above, but on that run 41 of 61
  findings collapsed onto a single early enum entry
  ("liability_cap_low"), against only 4 clauses actually classified as
  `liability_cap`. A small model asked to choose from a long flat list
  gravitates to the head of it. **Recommended next step, not yet built:**
  pass only the risk types belonging to the clause's own category (plus a
  few cross-cutting ones) instead of all 50, so the choice is both shorter
  and semantically scoped. That needs an extra argument on
  `AIProvider.analyze_clause_risk` and a per-call schema, so it is a
  deliberate change rather than a tweak.
- **What was not measured**: no accuracy/precision-recall numbers exist
  for clause classification or risk-finding quality — the same caveat as
  TenderGuard above applies. The verification here is "the pipeline runs
  correctly against a real model and produces plausible, evidence-checked
  output," not "the output is accurate enough for a real negotiation."
  `ClauseRiskClaudeProvider` (the cloud path) has not been run against a
  live key at all.
