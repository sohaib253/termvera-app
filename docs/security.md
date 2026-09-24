# Security notes (living document)

This file tracks the security posture of TenderGuard as it's built, and
what's explicitly *not* true yet. Update it every phase — don't let it
drift into aspirational claims.

## Current state (Phases 1–7)

- **Auth**: JWT access (30 min) + refresh (7 days) tokens issued by the API
  itself, signed with `HS256` using `JWT_SECRET_KEY`. Passwords hashed with
  bcrypt via passlib. There is no password reset, MFA, or SSO yet.
- **Tenant isolation**: every project row carries `organization_id`, and
  every read/write filters on the caller's organization id resolved from a
  verified membership row (not just the JWT claim — see `app/api/deps.py`,
  which re-checks membership on every request as defense in depth).
  Documents, requirements, evidence, and assessments are scoped
  transitively through their parent project (checked explicitly in
  `app/services/requirement.py::get_requirement_detail` and the documents
  routes' `_ensure_project_access`). Covered by
  `test_tenant_isolation.py`, `test_documents.py::test_document_tenant_isolation`,
  and `test_requirements.py::test_requirement_detail_tenant_isolation`.
- **Secrets**: `JWT_SECRET_KEY` and `ANTHROPIC_API_KEY` live in `.env`
  (gitignored) and are read via `pydantic-settings`. Nothing is logged
  that contains a password, token, or document content —
  `app/core/logging.py` only ever logs request metadata.
- **Document storage**: uploaded files are written to
  `apps/api/storage/{org_id}/{project_id}/{document_id}/{filename}` on
  local disk (gitignored). The client-supplied filename is sanitized to
  its basename before use (`Path(filename).name` in
  `app/services/storage.py`) to prevent path traversal. Retrieval
  (`GET .../documents/{id}/file`) is gated by the same project-access
  check as everything else — no unauthenticated or cross-tenant read path.
  **Not yet done**: encryption at rest, virus/malware scanning of
  uploads, configurable retention/deletion.
- **Upload validation**: MIME type restricted to `application/pdf`, size
  capped at 50MB (`app/services/storage.py`), and the file is opened with
  PyMuPDF before being trusted — a corrupted or non-PDF file with a
  spoofed content-type fails extraction cleanly
  (`UnsupportedDocumentError`) rather than crashing the worker.
- **Transport**: no TLS termination is configured yet — local dev runs
  over plain HTTP on `localhost`. TLS is a Phase 8 (production hardening)
  requirement before any real deployment.
- **CORS**: locked to `CORS_ORIGINS` (defaults to the local frontend origin
  only).
- **Licensing**: usage limits are enforced server-side
  (`app/services/license.py`), but this is a local fixture with no
  cryptographic signing — see `docs/licensing.md`.

## Prompt injection posture (Phases 3–4)

Tender and bid documents are treated as **untrusted data**, never as
instructions, in both prompt modules
(`prompts/requirement_extraction/v1.md`,
`prompts/compliance_assessment/v1.md`): each explicitly tells the model
that document text between the `<document>` markers is untrusted content
to analyze, not instructions to follow, and never to reveal system
instructions. This is prompt-level mitigation only — it has not been
red-teamed with adversarial documents (no live API key was available to
test against in this environment; see `docs/ai-evaluation.md`).

Beyond the prompt itself, a **deterministic backstop** doesn't depend on
the model behaving: every excerpt the model returns (a requirement's
`source_excerpt`, an evidence record's `excerpt`) is checked as an actual
substring of the real extracted document text before being persisted
(`app/services/analysis.py::_excerpt_is_verifiable`). A prompt-injected
instruction could still influence the model's *classification* of a
requirement, but it cannot make the system display evidence or source
text that doesn't genuinely exist in the document — an unverifiable claim
is silently dropped rather than shown to the user as fact.

ClauseRisk's prompts (`prompts/clause_extraction/v1.md`,
`prompts/risk_analysis/v1.md`, `prompts/missing_protections/v1.md`) carry
the same untrusted-content framing, and its pipeline uses the exact same
excerpt-verification function
(`app/services/text_verification.py::excerpt_is_verifiable`, extracted
from TenderGuard's `analysis.py` so both modules share one implementation
rather than two copies that could drift). One difference: an unverified
ClauseRisk finding is **kept with an empty evidence list** rather than
dropped outright (see `docs/ai-evaluation.md`'s ClauseRisk section for
why), since the underlying risk classification can still be worth a
reviewer's attention even when the cited excerpt can't be confirmed
verbatim — the finding is visibly flagged as unverified in the UI, never
presented as confirmed evidence.

## Explicitly NOT true yet — do not claim these to customers

- No security review or penetration test has been performed.
- No encryption at rest for stored documents.
- No malware/virus scanning of uploaded PDFs.
- No rate limiting on auth endpoints (brute-force protection is a Phase 8 item).
- No SSO/enterprise identity integration, no MFA, no password reset.
- No signed/cryptographically-verified licensing — see `docs/licensing.md`.
- No data residency or retention controls.
- No red-teaming of the AI prompts against adversarial document content.
- TLS, security headers, and production deployment hardening — all Phase 8.
