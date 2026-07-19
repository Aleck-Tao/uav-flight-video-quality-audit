"""Quality audit for field-test video evidence."""

from __future__ import annotations

from pathlib import Path
from typing import Any

__all__ = ["audit_videos"]
__version__ = "1.0.0"


def audit_videos(video_dir: Path, results_dir: Path, **kwargs: Any) -> dict[str, object]:
    """Load the pipeline lazily so ``python -m videoaudit.pipeline`` stays warning-free."""
    from .pipeline import audit_videos as _audit_videos

    return _audit_videos(video_dir, results_dir, **kwargs)
