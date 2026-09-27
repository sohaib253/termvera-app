"""Desktop onboarding: set up once with no password, then signed in automatically."""

import pytest
from httpx import AsyncClient

from app.core.config import get_settings

pytestmark = pytest.mark.asyncio


@pytest.fixture
def desktop_mode(monkeypatch):
    monkeypatch.setattr(get_settings(), "environment", "desktop")


async def test_desktop_routes_are_off_in_a_server_deployment(client: AsyncClient):
    status = (await client.get("/api/desktop/status")).json()
    assert status["desktop"] is False and status["setup_required"] is False
    assert (await client.post("/api/desktop/session")).status_code == 404


async def test_first_run_setup_then_automatic_sign_in(client: AsyncClient, desktop_mode):
    status = (await client.get("/api/desktop/status")).json()
    assert status["desktop"] is True and status["setup_required"] is True
    assert (await client.post("/api/desktop/session")).status_code == 409

    setup = await client.post(
        "/api/desktop/setup", json={"full_name": "Sohaib Iqbal", "organization_name": "Iqbal Energy"}
    )
    assert setup.status_code == 201, setup.text

    assert (await client.get("/api/desktop/status")).json()["setup_required"] is False
    tokens = (await client.post("/api/desktop/session")).json()
    me = (
        await client.get("/api/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    ).json()
    assert me["user"]["full_name"] == "Sohaib Iqbal"
    assert me["organization"]["name"] == "Iqbal Energy"
    assert me["role"] == "owner"

    license_state = (
        await client.get("/api/license", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    ).json()
    assert license_state["state"] == "trial"
    assert license_state["days_left"] == 14


async def test_setup_cannot_be_run_twice(client: AsyncClient, desktop_mode):
    body = {"full_name": "A", "organization_name": "B"}
    assert (await client.post("/api/desktop/setup", json=body)).status_code == 201
    assert (await client.post("/api/desktop/setup", json=body)).status_code == 409


async def test_help_checklists_come_from_the_engine(client: AsyncClient):
    from app.services.brain.contract_kb import PROTECTIONS, RULES

    body = (await client.get("/api/help/checklists")).json()

    assert body["contract_rule_count"] == len(RULES)
    assert sum(len(a["checks"]) for a in body["contract_areas"]) == len(RULES)
    assert len(body["missing_protections"]) == len(PROTECTIONS)
    assert any(a["area"] == "HSE" for a in body["tender_areas"])
    assert "bid bond" in body["tender_evidence_anchors"]
