from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent.parent.parent / "prompts"

CLAUSE_EXTRACTION_VERSION = "v1"
RISK_ANALYSIS_VERSION = "v1"
MISSING_PROTECTIONS_VERSION = "v1"


def load_prompt(module: str, version: str) -> str:
    return (PROMPTS_DIR / module / f"{version}.md").read_text(encoding="utf-8")
