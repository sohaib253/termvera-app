from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"

    # Product name, used in the API title and anywhere the backend names the
    # product. The web app's copy lives in apps/web/lib/brand.ts.
    app_name: str = "Termvera"

    database_url: str = "postgresql+asyncpg://tenderguard:tenderguard@localhost:5432/tenderguard"

    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    cors_origins: list[str] = ["http://localhost:3000"]

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-opus-5"

    # Analysis engines. "brain" is the built-in rule-based expert engine
    # (app/services/brain): no model, no API key, no GPU, runs anywhere.
    # "claude" and (ClauseRisk only) "ollama" remain available. Only the
    # factory functions may branch on these strings.
    tenderguard_ai_provider: str = "brain"
    clauserisk_ai_provider: str = "brain"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "mistral:7b-instruct"

    # Document ingestion. Scanned PDFs and images are read with Tesseract
    # OCR; TESSERACT_CMD only needs setting when tesseract.exe is neither
    # on PATH nor in a standard install folder (see app/services/ocr.py).
    # .docx, .rtf and .odt need nothing installed. Legacy .doc is converted
    # by Microsoft Word when present, else LibreOffice (LIBREOFFICE_PATH
    # only if it is outside the standard install folders).
    tesseract_cmd: str | None = None
    ocr_languages: str = "eng"
    ocr_dpi: int = 300
    ocr_workers: int = 0  # 0 = half the CPU cores, capped at 8
    libreoffice_path: str | None = None

    # Early-access launch: with billing off, every workspace is on the free
    # plan (no trial countdown, no view-only mode). Turning it on later
    # starts a fresh TRIAL_DAYS trial for existing free users, then the
    # paid plans apply. The desktop build sets it in apps/desktop/launcher.py.
    billing_enabled: bool = True

    # Desktop (offline) install. The launcher (apps/desktop/launcher.py)
    # sets these; a server deployment leaves them unset.
    # data_dir: where uploads, the SQLite database and logs live.
    # web_dist_dir: the exported web app, served by this API at "/".
    # resource_dir: bundled read-only files (sample_data/, prompts/).
    data_dir: str | None = None
    web_dist_dir: str | None = None
    resource_dir: str | None = None
    log_file: str | None = None

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_desktop(self) -> bool:
        return self.environment == "desktop"


@lru_cache
def get_settings() -> Settings:
    return Settings()
