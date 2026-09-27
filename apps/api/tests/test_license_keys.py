"""Trial, signed license keys, and the view-only mode after expiry."""

import base64
from datetime import UTC, date, datetime, timedelta

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from httpx import AsyncClient
from sqlalchemy import select

from app.models.license import LicenseAccount
from app.services import license_keys

pytestmark = pytest.mark.asyncio


@pytest.fixture
def signing_key(monkeypatch) -> Ed25519PrivateKey:
    """A throwaway vendor key; the app is pointed at its public half."""
    key = Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )
    monkeypatch.setattr(license_keys, "PUBLIC_KEY_B64", base64.b64encode(public).decode())
    return key


def _key(
    signing_key: Ed25519PrivateKey, *, expires: date, plan: str = "professional", machine: str | None = None
) -> str:
    return license_keys.sign(
        license_keys.LicenseKeyClaims(
            license_id="L-TEST000001",
            licensee="Meridian Energy",
            email="buyer@meridian.example",
            plan=plan,
            seats=5,
            modules=["tenderguard", "clauserisk"],
            issued_at=date.today(),
            expires_at=expires,
            machine_id=machine,
        ),
        signing_key,
    )


async def _headers(client: AsyncClient, payload) -> dict[str, str]:
    token = (await client.post("/api/auth/register", json=payload)).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _age_workspace(db_session, *, trial_days_ago: int = 0, expired_days_ago: int | None = None):
    """Move the workspace's trial start / paid-up date into the past."""
    account = await db_session.scalar(select(LicenseAccount))
    now = datetime.now(UTC)
    account.trial_started_at = now - timedelta(days=trial_days_ago)
    account.clock_high_water = None
    if expired_days_ago is not None:
        account.expires_at = now - timedelta(days=expired_days_ago)
    await db_session.commit()


