# Licensing: trial, license keys, and what is enforced

## Commercial model

| Stage | What the customer gets | How it ends |
|---|---|---|
| **Free trial** | Every feature for 14 days (`TRIAL_DAYS`), no card, no sign-up. Starts at first-run setup. Trial limits: 10 projects, 25 contracts, 25 analyses a month. | Workspace becomes **view-only**. |
| **Subscription** | A signed **license key** sets the plan, seats, modules and paid-up-until date. | 7-day **grace period** (`GRACE_DAYS`), still fully usable, then **view-only**. |
| **Renewal / upgrade** | A new key replaces the old one (Settings → License). | — |

**View-only** means everything can still be opened, searched and exported,
but nothing new can be created, uploaded or analysed. Customers are never
locked out of their own data. This is the Microsoft 365 "reduced
functionality" pattern, and it keeps renewal conversations friendly.

Plans (`app/services/license.py::PLAN_PRESETS`):

| Plan | Projects | Contracts | Analyses / month |
|---|---|---|---|
| Trial | 10 | 25 | 25 |
| Professional | 100 | 250 | 250 |
| Enterprise | Unlimited | Unlimited | Unlimited |

`demo` remains for development and tests only.

## License keys

Format: `TMV1.<payload>.<signature>`. The payload is base64url JSON
(licensee, email, plan, seats, modules, issue date, expiry date); the
signature is Ed25519 over it (`app/services/license_keys.py`).

- The app contains only the **public** key, so it verifies keys offline:
  no license server, nothing sent anywhere, works on air-gapped machines.
- Keys cannot be forged or edited (for example, changing `seats` breaks the
  signature). Both are covered by tests.
- The licensee name is shown in the app ("Professional · licensed to
  Meridian Energy"), which discourages sharing a key between companies.
- Winding the system clock back doesn't extend a trial or subscription: each
  workspace records the latest time it has seen (`clock_high_water`).

### Issuing a key (the simple way)

Double-click **`apps\licensing\License Maker.bat`**. It asks for the
customer's company, email, subscription length, plan and number of users,
then prints the key, copies it to the clipboard for your email, and adds a
row to `%USERPROFILE%\.termvera\issued-licenses.csv` (open it in Excel:
your register of who has which key until when).

Default practice until online activation exists: **one key per customer
company, usable on any of their PCs.** The app shows "Licensed to
<Company>", which is the deterrent against passing it on. Per-PC keys
(below) are there for customers who ask for them.

### Issuing a key from the command line

```powershell
cd apps\licensing
..\api\.venv\Scripts\python.exe termvera_license.py issue `
    --licensee "Meridian Energy" --email buyer@meridian.com `
    --plan professional --seats 5 --months 12
```

Paste the printed `TMV1…` key into the customer's welcome email.
`inspect <key>` shows what any key grants.

### One key per PC

Each installation shows a **Machine ID** in Settings → License (for
example `K7QF-2M9X-4HCT-8WPN-B3RD`), derived from the ID Windows assigns
the computer, so it survives reboots, reinstalls and upgrades. The
customer sends you the Machine IDs of the PCs they're buying for, and you
issue one key per PC:

```powershell
..\api\.venv\Scripts\python.exe termvera_license.py issue `
    --licensee "Meridian Energy" --months 12 `
    --machine-id K7QF-2M9X-4HCT-8WPN-B3RD Q2TC-8HWN-3KPM-7RXD-F4JA
```

A key bound to a PC:

- activates only on that PC; anywhere else it's refused with a message
  giving that computer's own Machine ID to request a key with;
- is re-checked continuously, so copying a licensed data folder to another
  PC makes it view-only there (state `other_machine`).

For a site licence or trial extension, `--count N` issues N unbound keys
that work on any computer.

### Online activation (design, not built)

Per-PC keys need the customer to send Machine IDs. Online activation does
the same exchange automatically, which is what makes "buy 5 seats, install
anywhere" work:

1. The customer buys N seats and receives one **order key** (an unbound
   key with `seats: N`).
2. On activation the app sends the order key and its Machine ID to your
   activation server (for example `https://activate.termvera.app`).
3. The server checks its database: is the order key genuine and paid, and
   how many machines already hold a seat? If one is free, it records this
   Machine ID and returns a **per-PC key**, the exact format above, signed
   there.
4. The app activates that per-PC key as usual, verifying it offline with
   the public key. After activation it never needs the server again (no
   phoning home), which suits customers' locked-down networks.
5. "Deactivate this PC" in Settings releases the seat on the server, to
   move it to a new laptop. Support can also free a seat for a lost machine.

**Where the `.pem` goes:** the private key moves to the activation server
only (ideally in a cloud key-management service such as AWS KMS or Azure
Key Vault, which signs without ever revealing the key), and off your
laptop. The app never has it; it only ever holds the public key. Customers
on air-gapped networks keep using the manual per-PC flow above.

The server is a small web service (about a day's work): one endpoint, a
table of (order key, Machine ID, activated at), and the existing signing
code. Pair it with the store webhook so a purchase creates the order key
automatically.

### The signing key: protect it

The private key is at `%USERPROFILE%\.termvera\license-signing-key.pem`
(created by `termvera_license.py keygen`; never in the repository).

- **Anyone holding it can mint valid keys.** Keep it on as few machines as
  possible, never commit or email it, and never ship it in the app.
- **Losing it means the installed base can't accept new keys** until an app
  update ships a new public key. Back it up now, to a password manager or
  offline media.
- Its public half is `PUBLIC_KEY_B64` in `app/services/license_keys.py`.
  Changing that invalidates every key already issued.

## Where it's enforced

Every write path already ran through one of the limit checks in
`app/services/license.py` (`check_project_limit`, `check_contract_limit`,
`check_and_report_usage`); each now first calls `_ensure_writable`, which
raises `WorkspaceReadOnlyError` (HTTP 402, with a message saying the work is
safe and how to continue) once the trial or subscription has lapsed.

`PATCH /api/license` (an admin picking a plan) works only when
`ENVIRONMENT=development`. Anywhere else it returns 403, because otherwise
any customer admin could give themselves Enterprise for free.

## Not built yet

- **Online activation** (designed above). Until it exists, seats are
  enforced by issuing per-PC keys by hand; unbound keys rely on the
  licensee name in the app as a deterrent.
- **Payment integration.** Keys are issued by hand. The natural next step
  is a store (Paddle, Lemon Squeezy or FastSpring handle global tax as
  merchant of record) calling a webhook that runs the same signing code and
  emails the key.
- **Revocation.** A key is valid until its expiry date. Keep terms to 12
  months or less so a lapsed or refunded customer ages out.
