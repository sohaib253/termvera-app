"""Repository paths resolved once.

Four modules previously each counted `.parent` hops from their own depth to
reach sample_data/, and one of them was off by one, which only showed up as
a sample document reporting a size of zero. Resolve it here instead.
"""

from pathlib import Path

# app/core/paths.py -> app/core -> app -> apps/api -> apps -> repo root
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
SAMPLE_DATA_DIR = REPO_ROOT / "sample_data"
