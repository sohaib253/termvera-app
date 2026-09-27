
from app.core.paths import PROMPTS_DIR

CLAUSE_EXTRACTION_VERSION = "v1"
RISK_ANALYSIS_VERSION = "v1"
MISSING_PROTECTIONS_VERSION = "v1"


def load_prompt(module: str, version: str) -> str:
    return (PROMPTS_DIR / module / f"{version}.md").read_text(encoding="utf-8")
