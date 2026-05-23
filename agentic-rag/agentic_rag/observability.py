"""Langfuse tracing helpers for the Agentic RAG demo."""

from __future__ import annotations

import os
from typing import Any

from agentic_rag.settings import (
    LANGFUSE_ENABLED,
    LANGFUSE_HOST,
    LANGFUSE_PUBLIC_KEY,
    LANGFUSE_SECRET_KEY,
    OPENAI_MODEL_NAME,
)


def _set_langfuse_env() -> None:
    """Langfuse's LangChain callback reads credentials from env vars."""
    if LANGFUSE_PUBLIC_KEY:
        os.environ["LANGFUSE_PUBLIC_KEY"] = LANGFUSE_PUBLIC_KEY
    if LANGFUSE_SECRET_KEY:
        os.environ["LANGFUSE_SECRET_KEY"] = LANGFUSE_SECRET_KEY
    if LANGFUSE_HOST:
        os.environ["LANGFUSE_HOST"] = LANGFUSE_HOST


def is_langfuse_configured() -> bool:
    return bool(LANGFUSE_ENABLED and LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY)


def get_langfuse_handler():
    """Create a Langfuse callback handler if tracing is configured.

    Returns None when tracing is disabled, credentials are missing, or the
    optional langfuse dependency is unavailable.
    """
    if not is_langfuse_configured():
        return None

    _set_langfuse_env()

    try:
        from langfuse.langchain import CallbackHandler
    except ImportError:
        return None

    try:
        return CallbackHandler()
    except Exception:
        return None


def build_langfuse_config(question: str, session_id: str | None = None) -> dict[str, Any]:
    """Build LangGraph RunnableConfig with Langfuse callback and metadata."""
    handler = get_langfuse_handler()
    config: dict[str, Any] = {
        "run_name": "agentic-rag",
        "tags": ["agentic-rag", "rag", "langgraph"],
        "metadata": {
            "app": "agentic-rag-demo",
            "model": OPENAI_MODEL_NAME,
            "question": question,
        },
    }

    if session_id:
        config["metadata"]["session_id"] = session_id
        config["metadata"]["user_id"] = session_id

    if handler:
        config["callbacks"] = [handler]

    return config


def flush_langfuse() -> None:
    """Flush queued Langfuse events when tracing is configured."""
    if not is_langfuse_configured():
        return

    try:
        from langfuse import get_client

        get_client().flush()
    except Exception:
        return


def langfuse_status() -> dict[str, str | bool]:
    return {
        "enabled": LANGFUSE_ENABLED,
        "configured": is_langfuse_configured(),
        "host": LANGFUSE_HOST,
    }
