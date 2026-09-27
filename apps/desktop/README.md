# Termvera desktop (offline) build

Produces one Windows installer, `Termvera-Setup-<version>.exe` (~65 MB),
that installs everything the app needs. The user's machine needs nothing
else installed: no Python, Node.js, PostgreSQL, Tesseract or LibreOffice.

## What the user gets

- Installs per user, with no administrator rights, into
  `%LOCALAPPDATA%\Programs\Termvera`, plus a Start menu shortcut and an
  optional desktop shortcut.
- First launch asks for a name and company, then starts the 14-day trial;
  there is no account or password, and later launches open straight into
  the workspace. Licensing is described in `docs/licensing.md`.
- Starting it opens Termvera in its own window (Microsoft Edge app mode,
  present on every Windows 10/11 machine). Closing the window stops it.
- **Everything stays on the machine.** The database (SQLite), uploaded
  documents and logs are in `%LOCALAPPDATA%\Termvera`. The server listens
  on `127.0.0.1` only, so it can't be reached from the network. Analysis
  uses the built-in rule-based engine, never a remote AI service.
- Scanned PDFs and images are read by the bundled Tesseract OCR. Word
  (.docx), RTF and ODT are read directly. Legacy .doc uses the user's
  Microsoft Word if installed; otherwise the user is asked to save as .docx.
- Upgrading means running a newer installer over the old one; the data
  folder is untouched, and database migrations run at start-up. Uninstalling
  asks whether to delete the data (a silent uninstall keeps it).

## Building the installer

On a Windows developer machine with:

- `apps\api\.venv` set up with `pip install -r requirements.txt -r requirements-dev.txt`
  (the dev requirements include PyInstaller and pefile)
- Node.js, with `npm ci` done in `apps\web`
- Tesseract installed (`winget install tesseract-ocr.tesseract`, or the
  per-user install described in `docs/setup.md`)
- Inno Setup 6 (`winget install JRSoftware.InnoSetup`)

run:

```powershell
powershell -ExecutionPolicy Bypass -File apps\desktop\build.ps1 -Version 0.1.0
```

Output: `build\desktop\installer\Termvera-Setup-0.1.0.exe`.

The script:

1. Exports the web app as static files (`apps/web/out`).
2. Copies only the parts of Tesseract that OCR needs (60 MB, down from 110 MB).
3. Bundles the launcher, API, web files and Tesseract with PyInstaller.
4. Wraps the bundle in an Inno Setup installer.

## Files

| File | Purpose |
|---|---|
| `launcher.py` | The program users run. Starts the local server and opens the window. `--no-window` serves without opening one. |
| `termvera.spec` | PyInstaller recipe. |
| `installer.iss` | Inno Setup installer script. |
| `collect_tesseract.py` | Copies the minimal Tesseract runtime. |
| `make_icon.py` / `termvera.ico` | Draws the app icon and the web favicon from the brand mark (see docs/go-to-market.md). |

Run from source without building: `apps\api\.venv\Scripts\python.exe apps\desktop\launcher.py`
(this uses `apps/web/out`, so build the web app first with
`NEXT_PUBLIC_API_BASE_URL=same-origin`).

## Before distributing publicly

- **Code signing.** An unsigned installer triggers Windows SmartScreen
  ("Windows protected your PC"). Sign both `Termvera.exe` and the setup
  file with a code-signing certificate (`signtool`, or Inno Setup's
  `SignTool` directive).
- **Licences.** Ship third-party notices. PyMuPDF is AGPL-3.0, so a
  closed-source distribution needs Artifex's commercial licence; otherwise
  publish the source. Tesseract is Apache-2.0 (its licence is bundled).
- **Database migrations must be SQLite-safe.** New installs create the
  schema directly and are stamped at the latest migration. Every migration
  from `7c2e9a41d5b3` onward runs on user machines during upgrades, so use
  `op.batch_alter_table` for anything beyond adding a column.
- **Only tested on the build machine.** Test on a clean Windows 10 and
  Windows 11 machine before release.

## Release smoke test

Before publishing a build, install it and run `apps/desktop/ui_smoke_test.py`. It drives the real interface in Microsoft Edge: first-run setup, trial, a scanned-contract upload through OCR and analysis, the Help page, and license-key activation and rejection. Usage is in the script's docstring.

## Automatic releases and website

- Code lives in the private repository `sohaib253/termvera-app`.
- The website and installer downloads live in the public repository
  `sohaib253/termvera`, served by GitHub Pages at
  https://sohaib253.github.io/termvera/.
- Every push runs the tests (`.github/workflows/ci.yml`).
- A change under `apps/site/` republishes the website (`site.yml`).
- Tagging a version builds and publishes the installer (`release.yml`):

  ```powershell
  git tag v0.4.1
  git push --tags
  ```

  The site's Download button points at
  `https://github.com/sohaib253/termvera/releases/latest/download/Termvera-Setup.exe`,
  which always serves the newest release.
- Both publishing workflows need the private repository secret
  `PUBLIC_REPO_TOKEN`: a fine-grained token with "Contents: read and write"
  on `sohaib253/termvera` only.
