"""Release smoke test: drive an installed Termvera through its real UI.

Walks a first-time user's journey: welcome screen, trial start, automatic
sign-in on reload, drag-in upload of a scanned contract, OCR and analysis,
the Help page, license activation, and rejection of a tampered key.
Screenshots go to --shots.

Needs Microsoft Edge (Playwright drives it; no browser download) and the
vendor signing key for the activation step. Run against a throwaway data
folder so it starts at first-run setup:

  $env:LOCALAPPDATA = "C:	emp	v-data"
  & "$env:USERPROFILE\AppData\Local\Programs\Termvera\Termvera.exe" --no-window
  python apps/desktop/ui_smoke_test.py --data C:	emp	v-data --contract <scanned.pdf>
"""

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

REPO = Path(__file__).resolve().parent.parent.parent
parser = argparse.ArgumentParser()
parser.add_argument("--data", type=Path, required=True, help="LOCALAPPDATA the app was started with")
parser.add_argument("--contract", type=Path, required=True, help="A scanned contract PDF to upload")
parser.add_argument("--shots", type=Path, default=Path("smoke-shots"))
args = parser.parse_args()

URL = json.loads((args.data / "Termvera" / "running.json").read_text())["url"]
CONTRACT = args.contract
SHOTS = args.shots
SHOTS.mkdir(exist_ok=True)

key = subprocess.run(
    [sys.executable, str(REPO / "apps" / "licensing" / "termvera_license.py"), "issue",
     "--licensee", "Iqbal Energy Services", "--plan", "professional", "--seats", "3", "--months", "12"],
    capture_output=True, text=True, check=True,
).stdout.strip().splitlines()[-1]


def step(name: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {name}", flush=True)


with sync_playwright() as pw:
    browser = pw.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))

    step("open app -> expect welcome screen")
    page.goto(URL + "/")
    page.wait_for_url("**/welcome/**", timeout=15000)
    expect(page.get_by_text("Let's set up your workspace").first).to_be_visible()
    page.screenshot(path=SHOTS / "1-welcome.png")

    step("fill setup and start trial")
    page.fill("#full_name", "Sohaib Iqbal")
    page.fill("#organization_name", "Iqbal Energy Services")
    page.get_by_role("button", name=re.compile(r"free trial|it's free")).click()
    page.wait_for_url("**/dashboard/**", timeout=15000)
    expect(page.get_by_text(re.compile(r"Free trial · 14 days left|Free · early access")).first).to_be_visible(timeout=10000)
    page.screenshot(path=SHOTS / "2-dashboard-trial.png")

    step("reload -> still signed in, no login screen")
    page.reload()
    page.wait_for_url("**/dashboard/**", timeout=15000)
    expect(page.get_by_text(re.compile(r"Free trial · 14 days left|Free · early access")).first).to_be_visible(timeout=10000)

    step("new contract review: drop the scanned OGDCL contract")
    page.goto(URL + "/contracts/new/")
    expect(page.get_by_text("Drag the contract here or click to browse").first).to_be_visible(timeout=10000)
    page.set_input_files("input[type=file]", str(CONTRACT))
    expect(page.locator("#contract_name")).to_have_value("OGDCL Sand Trap Contract 2014")
    page.select_option("#project", "__new__") if page.locator("#project").count() else None
    page.fill("#new_project_name", "OGDCL Sand Trap")
    page.fill("#counterparty", "OGDCL")
    page.screenshot(path=SHOTS / "3-new-contract.png")
    page.get_by_role("button", name="Start contract review").click()
    page.wait_for_url("**/contracts/view/**", timeout=30000)

    step("wait for OCR + analysis to complete")
    expect(page.get_by_text("Reading text").first).to_be_visible(timeout=20000)
    page.screenshot(path=SHOTS / "4-ocr-progress.png")
    expect(page.get_by_role("button", name="Re-run")).to_be_visible(timeout=180000)
    page.screenshot(path=SHOTS / "5-contract-analysed.png")

    step("open the analysed version")
    page.get_by_role("link", name="v1 — Original").click()
    page.wait_for_url("**/contracts/version/**", timeout=15000)
    page.wait_for_timeout(2500)
    page.screenshot(path=SHOTS / "6-version-findings.png", full_page=False)

    step("open a finding: evidence names section, clause and printed page")
    page.locator("a[href*='/risk-findings/view']").first.click()
    page.wait_for_url("**/risk-findings/view/**", timeout=15000)
    expect(page.get_by_text("printed page").first).to_be_visible(timeout=10000)
    expect(page.get_by_role("button", name="Open at this page").first).to_be_visible()
    page.get_by_role("heading", name="Evidence").scroll_into_view_if_needed()
    page.screenshot(path=SHOTS / "6b-finding-evidence.png")

    step("help page")
    page.goto(URL + "/help/")
    expect(page.get_by_text("Contract checklist", exact=True).first).to_be_visible(timeout=10000)
    page.get_by_placeholder("Search the rules").fill("liquidated")
    page.wait_for_timeout(500)
    page.screenshot(path=SHOTS / "7-help.png", full_page=False)

    step("activate a real license key in settings")
    page.goto(URL + "/settings/")
    expect(page.get_by_text("This computer's Machine ID").first).to_be_visible(timeout=10000)
    page.fill("#license_key", key)
    page.get_by_role("button", name="Activate").click()
    expect(page.get_by_text("License activated").first).to_be_visible(timeout=10000)
    licensed = page.get_by_text("Professional · licensed to Iqbal Energy Services").first
    expect(licensed).to_be_visible(timeout=10000)
    page.screenshot(path=SHOTS / "8-licensed.png")

    step("bad key is rejected with a clear message")
    page.fill("#license_key", key[:-6] + "AAAAAA")
    page.get_by_role("button", name="Activate").click()
    expect(page.get_by_text("could not be verified").first).to_be_visible(timeout=10000)

    print("page errors:", errors or "none")
    browser.close()
print("SMOKE TEST PASSED")
