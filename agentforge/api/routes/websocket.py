"""websocket.py — deprecated shim, kept for backward compat. Use ws.py."""
# This file previously duplicated WebSocket routes that now live in ws.py.
# It is kept as a no-op shim so any old import does not crash.
from agentforge.api.routes.ws import router  # noqa: F401
