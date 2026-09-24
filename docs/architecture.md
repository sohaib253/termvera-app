# TenderGuard — Architecture & Roadmap

## 0. Repository assessment (Phase 0)

This is a greenfield project. The repository was created fresh at
`C:\Users\siqbal2\tenderguard` (previously the working directory was the
user's home folder, which held unrelated personal files — the project was
moved into its own git repo to avoid mixing the two).

Local environment discovered during inspection:

| Tool | Status |
|---|---|
| Python | 3.11.9 (`AppData\Local\Programs\Python\Python311`) |
| Node.js | v24.12.0 |
| PostgreSQL | 14.x installed locally (`C:\Program Files\PostgreSQL\14`) |
| Docker | Not installed — docker-compose files are provided for later use, but local dev in the meantime runs against the native Postgres 14 install |
| Git | Available; repo initialized for this project |

Because Docker isn't available yet, Phase 1 targets **native local
execution**: FastAPI run with `uvicorn`, Next.js run with `next dev`, and
Postgres via the existing local install. `docker-compose.yml` is still
written and kept current so the team can switch to it the moment Docker is
available, but it is not the tested path for this milestone.

## 1. Stack decisions

Per the project brief, using the recommended stack as-is (no existing code
to reconcile with):

- **Backend**: FastAPI + Pydantic v2 + SQLAlchemy 2.0 (async) + Alembic + PostgreSQL.
- **Frontend**: Next.js (App Router) + TypeScript + Tailwind CSS + shadcn/ui + TanStack Query + React Hook Form + Zod.
- **AI provider**: Claude API, behind a provider-agnostic interface (`AIProvider` protocol) so evaluation/swap-out doesn't require touching call sites. No AI calls are implemented until Phase 3 — Phase 1 has no fabricated AI output.
- **Auth**: JWT access/refresh tokens issued by the API itself for the MVP (no third-party IdP yet — documented as a Phase 8 hardening item). Passwords hashed with `bcrypt` via `passlib`.
- **Migrations**: Alembic from day one, so the schema evolves through reviewable migration files rather than `create_all` in production paths.

## 2. Monorepo layout

```
tenderguard/
├── apps/
│   ├── web/            Next.js frontend
│   └── api/             FastAPI backend
│       └── app/
│           ├── api/          route modules
│           ├── core/          config, security, logging
│           ├── db/            engine/session, base model
│           ├── models/        SQLAlchemy ORM models
│           ├── schemas/       Pydantic request/response models
│           ├── services/      business logic (incl. services/ai/ provider abstraction)
│           ├── repositories/  unused — CRUD lives directly in services/ (YAGNI; revisit if it grows)
│           └── workers/       unused — background work runs via FastAPI BackgroundTasks instead (see §5)
│       └── storage/            uploaded document files, gitignored, created on first upload
├── packages/
│   ├── shared-types/    unused — the web app hand-keeps app/web/lib/types.ts in sync with the API schemas instead (small enough not to need codegen yet)
│   └── ai-contracts/    unused — AI I/O contracts live in apps/api/app/schemas/ai.py (single consumer; not worth a separate package yet)
├── prompts/              versioned prompt modules — requirement_extraction/v1.md, compliance_assessment/v1.md
├── sample_data/           generated fictional tender + bid PDFs (apps/api/scripts/generate_sample_data.py)
├── docs/
├── scripts/
└── docker-compose.yml
```

## 3. Roadmap status

