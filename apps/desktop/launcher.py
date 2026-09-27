"""Termvera desktop launcher: the program the installer's shortcut runs.

Everything stays on this computer. The API, the web interface (served by
the API itself), OCR and the database run locally; data lives in
%LOCALAPPDATA%\\Termvera; analysis uses the built-in rule-based engine,
never a remote AI service.

Start-up:
1. Point the app's settings at the data folder and the bundled resources
   (these must be in the environment before `app` is imported, because
   settings are read once at import).
2. Create the SQLite database on first run, or apply migrations after an
   upgrade.
3. Serve on a free local port, bound to 127.0.0.1 only.
4. Open the app in a chromeless Microsoft Edge window (present on every
   Windows 10/11 machine) with its own profile, and stop the server when
   that window closes. Without Edge, fall back to the default browser.

Launching again while it's running just opens another window onto the
running instance; a lock file makes that hold even when two launches race
(a double-click on the shortcut).
"""

from __future__ import annotations

import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

APP_NAME = "Termvera"
PREFERRED_PORT = 8765


def _bundle_dir() -> Path:
    """Where the bundled files are: PyInstaller's folder when frozen, the
    repository when run from source (python apps/desktop/launcher.py)."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent.parent


def _data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    path = Path(base) / APP_NAME
    (path / "logs").mkdir(parents=True, exist_ok=True)
    return path


def _secret_key(data_dir: Path) -> str:
    """A signing key unique to this install, so a token from one machine is
    worthless on another."""
    key_file = data_dir / "secret.key"
    if not key_file.exists():
        key_file.write_text(secrets.token_urlsafe(48), encoding="utf-8")
    return key_file.read_text(encoding="utf-8").strip()


def _configure_environment(bundle: Path, data_dir: Path) -> None:
    frozen = getattr(sys, "frozen", False)
    web_dist = bundle / "web" if frozen else bundle / "apps" / "web" / "out"
    tesseract = bundle / "tesseract" / "tesseract.exe"
    db_path = data_dir / "tenderguard.db"

    env = {
        "ENVIRONMENT": "desktop",
        "DATABASE_URL": f"sqlite+aiosqlite:///{db_path.as_posix()}",
        "JWT_SECRET_KEY": _secret_key(data_dir),
        "DATA_DIR": str(data_dir),
        "WEB_DIST_DIR": str(web_dist),
        "RESOURCE_DIR": str(bundle),
        "LOG_FILE": str(data_dir / "logs" / "tenderguard.log"),
        # Offline by design: the built-in engine only, whatever the machine's
        # environment says.
        # Free early access. Change to "true" when paid plans launch: existing
        # free users then get a fresh 14-day trial before licences apply.
        "BILLING_ENABLED": "false",
        "TENDERGUARD_AI_PROVIDER": "brain",
        "CLAUSERISK_AI_PROVIDER": "brain",
        "ANTHROPIC_API_KEY": "",
        # A desktop session shouldn't log the user out every half hour.
        "ACCESS_TOKEN_EXPIRE_MINUTES": "720",
        "REFRESH_TOKEN_EXPIRE_DAYS": "90",
    }
    if tesseract.is_file():
        env["TESSERACT_CMD"] = str(tesseract)
    os.environ.update(env)
    if frozen:
        # Tesseract's own DLLs sit beside it; make sure they're found first.
        os.environ["PATH"] = str(tesseract.parent) + os.pathsep + os.environ.get("PATH", "")


class _InstanceLock:
    """Held for the life of the process. msvcrt locks are released by the OS
    if the process dies, so a crash never leaves the app unable to start."""

    def __init__(self, path: Path) -> None:
        self._file = open(path, "a+b")  # noqa: SIM115
        self.acquired = False

    def try_acquire(self) -> bool:
        import msvcrt

        try:
            self._file.seek(0)
            msvcrt.locking(self._file.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            return False
        self.acquired = True
        return True


def _redirect_output(data_dir: Path) -> None:
    # A windowed (no-console) build has no stdout/stderr at all; anything
    # that prints would crash. Send it to a file instead.
    if sys.stdout is None or sys.stderr is None:
        stream = open(data_dir / "logs" / "console.log", "a", encoding="utf-8", buffering=1)  # noqa: SIM115
        sys.stdout = sys.stdout or stream
        sys.stderr = sys.stderr or stream


def _init_database(bundle: Path) -> None:
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, inspect

    import app.models  # noqa: F401  (registers every model with Base.metadata)
    from app.core.config import get_settings
    from app.db.base import Base

    api_dir = bundle / "api" if getattr(sys, "frozen", False) else bundle / "apps" / "api"
    config = Config(str(api_dir / "alembic.ini"))
    config.set_main_option("script_location", str(api_dir / "migrations"))
    config.attributes["configure_logger"] = False

    sync_url = get_settings().database_url.replace("sqlite+aiosqlite", "sqlite")
    engine = create_engine(sync_url)
    try:
        has_schema = inspect(engine).has_table("alembic_version")
        if not has_schema:
            # A new install gets the current schema directly: the early
            # migrations were written for PostgreSQL and alter tables in
            # ways SQLite can't. Recording it as "head" means every later
            # (SQLite-safe) migration applies normally on upgrade.
            Base.metadata.create_all(engine)
    finally:
        engine.dispose()
    if has_schema:
        command.upgrade(config, "head")
    else:
        command.stamp(config, "head")


def _port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex(("127.0.0.1", port)) != 0


def _choose_port() -> int:
    if _port_is_free(PREFERRED_PORT):
        return PREFERRED_PORT
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _healthy(url: str) -> bool:
    try:
        with urllib.request.urlopen(f"{url}/health", timeout=2) as response:  # noqa: S310
            return response.status == 200
    except OSError:
        return False


def _running_instance(data_dir: Path) -> str | None:
    state = data_dir / "running.json"
    try:
        url = json.loads(state.read_text(encoding="utf-8"))["url"]
    except (OSError, ValueError, KeyError):
        return None
    return url if _healthy(url) else None


def _find_edge() -> str | None:
    candidates = [shutil.which("msedge")]
    for env_var in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA"):
        base = os.environ.get(env_var)
        if base:
            candidates.append(str(Path(base) / "Microsoft" / "Edge" / "Application" / "msedge.exe"))
    return next((c for c in candidates if c and Path(c).is_file()), None)


def _open_window(url: str, data_dir: Path) -> subprocess.Popen | None:  # type: ignore[type-arg]
    edge = _find_edge()
    if edge is None:
        webbrowser.open(url)
        return None
    return subprocess.Popen(
        [
            edge,
            f"--app={url}",
            # A profile of its own: the window is then a separate browser
            # process that exits when the user closes it, and the app's
            # login stays apart from the user's normal browsing.
            f"--user-data-dir={data_dir / 'window'}",
            "--no-first-run",
            "--no-default-browser-check",
            "--window-size=1400,900",
        ]
    )


def _show_error(message: str) -> None:
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, message, APP_NAME, 0x10)
    except Exception:
        print(message, file=sys.stderr)


# Shown the moment the window opens, while the engine starts (3-4 seconds,
# longer on the first launch after a reboot while Windows scans the app).
# It polls the local server and switches to the app as soon as it answers.
_STARTING_PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>Termvera</title>
<style>
  html,body{height:100%;margin:0;background:#fbfbfd;font-family:"Segoe UI",system-ui,sans-serif;color:#14163a}
  main{height:100%;display:grid;place-content:center;justify-items:center;gap:18px}
  svg{width:64px;height:64px}
  p{margin:0;color:#55587a;font-size:15px}
  .bar{width:180px;height:4px;border-radius:4px;background:#e8e8f8;overflow:hidden}
  .bar i{display:block;height:100%;width:40%;border-radius:4px;background:#4b47e0;animation:slide 1.2s ease-in-out infinite}
  @keyframes slide{0%{transform:translateX(-100%)}100%{transform:translateX(260%)}}
</style></head><body><main>
<svg viewBox="0 0 32 32"><rect width="32" height="32" rx="8.5" fill="#3f3bc4"/><rect x="7" y="7.2" width="18" height="4.2" rx="2.1" fill="#fff"/>
<path d="M13.9 11.2 L16.2 23.2 L23.6 13.8" fill="none" stroke="#2dd4bf" stroke-width="3.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
<p>Starting Termvera&hellip;</p><div class="bar"><i></i></div>
</main><script>
  const url = "__URL__";
  (function poll() {
    fetch(url + "/health", { mode: "no-cors", cache: "no-store" })
      .then(() => location.replace(url + "/"))
      .catch(() => setTimeout(poll, 300));
  })();
</script></body></html>"""

