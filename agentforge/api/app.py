"""
DEPRECATED: This file is kept for backwards compatibility only.
The canonical FastAPI app entry point is agentforge/api/main.py

Do NOT import from this file. Use:
    from agentforge.api.main import app
"""
import warnings

warnings.warn(
    "agentforge.api.app is deprecated. Use agentforge.api.main instead.",
    DeprecationWarning,
    stacklevel=2,
)

from agentforge.api.main import app  # noqa: F401, E402

__all__ = ["app"]