| Phase | Scope | Status |
|---|---|---|
| 0 | Repo inspection, planning | **Done** (this document) |
| 1 | Foundation: app shell, DB, auth, org/project model, nav, logging, error handling, migrations, test setup | **Done** |
| 2 | Document ingestion: upload, extraction, OCR fallback, viewer | **Done** |
| 3 | AI requirement extraction | **Done, code-complete — untested against a live key** (see docs/ai-evaluation.md) |
| 4 | Evidence matching & assessment | **Done, code-complete — untested against a live key** (see docs/ai-evaluation.md) |
| 5 | Compliance workspace (matrix, filters, detail panel) | **Done** |
| 6 | Exports + demo mode | **Done** |
| 7 | Licensing foundation | **Done** (local fixture, real limit enforcement — see docs/licensing.md) |
| 8 | Production hardening | Not started |
| 9 | Desktop distribution | Not started (explicit user decision — see §6 below) |
| — | ClauseRisk module (contract risk analysis, second module in this platform) | **Done** — see §7 below |

## 4. Phase 1 definition of done — STATUS: done, verified 2026-09-21

- `apps/api` runs locally with `uvicorn`, connects to Postgres, and exposes:
  `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/refresh`,
  `GET /api/me` (user + organization), `POST/GET /api/projects`,
  `GET/PATCH /api/projects/{id}`. (Registration creates the organization —
  there's no separate organization CRUD endpoint yet; not required by the
  Phase 1 scope.)
- Alembic migration produces the initial schema: `organizations`, `users`,
  `memberships`, `projects`. Applied to a local Postgres 14 `tenderguard` db.
- Passwords hashed (bcrypt); JWT auth (30 min access / 7 day refresh) guards
  all non-auth routes; every project is scoped to the caller's organization,
  re-verified against the `memberships` table on every request (defense in
  depth beyond trusting the JWT claim) — tenant isolation from day one.
- Structured logging configured; unhandled errors return a consistent
  `{"error": {"message", "request_id"}}` JSON shape instead of raw tracebacks.
- `apps/web` (Next.js 16 / React 19) runs locally with `next dev`, has the
  application shell (sidebar nav per §6 of the brief, with not-yet-built
  sections visibly disabled rather than dead links), landing page, login
  and register pages, dashboard with a real empty state, and a working
  "create project" flow backed by the real API (no mocked data). Project
  detail page supports status transitions and honestly states that
  document upload/AI analysis aren't built yet.
- Verified: `pytest` (14/14 passing), `ruff check`, `mypy` all clean on the
  backend; `tsc --noEmit` and `eslint` clean on the frontend; and a full
  browser-driven pass (Playwright) through register → dashboard → create
  project → status change → back to dashboard, against the live API and a
  real Postgres database, with zero browser console errors.
- `docs/setup.md` lets a new developer get the stack running from a clean
  checkout.

## 5. Phases 2–7 definition of done — STATUS: done, verified 2026-09-21

