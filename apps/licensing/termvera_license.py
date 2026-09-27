"""Termvera license key tool (vendor side; never ship this to customers).

  keygen   Create the signing key pair (once). The private key is written
           outside the repository; the public key is printed for
           app/services/license_keys.py.
  issue    Create a license key for a customer.
  inspect  Verify a key and show what it grants.

Examples:
  python termvera_license.py keygen
  python termvera_license.py issue --licensee "Meridian Energy" --email buyer@meridian.com \\
      --plan professional --months 12 --machine-id K7QF-2M9X-4HCT-8WPN-B3RD Q2TC-...
      (one key per PC: the customer reads each Machine ID from Settings)
  python termvera_license.py issue --licensee "Meridian Energy" --count 5 --months 12
      (five unbound keys, usable on any computer)
  python termvera_license.py inspect TMV1.eyJ...

The private key file is the whole licensing system: anyone holding it can
mint keys, and losing it means you can't issue keys the installed base
accepts. Keep it out of git, back it up somewhere safe (a password manager
or offline media), and restrict who has it.
"""

import argparse
import base64
import calendar
import csv
import subprocess
import sys
import uuid
from datetime import date
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api"))
from app.services.license_keys import LicenseKeyClaims, sign, verify  # noqa: E402
from app.services.machine_id import normalise_machine_id  # noqa: E402

DEFAULT_KEY_FILE = Path.home() / ".termvera" / "license-signing-key.pem"
# Every key issued is appended here: who has which key, until when. Needed
# for renewals, support questions and invoicing. Opens in Excel.
REGISTER_FILE = Path.home() / ".termvera" / "issued-licenses.csv"
PLANS = ("professional", "enterprise")
MODULES = ("tenderguard", "clauserisk")


def _add_months(start: date, months: int) -> date:
    month_index = start.month - 1 + months
    year, month = start.year + month_index // 12, month_index % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _load_private_key(path: Path) -> Ed25519PrivateKey:
    if not path.exists():
        sys.exit(f"No signing key at {path}. Run 'keygen' first, or pass --key-file.")
    key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        sys.exit(f"{path} is not an Ed25519 private key.")
    return key


def _public_b64(key: Ed25519PrivateKey) -> str:
    raw = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )
    return base64.b64encode(raw).decode("ascii")


def keygen(args: argparse.Namespace) -> None:
    path: Path = args.key_file
    if path.exists():
        sys.exit(f"{path} already exists. Refusing to overwrite: every issued key depends on it.")
    path.parent.mkdir(parents=True, exist_ok=True)
    key = Ed25519PrivateKey.generate()
    path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    print(f"Private key written to {path} (back it up; never commit it).")
    print(f"Public key for app/services/license_keys.py:\n{_public_b64(key)}")


def _record(claims: LicenseKeyClaims, license_key: str) -> None:
    new_file = not REGISTER_FILE.exists()
    with REGISTER_FILE.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if new_file:
            writer.writerow(["issued", "license_id", "licensee", "email", "plan", "seats",
                             "valid_until", "machine_id", "key"])
        writer.writerow([claims.issued_at, claims.license_id, claims.licensee, claims.email or "",
                         claims.plan, claims.seats, claims.expires_at, claims.machine_id or "",
                         license_key])


def _make_key(
    private_key: Ed25519PrivateKey,
    *,
    licensee: str,
    email: str | None,
    plan: str,
    seats: int,
    months: int,
    start: date,
    modules: list[str] | None = None,
    machine: str | None = None,
) -> tuple[LicenseKeyClaims, str]:
    claims = LicenseKeyClaims(
        license_id=f"L-{uuid.uuid4().hex[:10].upper()}",
        licensee=licensee,
        email=email,
        plan=plan,
        seats=seats,
        modules=modules or list(MODULES),
        issued_at=date.today(),
        expires_at=_add_months(start, months),
        machine_id=machine,
    )
    license_key = sign(claims, private_key)
    verify(license_key, public_key_b64=_public_b64(private_key))  # never hand out a key that fails
    _record(claims, license_key)
    return claims, license_key