async def test_activating_a_valid_key_licenses_the_workspace(
    client: AsyncClient, registration_payload, signing_key
):
    headers = await _headers(client, registration_payload)
    key = _key(signing_key, expires=date.today() + timedelta(days=365))

    # Pasted from an email: wrapped and indented.
    response = await client.post(
        "/api/license/activate", json={"key": f"  {key[:40]}\n  {key[40:]}  "}, headers=headers
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["state"] == "active"
    assert body["plan"] == "professional"
    assert body["licensed_to"] == "Meridian Energy"
    assert body["seat_limit"] == 5
    assert body["days_left"] >= 364


async def test_tampered_key_is_rejected(client: AsyncClient, registration_payload, signing_key):
    headers = await _headers(client, registration_payload)
    key = _key(signing_key, expires=date.today() + timedelta(days=30))
    prefix, payload, signature = key.split(".")
    forged_payload = license_keys._b64encode(
        license_keys._b64decode(payload).replace(b'"seats":5', b'"seats":500')
    )

    response = await client.post(
        "/api/license/activate", json={"key": f"{prefix}.{forged_payload}.{signature}"}, headers=headers
    )

    assert response.status_code == 422
    assert (await client.get("/api/license", headers=headers)).json()["state"] == "trial"


async def test_key_signed_by_someone_else_is_rejected(client: AsyncClient, registration_payload, signing_key):
    headers = await _headers(client, registration_payload)
    impostor_key = _key(Ed25519PrivateKey.generate(), expires=date.today() + timedelta(days=30))

    response = await client.post("/api/license/activate", json={"key": impostor_key}, headers=headers)

    assert response.status_code == 422


async def test_expired_trial_is_view_only_but_keeps_data_readable(
    client: AsyncClient, registration_payload, db_session
):
    headers = await _headers(client, registration_payload)
    project_id = (
        await client.post("/api/projects", json={"name": "Before expiry"}, headers=headers)
    ).json()["id"]
    await _age_workspace(db_session, trial_days_ago=15)

    blocked = await client.post("/api/projects", json={"name": "After expiry"}, headers=headers)
    assert blocked.status_code == 402
    assert "trial has ended" in blocked.json()["error"]["message"]

    # Existing work is still there to read.
    assert (await client.get(f"/api/projects/{project_id}", headers=headers)).status_code == 200
    license_state = (await client.get("/api/license", headers=headers)).json()
    assert license_state["state"] == "trial_expired"
    assert license_state["read_only"] is True


async def test_lapsed_subscription_gets_a_grace_period_then_goes_view_only(
    client: AsyncClient, registration_payload, db_session, signing_key
):
    headers = await _headers(client, registration_payload)
    await client.post(
        "/api/license/activate",
        json={"key": _key(signing_key, expires=date.today() + timedelta(days=30))},
        headers=headers,
    )

    await _age_workspace(db_session, expired_days_ago=3)
    assert (await client.get("/api/license", headers=headers)).json()["state"] == "grace"
    assert (
        await client.post("/api/projects", json={"name": "In grace"}, headers=headers)
    ).status_code == 201

    await _age_workspace(db_session, expired_days_ago=10)
    assert (await client.get("/api/license", headers=headers)).json()["state"] == "expired"
    assert (
        await client.post("/api/projects", json={"name": "Lapsed"}, headers=headers)
    ).status_code == 402


async def test_winding_the_clock_back_does_not_extend_the_trial(
    client: AsyncClient, registration_payload, db_session
):
    headers = await _headers(client, registration_payload)
    await client.get("/api/license", headers=headers)  # creates the workspace's license row
    account = await db_session.scalar(select(LicenseAccount))
    # By the (wound-back) system clock the trial has a day left, but this
    # workspace has already seen a date two days later than that clock.
    account.trial_started_at = datetime.now(UTC) - timedelta(days=13)
    account.clock_high_water = datetime.now(UTC) + timedelta(days=2)
    await db_session.commit()

    assert (await client.get("/api/license", headers=headers)).json()["state"] == "trial_expired"


async def test_plan_cannot_be_self_selected_outside_development(
    client: AsyncClient, registration_payload, monkeypatch
):
    from app.core.config import get_settings

    headers = await _headers(client, registration_payload)
    monkeypatch.setattr(get_settings(), "environment", "desktop")

    response = await client.patch("/api/license", json={"plan": "enterprise"}, headers=headers)

    assert response.status_code == 403


async def test_per_pc_key_activates_only_on_its_computer(
    client: AsyncClient, registration_payload, signing_key, monkeypatch
):
    import app.services.license as license_module

    monkeypatch.setattr(license_module, "machine_id", lambda: "AAAA-BBBB-CCCC-DDDD-EEEE")
    headers = await _headers(client, registration_payload)
    expires = date.today() + timedelta(days=365)

    wrong = await client.post(
        "/api/license/activate",
        json={"key": _key(signing_key, expires=expires, machine="ZZZZ-YYYY-XXXX-WWWW-VVVV")},
        headers=headers,
    )
    assert wrong.status_code == 422
    assert "AAAA-BBBB-CCCC-DDDD-EEEE" in wrong.json()["error"]["message"]  # tells them this PC's ID

    right = await client.post(
        "/api/license/activate",
        json={"key": _key(signing_key, expires=expires, machine="AAAA-BBBB-CCCC-DDDD-EEEE")},
        headers=headers,
    )
    assert right.status_code == 200
    assert right.json()["state"] == "active"
    assert right.json()["bound_machine_id"] == "AAAA-BBBB-CCCC-DDDD-EEEE"


async def test_licensed_workspace_copied_to_another_pc_is_view_only(
    client: AsyncClient, registration_payload, signing_key, monkeypatch
):
    import app.services.license as license_module

    monkeypatch.setattr(license_module, "machine_id", lambda: "AAAA-BBBB-CCCC-DDDD-EEEE")
    headers = await _headers(client, registration_payload)
    key = _key(signing_key, expires=date.today() + timedelta(days=365), machine="AAAA-BBBB-CCCC-DDDD-EEEE")
    await client.post("/api/license/activate", json={"key": key}, headers=headers)

    # The data folder moves to a different computer.
    monkeypatch.setattr(license_module, "machine_id", lambda: "QQQQ-RRRR-SSSS-TTTT-UUUU")

    assert (await client.get("/api/license", headers=headers)).json()["state"] == "other_machine"
    blocked = await client.post("/api/projects", json={"name": "Elsewhere"}, headers=headers)
    assert blocked.status_code == 402
    assert "QQQQ-RRRR-SSSS-TTTT-UUUU" in blocked.json()["error"]["message"]


async def test_pasting_the_signing_key_gets_a_clear_warning(client: AsyncClient, registration_payload):
    headers = await _headers(client, registration_payload)
    pem_body = "MC4CAQAwBQYDK2VwBCIEIBAc+4jaofVMKIQ7/MUeeWcNhVQTroZUfC0AIIoNG8DT"

    response = await client.post("/api/license/activate", json={"key": pem_body}, headers=headers)

    assert response.status_code == 422
    assert "private signing key" in response.json()["error"]["message"]


async def test_free_early_access_has_no_countdown_or_limits(
    client: AsyncClient, registration_payload, db_session, monkeypatch
):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "billing_enabled", False)
    headers = await _headers(client, registration_payload)

    license_state = (await client.get("/api/license", headers=headers)).json()
    assert license_state["plan"] == "free"
    assert license_state["state"] == "free"
    assert license_state["read_only"] is False
    assert license_state["project_limit"] == -1

    # Long after a trial would have ended, still fully usable.
    await _age_workspace(db_session, trial_days_ago=400)
    for i in range(12):
        response = await client.post("/api/projects", json={"name": f"P{i}"}, headers=headers)
        assert response.status_code == 201, response.text


async def test_switching_billing_on_gives_free_users_a_fresh_trial(
    client: AsyncClient, registration_payload, db_session, monkeypatch
):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "billing_enabled", False)
    headers = await _headers(client, registration_payload)
    await client.get("/api/license", headers=headers)
    await _age_workspace(db_session, trial_days_ago=300)  # an early user from long ago

    monkeypatch.setattr(get_settings(), "billing_enabled", True)
    license_state = (await client.get("/api/license", headers=headers)).json()

    assert license_state["plan"] == "trial"
    assert license_state["state"] == "trial"
    assert license_state["days_left"] == 14