Built in one push per explicit user direction ("complete all and let's
launch the software"), with two scope decisions made up front by the user:
AI phases (3/4) ship in **demo mode** (precomputed sample data behind a
real, swappable `AIProvider` interface) rather than blocked on an API key;
desktop distribution (Phase 9) is explicitly skipped.

**Phase 2 — Document ingestion**
- `documents` / `document_pages` tables; local filesystem storage under
  `apps/api/storage/` (gitignored), PDF-only, 50MB limit.
- Real PyMuPDF extraction per page, run via FastAPI `BackgroundTasks` (not
  blocking the upload request). Low-text pages are flagged
  (`extraction_method`: `native` / `ocr` / `ocr_unavailable` /
  `ocr_failed`) rather than silently treated as empty — OCR itself
  (`pytesseract`) only activates if a `tesseract` binary is present, which
  it was not in this dev environment (`choco install` failed: no admin
  rights, no sudo escalation attempted), so `ocr_unavailable` is the
  honestly-reported path here.
- Frontend: upload panel with document-type selector, live status
  polling, and a PDF viewer opened via an authenticated blob fetch (the
  file endpoint requires a bearer token, so a plain `<a href>` can't be
  used) with `#page=N` deep-linking.

**Phases 3–4 — AI extraction, evidence matching, compliance assessment**
- `AIProvider` protocol (`app/services/ai/provider.py`) with a real
  `ClaudeProvider` implementation: versioned prompts
  (`prompts/requirement_extraction/v1.md`,
  `prompts/compliance_assessment/v1.md`) that explicitly instruct the
  model to treat document text as untrusted, cite only verbatim excerpts,
  and use `unclear`/`requires_human_review` rather than guessing.
  Structured output via the current `anthropic` 1.7.0 SDK's
  `output_config: {format: {type: "json_schema", ...}}`, validated against
  hand-written JSON schemas, with one retry on invalid JSON.
- **Deterministic validation stage** (`app/services/analysis.py`):
  every AI-cited excerpt is checked as an actual substring of the source
  page text (whitespace-normalized) before being persisted — an
  unverifiable requirement excerpt is dropped, an unverifiable evidence
  excerpt is discarded with a note in the assessment reason. This is what
  stands between an AI hallucination and a false "evidence found" result.
- `POST /api/projects/{id}/analysis` requires `ANTHROPIC_API_KEY`; without
  it, returns `400` with a clear message pointing at the demo project —
  it does **not** silently fall back to fabricated results on real
  projects.
- **Demo mode** (`app/services/demo.py`, `app/services/demo_fixtures.py`):
  a separate, explicit seeding path — not a fallback `AIProvider` — that
  creates a fictional "Offshore Well Testing Services Package" project,
  generates+extracts two real PDFs (`scripts/generate_sample_data.py`),
  and attaches 10 hand-authored requirements whose every excerpt is a
  verbatim substring of the real extracted text (re-verifiable via
  `scripts/print_sample_pdf_text.py`). Deliberately covers the full status
  range brief §14/§28 ask for: compliant-looking, partially addressed,
  evidence not found (including a missing mandatory form → `critical`
  priority), potential non-compliance, an indicative/negotiable clause,
  and one already-`human_verified` item with a seeded audit-trail entry.
- Priority is computed by a small documented lookup table
  (`app/services/priority.py`) keyed on (mandatory_status, assessment
  status) — not an LLM judgment call.

**Phase 5 — Compliance workspace**
- `GET /api/projects/{id}/requirements` with server-side filters (status,
  mandatory_status, priority, reviewer_status, search) and
  `GET/POST /api/requirements/{id}` (+`/review`) for the detail panel and
  review actions.
- Frontend: filterable/searchable matrix with status/priority badges,
  requirement detail page (source excerpt, assessment reasoning, evidence
  list with "open source document" deep links, missing-information list),
  and a review form that changes status and/or adds a comment, both
  captured in an audit-trail (`review_actions`) rendered on the page.
- **Regression caught and fixed during this build**: the review endpoint
  initially returned an empty `review_actions` list in the same response
  that just created one — a SQLAlchemy identity-map staleness bug (fixed
  by appending through the relationship instead of `db.add()` with a bare
  FK, see `app/services/requirement.py`). A dedicated regression test
  (`tests/test_requirements.py::test_review_action_appears_immediately_in_response`)
  now guards this.

**Phase 6 — Exports + demo mode**
- `GET /api/projects/{id}/exports/compliance-matrix.xlsx` (openpyxl):
  Summary sheet, Compliance Matrix sheet (frozen header, autofilter,
  status-colored cells, wrapped text), Assumptions & Limitations sheet.
  Generated synchronously on request — no export-job table (documented
  MVP simplification; fine at current data volumes).
- "Try the sample project" entry points on the dashboard (empty state +
  header) and requirement/matrix pages carry a persistent "Sample data —
  fictional" banner.

**Phase 7 — Licensing foundation**
- `license_accounts` / `usage_events` tables; every org gets a `demo` plan
  lazily. Real enforcement (not just display) on project count, monthly
  document uploads, and monthly analysis runs — `402 Payment Required`
  with a clear message when exceeded. `GET /api/license`, `GET /api/usage`,
  shown live in the topbar. See `docs/licensing.md` for exactly what this
  is not (no signed tokens, no payment integration, no remote validation).

**Verified across all of the above**: 26/26 backend tests pass (added 12
new tests: documents, demo seeding, license limits, requirement review —
including the regression test above), `ruff` and `mypy` clean on the
full `apps/api` tree, `tsc --noEmit` and `eslint` clean on `apps/web`,
and two full Playwright browser passes with zero console errors covering
register → load demo → compliance matrix → filter → open requirement →
override status with comment → verify audit trail → back to matrix →
project detail → document list.

Also completed as part of this push: upgraded the pinned `anthropic` SDK
from `0.42.0` (pre-1.x, didn't recognize current model IDs or
`output_config`) to `1.7.0` via the SDK's own documented 0.x→1.x migration
process — zero call-site changes were needed since the code already used
the current `output_config` syntax rather than the deprecated
`output_format` dict form.

## 6. Explicit scope decisions and non-goals

- **Desktop distribution (Phase 9): not started, by user decision.**
  Building it would need a Rust/Tauri toolchain install and can't produce
  signed installers without certificates the user would need to provide —
  matches the brief's own guidance (§16) not to let desktop packaging
  block validating the product. The web app's API/frontend boundary is
  already structured to support this later.
- **Production hardening (Phase 8): not started.** No TLS, rate limiting,
  backup strategy, or security review has been done — see
  `docs/security.md` for the current, honest posture.
- **AI output quality: unverified against a real key** — see
  `docs/ai-evaluation.md`. Demo mode's realism was verified manually
  (every excerpt checked against real extracted PDF text); the live
  `ClaudeProvider` path has not been exercised end-to-end.
- No payment processing, no signed license tokens — see `docs/licensing.md`.

## 7. ClauseRisk module — STATUS: done, verified 2026-09-22

A second module built inside this same platform (not a separate app), per
explicit user direction: it reuses TenderGuard's auth, organization/project
management, document storage/extraction, AI provider abstraction pattern,
audit trail (`review_actions`, extended with a nullable `risk_finding_id`
and a table-level "exactly one of requirement_id/risk_finding_id" check
constraint), reporting/export machinery, and licensing system wholesale.

**AI architecture** — the one hard constraint from the brief: no
provider-specific branching anywhere except one factory function.
- `app/services/clauserisk/ai/provider.py` defines an `AIProvider`
  Protocol (`is_available`, `extract_clause`, `analyze_clause_risk`,
  `find_missing_protections`); `app/services/clauserisk/ai/__init__.py`'s
  `get_clauserisk_ai_provider()` is the **only** place that reads
  `CLAUSERISK_AI_PROVIDER` and branches on it.
- `OllamaProvider` (local, default — `mistral:7b-instruct` against
  `http://localhost:11434`) and `ClauseRiskClaudeProvider` (cloud) both
  implement the same protocol against the same versioned prompts
  (`prompts/clause_extraction/v1.md`, `prompts/risk_analysis/v1.md`,
  `prompts/missing_protections/v1.md`).
- Structured output via JSON-schema `enum` constraints
  (`app/services/clauserisk/ai/schemas_json.py`), built from
  `risk_categories.py`'s category/subcategory registry rather than
  hand-duplicated — this is what makes categorical AI output reliable
  enough to trust deterministically downstream.

**Pipeline** (`app/services/clauserisk/pipeline.py`, stages 4-12 of the
brief's 14): deterministic clause segmentation
(`segmentation.py`, regex-based header detection, no AI) → per-clause AI
extraction → deterministic cross-clause linking
(`cross_links.py`: explicit "Clause X.X" references + configured
category-pair patterns, e.g. `liability_cap` ↔ `indemnity`) → per-clause AI
risk analysis (given up to 3 related clauses as context) → **evidence
verification** (every AI-cited excerpt checked as a real substring of the
source text via the same `app/services/text_verification.py` TenderGuard
uses — unverified findings are kept but flagged, not dropped) →
**deterministic risk scoring** (`risk_engine.py`'s `compute_risk_score`:
severity is computed from documented factors — subcategory, cap/exposure
language, evidence verification, AI confidence, uncertainty — never taken
directly from the AI's `severity_hint`, and every factor is stored on the
finding for the UI's "Scoring factors" panel).

**Schema highlights**:
- `Clause.category` is *never* an independent AI field — it's derived
  deterministically from `subcategory` via `category_for_subcategory()`.
  An earlier iteration let the AI set both fields independently and got
  mismatched pairs (e.g. subcategory `insurance_limits` with category
  `liability`); removing the field entirely fixed it by construction.
- `RiskFinding.clause_id` is nullable — a "missing protection" finding
  (no insurance clause found at all) isn't attached to any single clause,
  by design.
- Contract version re-analysis (`POST /api/contract-versions/{id}/analysis`
  on an already-completed version) **clears prior clauses/links/findings
  before regenerating** (`pipeline.py::_clear_previous_analysis`) — see
  the regression note below.

**Contract comparison** (`comparison.py`): fully deterministic — matches
clauses by `clause_number` across two versions, diffs amounts/
percentages/dates/obligation sets, classifies each change as
`material`/`minor` by category. No AI involved in comparison itself.

**Frontend**: Contracts section on the Project detail page (create/list,
mirrors the Documents panel pattern) plus three new top-level areas —
Contracts (org-wide, `GET /api/contracts`, joins across projects),
Risk Register (org-wide, `GET /api/risk-findings`, filterable by
severity/category/review status), and per-contract Compare Versions
(reached from the contract detail page, not a standalone nav item, since
a comparison always needs two versions of one specific contract already
selected). Contract detail page: version upload, per-version "Run
analysis" with status polling, expandable clause rows (extracted fields +
cross-clause links), risk findings table. Finding detail page: risk
description, scoring factors, evidence (with an honest "could not be
verified" state), review actions, audit trail — same shape as
TenderGuard's requirement detail page.

**Regression caught and fixed during this build**: running analysis
twice on the same contract version (surfaced by re-triggering a real
Ollama-backed run after a server restart killed the first one mid-flight)
duplicated every clause and finding — the pipeline only ever appended new
rows. Fixed by clearing prior clauses/links/findings for that version
before regenerating (`pipeline.py::_clear_previous_analysis`), with a
regression test
(`tests/test_clauserisk_api.py::test_rerunning_analysis_does_not_duplicate_clauses_or_findings`).
**The identical bug existed in TenderGuard's own analysis pipeline**
(`app/services/analysis.py`) — re-running compliance analysis on a
project duplicated every `Requirement` the same way, since it's the same
"regenerate on run" shape. Fixed the same way
(`analysis.py::_clear_previous_analysis`), with its own regression test
(`tests/test_analysis_rerun.py`). Both fixes intentionally discard prior
review actions on re-run (there's no versioned analysis-run history in
this MVP) — documented as a known limitation, not silently swallowed.

**Verified live against a real local Ollama model** (`mistral:7b-instruct`,
not a fake/fixture provider): the "Try the sample contract" demo contract
was analyzed end-to-end against the real running Ollama server —
clause segmentation, extraction, cross-linking, and risk scoring all
observed on real (if slow — roughly 60-90s per AI call, ~15-17 minutes for
a 10-clause contract's two analysis passes) model output, not mocked.
This is a materially higher bar than TenderGuard's own AI path, which
remains unverified against a live Claude key (see `docs/ai-evaluation.md`).

**Verified**: 62/62 backend tests pass (32 ClauseRisk-specific, including
the two new org-wide list endpoints and the re-run regression), `ruff`
and `mypy` clean on the full `apps/api` tree, `tsc --noEmit` and `eslint`
clean on `apps/web`, `next build` succeeds, and a full Playwright browser
pass (register → dashboard → create project → add contract → contract
detail → org-wide Contracts list → Risk Register) with zero console
errors.
