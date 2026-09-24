# Local setup

Verified on Windows with a native PostgreSQL 14 install (no Docker in the
current dev environment — see `docs/architecture.md` for why the
`docker-compose.yml` path isn't the tested one yet).

## Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL running locally, reachable at `localhost:5432`
- Optional: an `ANTHROPIC_API_KEY` to enable real AI requirement
  extraction / compliance assessment. Without one, the demo/sample
  project still works fully (it uses precomputed sample data, not a live
  AI call) — only `POST /api/projects/{id}/analysis` on a real project
  requires a key, and returns a clear error if one isn't set.
- Optional (for OCR fallback on scanned PDFs): a `tesseract` binary on
  `PATH`. Without it, low-text pages are flagged
  (`extraction_method: "ocr_unavailable"`) rather than silently treated
  as empty.
- Optional, for ClauseRisk contract analysis: a locally running
  [Ollama](https://ollama.com) server with a model pulled — this is the
  default provider (`CLAUSERISK_AI_PROVIDER=ollama`), no API key needed.
  Without it, ClauseRisk's contract/clause/risk-register pages still work
  for browsing, but "Run analysis" returns a clear error rather than
  fabricating output. See §5 below.

## 1. Database

Create the app role and databases (skip if they already exist):

```sql
CREATE ROLE tenderguard WITH LOGIN PASSWORD 'tenderguard';
CREATE DATABASE tenderguard OWNER tenderguard;
CREATE DATABASE tenderguard_test OWNER tenderguard;
```

## 2. Backend (apps/api)

```bash
cd apps/api
python -m venv .venv
./.venv/Scripts/activate      # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -r requirements-dev.txt
cp ../../.env.example .env    # then edit DATABASE_URL / JWT_SECRET_KEY / ANTHROPIC_API_KEY as needed
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Uploaded documents are stored under `apps/api/storage/` (gitignored) —
that directory is created automatically on first upload.

Run the test suite (uses an in-memory SQLite DB, no Postgres required):

```bash
pytest
ruff check app tests scripts
mypy app
```

API docs (Swagger UI) are served at `http://localhost:8000/docs` while the
server is running.

### Regenerating the sample documents

Every fictional document (the ITT, the bidder proposal, the services
agreement, and its amendment) is rendered from one content module,
`app/services/sample_content.py`, rather than hand-built:

```bash
pip install fpdf2==2.8.2
python scripts/generate_sample_data.py
pytest tests/test_sample_documents.py   # confirms every citation is still verbatim
```

The generator also writes `sample_data/manifest.json` recording which page
each clause landed on. `app/services/demo_fixtures.py` quotes the same
content strings and reads page numbers from that manifest, so the demo
project's "page N" citations cannot drift out of sync with the rendered
PDFs. `tests/test_sample_documents.py` fails if they ever do.

Users can download these documents in-app from **Settings → Sample
documents**, then upload them through the normal flow. That path is not
special-cased, so it exercises the same extraction and analysis pipeline a
real document would.

## 3. Frontend (apps/web)

```bash
cd apps/web
npm install
cp .env.example .env.local    # sets NEXT_PUBLIC_API_BASE_URL
npm run dev
```

Open `http://localhost:3000`.

## 4. First run

1. Visit `http://localhost:3000/register`, create an account (this also
   creates your organization).
2. You'll land on the dashboard with an empty state. Click "Try the
   sample project" for an instant, fully-populated example (fictional
   offshore well testing tender + bid, 10 requirements spanning every
   assessment status) — or "Create your first tender review" to start a
   real project.
3. On a real project: upload a tender PDF (type "Tender source") and a
   bid PDF (type "Bid response"), wait for extraction to complete, then
   click "Run analysis". This requires `ANTHROPIC_API_KEY` to be set — if
   it isn't, you'll get a clear error explaining that, with a pointer
   back to the sample project.
4. From either project type, open "Compliance matrix" to review, filter,
   and override AI assessments, then "Export to Excel" for the full
   compliance matrix workbook.

## 5. ClauseRisk (contract risk analysis)

ClauseRisk is a second module in the same app — same login, same
organization, separate nav items ("Contracts", "Risk Register").

1. **Set up Ollama** (the default AI provider — no API key needed):
   ```bash
   # install from https://ollama.com, then:
   ollama pull mistral:7b-instruct
   ollama serve   # usually already running as a background service after install
   ```
   Confirm it's reachable: `curl http://localhost:11434/api/tags`. To use
   a different model or a remote Ollama host, set `OLLAMA_MODEL` /
   `OLLAMA_BASE_URL` in `apps/api/.env`. To use Claude instead, set
   `CLAUSERISK_AI_PROVIDER=claude` and `ANTHROPIC_API_KEY`.
2. Click **New contract review** (dashboard header or Contracts page) for
   the one-screen flow: pick or create a project, name the contract,
   upload the PDF, and start analysis. Or click "Try the sample contract"
   to load the fictional offshore services agreement and its amendment.
3. Upload a contract PDF as a version, then click "Run analysis" — this
   calls the real pipeline (segmentation → AI clause extraction →
   cross-clause linking → AI risk analysis → deterministic scoring). With
   a local 7B Ollama model, expect roughly 60-90 seconds per clause (two
   AI calls each) — a 10-clause contract takes ~15-17 minutes. This is
   genuinely slow; there is no progress bar beyond the status badge, by
   design (no fake progress percentages).
4. Once complete, open the version to see extracted clauses and scored
   risk findings, or "Risk register" (top nav) for the cross-contract
   view. With two analyzed versions, "Compare versions" on the contract
   page produces a deterministic diff (no AI involved in comparison
   itself).
5. Export a risk report from a version detail page (Excel, multiple
   sheets — executive summary, clause risk register, commercial/liability
   summaries, negotiation issues, assumptions & limitations).

## Known limitations at this milestone

- **Licensing is a local fixture, not enforcement**: usage limits
  (projects/documents/analyses per month) are real and enforced, but
  there's no payment integration, signed tokens, or remote validation.
  See `docs/licensing.md`.
- **AI extraction/assessment has not been tested against a real API key**
  in this environment — see `docs/ai-evaluation.md` before trusting its
  output quality on a real tender.
- **ClauseRisk's local Ollama path is slow** (~60-90s per AI call, ~15-17
  minutes for a 10-clause contract) — see `docs/ai-evaluation.md` for
  what was actually verified running against it live, and its `Claude`
  provider path is entirely untested against a real key.
- **Re-running analysis discards prior review decisions** on that
  project/version's findings — both pipelines regenerate from scratch
  rather than keeping versioned analysis-run history (see
  `docs/architecture.md` §7's regression-fix note).
- **OCR fallback is architecturally complete but untested** without a
  `tesseract` install available in this environment.
- Single organization per user is assumed by the "current organization"
  resolution in the JWT (`app/services/auth.py`); the `memberships` table
  already supports multiple organizations per user for when that's needed.
- No password reset flow yet.
- No desktop packaging (Phase 9 — not started, per the brief's own
  guidance not to let it block validating the product).
- No production hardening (TLS, rate limiting, backups, security review)
  — see `docs/security.md`.