def wizard(args: argparse.Namespace) -> None:
    """Question-and-answer key creation: what License Maker.bat runs."""
    private_key = _load_private_key(args.key_file)
    print("Termvera License Maker\n")
    licensee = ""
    while not licensee:
        licensee = input("Customer company name (shown in the app): ").strip()
    email = input("Customer email (optional): ").strip() or None
    months_text = input("Subscription length in months [12]: ").strip() or "12"
    plan_text = input("Plan: 1 = Professional, 2 = Enterprise [1]: ").strip() or "1"
    plan = "enterprise" if plan_text == "2" else "professional"
    seats_text = input("Number of users [1]: ").strip() or "1"

    claims, license_key = _make_key(
        private_key,
        licensee=licensee,
        email=email,
        plan=plan,
        seats=max(1, int(seats_text)),
        months=max(1, int(months_text)),
        start=date.today(),
    )
    print(f"\nLicense {claims.license_id} for {claims.licensee}: {claims.plan}, "
          f"{claims.seats} user(s), valid until {claims.expires_at:%d %b %Y}\n")
    print(license_key)
    if sys.platform == "win32":
        subprocess.run(["clip"], input=license_key.encode("utf-16-le"), check=False)
        print("\nThe key is copied to your clipboard: paste it into your email to the customer.")
    print(f"Recorded in {REGISTER_FILE}")


def issue(args: argparse.Namespace) -> None:
    key = _load_private_key(args.key_file)
    start = date.fromisoformat(args.start) if args.start else date.today()
    # One key per Machine ID given (each works only on that PC), otherwise
    # --count keys that work on any PC.
    machines = [normalise_machine_id(m) for m in args.machine_id] if args.machine_id else [None] * args.count
    for machine in machines:
        claims, license_key = _make_key(
            key,
            licensee=args.licensee,
            email=args.email,
            plan=args.plan,
            seats=1 if machine else args.seats,
            months=args.months,
            start=start,
            modules=args.modules,
            machine=machine,
        )
        where = f"PC {machine}" if machine else "any PC"
        print(f"License {claims.license_id} for {claims.licensee} ({where}): {claims.plan}, "
              f"valid until {claims.expires_at}")
        print(license_key)
        print()


def inspect(args: argparse.Namespace) -> None:
    claims = verify(args.key)
    for field, value in claims.__dict__.items():
        print(f"{field:12} {value}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--key-file", type=Path, default=DEFAULT_KEY_FILE)
    commands = parser.add_subparsers(dest="command")

    commands.add_parser("keygen").set_defaults(func=keygen)
    commands.add_parser("wizard", help="Create a key by answering questions").set_defaults(func=wizard)

    p = commands.add_parser("issue")
    p.add_argument("--licensee", required=True, help="Company name shown in the app")
    p.add_argument("--email")
    p.add_argument("--plan", choices=PLANS, default="professional")
    p.add_argument("--seats", type=int, default=1)
    p.add_argument("--months", type=int, default=12, help="Subscription length")
    p.add_argument("--start", help="Subscription start date, YYYY-MM-DD (default today)")
    p.add_argument("--modules", nargs="+", choices=MODULES)
    p.add_argument("--machine-id", nargs="+", help="Bind to these PCs: one key per Machine ID")
    p.add_argument("--count", type=int, default=1, help="Number of unbound keys (no --machine-id)")
    p.set_defaults(func=issue)

    p = commands.add_parser("inspect")
    p.add_argument("key")
    p.set_defaults(func=inspect)

    args = parser.parse_args()
    # No command (e.g. double-clicking License Maker.bat): ask questions.
    (getattr(args, "func", None) or wizard)(args)


if __name__ == "__main__":
    main()
