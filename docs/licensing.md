# Licensing (current state)

## What exists today

`app/services/license.py` implements `LicenseAccount` / `UsageEvent` as a
**local development / demo entitlement fixture**:

- Every organization gets a `LicenseAccount` row (plan `demo`) created
  lazily on first access — no signup flow, no payment.
- Real enforcement, not just display: `project_limit`,
  `monthly_document_limit`, and `monthly_analysis_limit` are checked at the
  point of use (`POST /api/projects`, `POST /api/projects/{id}/documents`,
  `POST /api/projects/{id}/analysis`) and return `402 Payment Required`
  with a clear message when exceeded. Usage is recorded in `usage_events`
  and reset monthly (calendar month boundary).
- `GET /api/license` and `GET /api/usage` expose plan + current usage;
  the web app's topbar shows `{plan} plan — {used}/{limit} projects`.

## Module entitlements (TenderGuard / ClauseRisk)

`LicenseAccount.enabled_modules` is a JSON list (`LicenseModule.TENDERGUARD`
/ `LicenseModule.CLAUSERISK`) stored on the same row as the usage limits
above — one licensing system shared by both modules, per the brief's
requirement. Every demo/local account is provisioned with both modules
enabled by default (`ALL_MODULES`).

- `app/services/license.py::check_module_entitlement` raises
  `ModuleNotEntitledError` (→ `403`) when a route's module isn't enabled;
  every ClauseRisk write route (`contracts.py`'s `_require_clauserisk`
  helper) checks this before doing anything else.
- Separate monthly limits for ClauseRisk usage:
  `monthly_contract_limit` and `monthly_clause_analysis_limit`, enforced
  the same way as TenderGuard's document/analysis limits (`402 Payment
  Required` on breach) — contracts and analysis runs don't share a quota
  with tender projects/documents.
- **No admin UI to toggle modules yet.** Disabling a module for testing
  currently means editing the `enabled_modules` column directly (exercised
  in `tests/test_clauserisk_license.py::test_module_gate_rejects_when_disabled`)
  — there's no `PATCH /api/license` endpoint. Same "not yet built" caveat
  as everything else in this document.

## Plans and the admin control

`PATCH /api/license` lets a workspace **owner or admin** (membership role,
re-checked from the database on every request via `require_admin`) set the
plan directly. There is no payment provider to buy one from, so pretending
this is a purchase flow would be dishonest; it is an entitlement control,
gated on role.

| Plan | Projects | Contracts | Analyses/month |
|---|---|---|---|
| Demo (default) | 3 | 10 | 10 |
| Trial | 10 | 25 | 25 |
| Professional | 100 | 250 | 250 |
| Enterprise | Unlimited | Unlimited | Unlimited |

"Unlimited" is the sentinel `-1` (`license_service.UNLIMITED`), checked by
`is_unlimited()` at each limit gate. Usage events are still recorded on an
unlimited plan: those counts are what a real paid tier would bill on, and
what the workspace owner sees in Settings. The web app renders `-1` as
"Unlimited" rather than showing the sentinel.

Admins can also delete a project (`DELETE /api/projects/{id}`), which soft
deletes the project and stamps its contracts as deleted too, removing the
whole tree from every list without destroying the underlying audit rows.

## What does NOT exist yet — do not claim otherwise

- **No cryptographic signing or remote validation.** The entitlement is a
  plain database row an operator with DB access could edit directly.
  There is no signed license token, no offline grace period, no
  revocation mechanism.
- **No payment integration.** No Stripe/payment-provider code exists.
  `LicensePlan` includes `trial` / `professional` / `enterprise` values in
  the schema for forward-compatibility, but nothing currently issues or
  upgrades a plan — every org is `demo` forever until this is built.
- **No seat/user-limit enforcement** (`seat_limit` is stored but not
  checked anywhere yet — only project/document/analysis counts are).
- **No way to invite a second user**, so in practice every workspace has
  exactly one member, who is its owner and therefore its admin. The
  role check is real; the role *assignment* has no UI behind it yet.
- **No desktop licensing story** — irrelevant until Phase 9 (desktop
  distribution), which has not been started.

## Path to a real licensing system (not yet built)

Per the product brief (§15): a production version needs a
`LicenseService` abstraction backed by a remote licensing service,
cryptographically signed license tokens with the private signing key held
server-side only (never in a desktop client), and a real payment
provider integration. The current `app/services/license.py` functions
(`get_or_create_license`, `check_and_report_usage`, `check_project_limit`,
`get_usage_summary`) are the seam where that would plug in — the call
sites in the API routes wouldn't need to change, only the implementation
behind them.
