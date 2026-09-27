"""Repository paths resolved once.

Four modules previously each counted `.parent` hops from their own depth to
reach sample_data/, and one of them was off by one, which only showed up as
a sample document reporting a size of zero. Resolve it here instead.

In the desktop build the source tree doesn't exist; the launcher points
RESOURCE_DIR at the bundled copies of these folders.
"""

from pathlib import Path

from app.core.config import get_settings

# app/core/paths.py -> app/core -> app -> apps/api -> apps -> repo root
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
RESOURCE_ROOT = Path(get_settings().resource_dir or REPO_ROOT)
SAMPLE_DATA_DIR = RESOURCE_ROOT / "sample_data"
PROMPTS_DIR = RESOURCE_ROOT / "prompts"
