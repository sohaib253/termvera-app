"""A stable, anonymous identifier for this computer, for per-PC license keys.

Derived from the ID the operating system itself assigns at installation
(Windows: MachineGuid in the registry, readable without admin rights;
Linux: /etc/machine-id), hashed with a product-specific salt so it reveals
nothing about the machine and can't be matched against IDs other software
reports. Stays the same across reboots, app reinstalls and upgrades; changes
if Windows is reinstalled, which is when a customer needs a new key anyway.
"""

import hashlib
import os
import uuid
from functools import lru_cache
from pathlib import Path


def _os_machine_guid() -> str:
    if os.name == "nt":
        import winreg

        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography",
                0,
                winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
            ) as key:
                return str(winreg.QueryValueEx(key, "MachineGuid")[0])
        except OSError:
            pass
    for path in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
        try:
            value = Path(path).read_text().strip()
            if value:
                return value
        except OSError:
            continue
    # Last resort: the network adapter's MAC address. Less stable, but
    # every platform has one.
    return f"mac-{uuid.getnode():012x}"


@lru_cache
def machine_id() -> str:
    """Twenty characters in groups of four, e.g. "K7QF-2M9X-4HCT-8WPN-B3RD":
    easy to read out over the phone or paste into an email."""
    digest = hashlib.sha256(f"termvera-machine:{_os_machine_guid()}".encode()).digest()
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O or 1/I to misread
    number = int.from_bytes(digest[:13], "big")
    chars = []
    for _ in range(20):
        number, index = divmod(number, len(alphabet))
        chars.append(alphabet[index])
    code = "".join(chars)
    return "-".join(code[i : i + 4] for i in range(0, 20, 4))


def normalise_machine_id(value: str) -> str:
    raw = "".join(ch for ch in value.upper() if ch.isalnum())
    return "-".join(raw[i : i + 4] for i in range(0, len(raw), 4))
