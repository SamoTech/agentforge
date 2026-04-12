"""
DEPRECATED: This file is kept for backwards compatibility only.
The canonical WebSocket router is agentforge/api/routes/ws.py

Do NOT add new routes here. Use:
    from agentforge.api.routes.ws import router
"""
import warnings

warnings.warn(
    "agentforge.api.routes.websocket is deprecated. Use agentforge.api.routes.ws instead.",
    DeprecationWarning,
    stacklevel=2,
)

from agentforge.api.routes.ws import router  # noqa: F401, E402

__all__ = ["router"]
