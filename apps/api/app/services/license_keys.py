"""Signed license keys: the format, and verification.

A key is `TMV1.<payload>.<signature>`: the payload is base64url JSON
describing the entitlement; the signature is Ed25519 over the payload.
The app holds only the public key below, so it can check a key offline,
with no licence server and nothing leaving the customer's machine, but
cannot create one. Keys are issued with the vendor tool
(apps/licensing/termvera_license.py), which holds the private key; that
key must never be committed or shipped.

This is the model JetBrains and Sublime Text use for offline activation.
It stops forged and edited keys. A key can also be bound to one computer
(`machine`, the Machine ID shown in the app's Settings): it then activates
only there, which is how per-PC seats are enforced offline. An unbound key
works on any machine; "Licensed to <company>" is the deterrent there.
"""

import base64
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

KEY_PREFIX = "TMV1"

# Public half of the vendor signing key (Ed25519, raw 32 bytes, base64).
# Replacing it invalidates every key issued so far.
PUBLIC_KEY_B64 = "MZLlBgpVaRPgmRRP3FrrhYt9PmPz3c2ZxbxMMSCN+yk="


class InvalidLicenseKeyError(Exception):
    pass


@dataclass(frozen=True)
class LicenseKeyClaims:
    license_id: str
    licensee: str  # company name shown in the app
    email: str | None
    plan: str  # a LicensePlan value
    seats: int
    modules: list[str]
    issued_at: date
    expires_at: date  # last day of the subscription
    machine_id: str | None = None  # bound to this computer only, if set


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def normalise(key: str) -> str:
    """Keys get pasted from emails with line breaks and spaces in them."""
    return "".join(key.split())


def verify(key: str, *, public_key_b64: str | None = None) -> LicenseKeyClaims:
    if "PRIVATE KEY" in key or normalise(key).startswith("MC4CAQ"):
        # The vendor's signing key (or its base64 body) pasted by mistake.
        # Say so plainly: it must never be typed into the app or shared.
        raise InvalidLicenseKeyError(
            "That's the private signing key, not a license key. Don't paste or share it. "
            "Create a license key with the License Maker; it starts with TMV1."
        )
    key = normalise(key)
    parts = key.split(".")
    if len(parts) != 3 or parts[0] != KEY_PREFIX:
        raise InvalidLicenseKeyError(
            "This isn't a valid license key. Copy the whole key from your license email, "
            "starting with TMV1."
        )
    _, payload_b64, signature_b64 = parts
    try:
        public_key = Ed25519PublicKey.from_public_bytes(
            base64.b64decode(public_key_b64 or PUBLIC_KEY_B64)
        )
        public_key.verify(_b64decode(signature_b64), payload_b64.encode("ascii"))
        payload = json.loads(_b64decode(payload_b64))
        return LicenseKeyClaims(
            license_id=str(payload["id"]),
            licensee=str(payload["licensee"]),
            email=payload.get("email"),
            plan=str(payload["plan"]),
            seats=int(payload["seats"]),
            modules=[str(m) for m in payload["modules"]],
            issued_at=date.fromisoformat(payload["issued"]),
            expires_at=date.fromisoformat(payload["expires"]),
            machine_id=payload.get("machine"),
        )
    except (InvalidSignature, ValueError, KeyError, TypeError, UnicodeError) as exc:
        raise InvalidLicenseKeyError(
            "This license key could not be verified. Check it was copied completely, or "
            "contact support."
        ) from exc


def sign(claims: LicenseKeyClaims, private_key: Ed25519PrivateKey) -> str:
    """Used by the vendor tool and tests only; the app has no private key."""
    payload = {
        "id": claims.license_id,
        "licensee": claims.licensee,
        "email": claims.email,
        "plan": claims.plan,
        "seats": claims.seats,
        "modules": claims.modules,
        "issued": claims.issued_at.isoformat(),
        "expires": claims.expires_at.isoformat(),
    }
    if claims.machine_id:
        payload["machine"] = claims.machine_id
    payload_b64 = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = private_key.sign(payload_b64.encode("ascii"))
    return f"{KEY_PREFIX}.{payload_b64}.{_b64encode(signature)}"


def end_of_day(value: date) -> datetime:
    return datetime(value.year, value.month, value.day, 23, 59, 59, tzinfo=UTC)
