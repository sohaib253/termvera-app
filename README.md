# TenderGuard

AI-assisted tender compliance and contract risk software for
contractors, EPC companies, and bid management teams. Two modules on one
platform:

- **TenderGuard** (compliance): upload a tender package and a draft bid;
  get an evidence-backed compliance matrix that flags what's missing,
  weak, or ambiguous before submission.
- **ClauseRisk** (contract risk): upload a contract; get clause-by-clause
  risk analysis (liability, schedule, commercial, termination, and more),
  cross-clause relationships, deterministic risk scoring, and version-to-
  version comparison with a material-changes view.

Both are decision-support tools, not automated approval systems. Neither
guarantees bid compliance, tender acceptance, or negotiation outcomes —
see `docs/architecture.md` for the product principles this is built on
(no fabricated evidence, human-in-the-loop review, auditable overrides).

**Status**: functional MVP. TenderGuard covers document ingestion,
AI-assisted requirement extraction and compliance assessment (demo mode
plus a real, swappable Claude provider — see `docs/ai-evaluation.md`), a
filterable compliance workspace with human review/override and audit
trail, and Excel export. ClauseRisk covers contract ingestion, clause
segmentation and AI extraction, cross-clause linking, deterministic risk
scoring, a risk register, contract comparison, and Excel risk reports —
running by default against a **local Ollama model** (no API key
required), verified live end-to-end (see `docs/ai-evaluation.md`). Both
modules share one licensing/usage-limit fixture (`docs/licensing.md`).
Not production ready — no security review, no TLS, no payment
integration, no desktop build yet. See `docs/architecture.md` for the
full phase-by-phase status and `docs/setup.md` to run it locally
(includes one-click fictional demos for both modules, no API key
required for either).

## Structure

```
apps/
  web/    Next.js frontend (TenderGuard + ClauseRisk)
  api/    FastAPI backend (apps/api/app/services/clauserisk/ is the second module)
prompts/  versioned AI prompt modules (both modules)
sample_data/  generated fictional demo PDFs (tender+bid, and a sample contract)
docs/     architecture, setup, security, licensing, AI evaluation notes
```

## Quick start

See [`docs/setup.md`](docs/setup.md).

## License

Proprietary — all rights reserved. See `LICENSE` (placeholder text — not
yet reviewed by counsel).