# After the last window closes, the server waits this long before stopping,
# so reopening the app straight away finds it still running.
_CLOSE_GRACE_SECONDS = 5


def _starting_page(data_dir: Path, url: str) -> str:
    page = data_dir / "starting.html"
    page.write_text(_STARTING_PAGE.replace("__URL__", url), encoding="utf-8")
    return page.as_uri()


def _join_running_instance(lock: "_InstanceLock", data_dir: Path) -> str | None:
    """Another copy holds the data folder. Wait until it's answering (then
    use it) or until it has finished shutting down (then take over)."""
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        url = _running_instance(data_dir)
        if url:
            return url
        if lock.try_acquire():
            return None
        time.sleep(0.3)
    raise TimeoutError


def main() -> int:
    bundle = _bundle_dir()
    data_dir = _data_dir()
    _redirect_output(data_dir)
    show_window = "--no-window" not in sys.argv

    lock = _InstanceLock(data_dir / "instance.lock")
    if not lock.try_acquire():
        try:
            existing = _join_running_instance(lock, data_dir)
        except TimeoutError:
            _show_error(f"{APP_NAME} is already starting. If no window appears, restart your computer.")
            return 1
        if existing:
            if show_window:
                _open_window(existing, data_dir)
            return 0
        # The other copy has exited; this one takes over below.

    port = _choose_port()
    url = f"http://127.0.0.1:{port}"
    # Open the window straight away on the starting page; it switches to the
    # app by itself once the server answers.
    window = _open_window(_starting_page(data_dir, url), data_dir) if show_window else None

    _configure_environment(bundle, data_dir)
    try:
        _init_database(bundle)
    except Exception as exc:
        _show_error(f"{APP_NAME} could not prepare its database.\n\n{exc}\n\nLogs: {data_dir / 'logs'}")
        raise

    import uvicorn

    from app.main import app

    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_config=None, access_log=False)
    )
    thread = threading.Thread(target=server.run, name="api", daemon=True)
    thread.start()

    deadline = time.monotonic() + 90
    while not _healthy(url):
        if not thread.is_alive() or time.monotonic() > deadline:
            _show_error(f"{APP_NAME} could not start.\n\nLogs: {data_dir / 'logs'}")
            return 1
        time.sleep(0.2)

    state = data_dir / "running.json"
    state_text = json.dumps({"url": url, "pid": os.getpid()})
    state.write_text(state_text, encoding="utf-8")
    try:
        if window is not None:
            window.wait()
            while True:
                # Keep serving while any app window is open (a second launch
                # opens more windows onto this server through the profile).
                while _profile_in_use(data_dir):
                    time.sleep(2)
                # Last window closed. Stop advertising the server, but give a
                # quick reopen a few seconds to find it before shutting down.
                state.unlink(missing_ok=True)
                time.sleep(_CLOSE_GRACE_SECONDS)
                if not _profile_in_use(data_dir):
                    break
                state.write_text(state_text, encoding="utf-8")
        else:
            # No window to watch (default-browser fallback or --no-window):
            # keep serving until the process is stopped or the user signs out.
            thread.join()
    finally:
        state.unlink(missing_ok=True)
        server.should_exit = True
        thread.join(timeout=10)
    return 0


def _profile_in_use(data_dir: Path) -> bool:
    """True while any Edge window using the app's profile is still open.
    Chromium holds this lock file open for as long as the profile is in use."""
    lock = data_dir / "window" / "lockfile"
    if not lock.exists():
        return False
    try:
        lock.unlink()
    except OSError:
        return True
    return False


if __name__ == "__main__":
    if not getattr(sys, "frozen", False):
        # Running from source: make `import app` resolve to apps/api/app.
        sys.path.insert(0, str(_bundle_dir() / "apps" / "api"))
    sys.exit(main())
