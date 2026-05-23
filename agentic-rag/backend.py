"""FastAPI entrypoint.

Run:
    uv run uvicorn backend:app --host 0.0.0.0 --port 8000
"""

from agentic_rag.api import app

__all__ = ["app"]
