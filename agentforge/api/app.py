"""app.py — deprecated entry point, kept for backward compat. Use main.py.

The canonical application factory is agentforge.api.main:app.
This shim re-exports it so that any code or config pointing at
'agentforge.api.app:app' continues to work without changes.
"""
from agentforge.api.main import app  # noqa: F401

__all__ = ["app"]
