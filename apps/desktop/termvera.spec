# PyInstaller recipe for the Termvera desktop app. Run through build.ps1,
# which prepares the web export and the trimmed Tesseract first.
# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH).resolve().parent.parent  # noqa: F821  (SPECPATH is set by PyInstaller)
API = ROOT / "apps" / "api"
BUILD = ROOT / "build" / "desktop"

datas = [
    (str(ROOT / "apps" / "web" / "out"), "web"),
    (str(BUILD / "tesseract"), "tesseract"),
    (str(API / "alembic.ini"), "api"),
    (str(API / "migrations"), "api/migrations"),
    (str(ROOT / "sample_data"), "sample_data"),
    (str(ROOT / "prompts"), "prompts"),
]
datas += collect_data_files("docx")  # python-docx's default template and XML parts
datas += collect_data_files("striprtf")

hiddenimports = (
    collect_submodules("app")
    # Loaded by name at runtime rather than imported, so PyInstaller can't see them.
    + collect_submodules("uvicorn")
    + collect_submodules("passlib.handlers")
    + collect_submodules("alembic")
    + [
        "aiosqlite",
        "sqlalchemy.dialects.sqlite.aiosqlite",
        "sqlalchemy.dialects.sqlite.pysqlite",
        "logging.config",
    ]
)

a = Analysis(  # noqa: F821
    [str(ROOT / "apps" / "desktop" / "launcher.py")],
    pathex=[str(API)],
    datas=datas,
    hiddenimports=hiddenimports,
    # Server-deployment and dev-only packages the desktop build never uses:
    # it runs on SQLite. (The anthropic SDK stays: app.services.analysis
    # imports it at startup, though the launcher pins the offline engine.)
    excludes=["asyncpg", "psycopg2", "pytest", "mypy", "ruff", "tkinter", "IPython"],
    noarchive=False,
)
pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Termvera",
    console=False,
    icon=str(ROOT / "apps" / "desktop" / "termvera.ico"),
    version=str(BUILD / "version_info.txt"),
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    name="Termvera",
)
