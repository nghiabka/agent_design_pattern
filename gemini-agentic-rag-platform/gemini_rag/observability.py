"""Optional Langfuse tracing for the Agentic RAG workflow."""

from __future__ import annotations

from typing import Any

from langfuse import Langfuse, propagate_attributes
from langfuse.langchain import CallbackHandler
from rich.console import Console

from gemini_rag import __version__
from gemini_rag.settings import (
    LANGFUSE_BASE_URL,
    LANGFUSE_ENABLED,
    LANGFUSE_ENVIRONMENT,
    LANGFUSE_FLUSH_ON_RUN,
    LANGFUSE_PUBLIC_KEY,
    LANGFUSE_SECRET_KEY,
    MAX_HOPS,
    OPENAI_ENABLE_THINKING,
    OPENAI_MODEL_NAME,
)

console = Console()

_client: Langfuse | None = None
_warning_shown = False


class IterationAwareCallbackHandler(CallbackHandler):
    """Label repeated LangGraph nodes with their retrieval hop."""

    def on_chain_start(
        self,
        serialized: dict[str, Any] | None,
        inputs: Any,
        **kwargs: Any,
    ) -> Any:
        metadata = kwargs.get("metadata") or {}
        original_name = self.get_langchain_run_name(serialized, **kwargs)
        hop = inputs.get("hop") if isinstance(inputs, dict) else None

        if isinstance(hop, int):
            if original_name in {"planning_agent", "query_rewriter", "search_fanout"}:
                iteration = hop + 1
            elif original_name in {
                "sufficient_context",
                "route_after_sufficiency",
                "answer",
                "fallback",
            }:
                iteration = max(hop, 1)
            else:
                iteration = None

            if iteration is not None and metadata.get("langgraph_node"):
                kwargs["name"] = f"hop-{iteration}/{original_name}"

        return super().on_chain_start(serialized, inputs, **kwargs)


def _warn(message: str) -> None:
    global _warning_shown
    if not _warning_shown:
        console.print(f"[yellow]Langfuse disabled: {message}[/yellow]")
        _warning_shown = True


def get_langfuse_client() -> Langfuse | None:
    """Return the configured singleton client, or None when tracing is disabled."""
    global _client

    if not LANGFUSE_ENABLED:
        return None

    if not LANGFUSE_PUBLIC_KEY or not LANGFUSE_SECRET_KEY:
        _warn("thiếu LANGFUSE_PUBLIC_KEY hoặc LANGFUSE_SECRET_KEY.")
        return None

    if _client is None:
        try:
            _client = Langfuse(
                public_key=LANGFUSE_PUBLIC_KEY,
                secret_key=LANGFUSE_SECRET_KEY,
                base_url=LANGFUSE_BASE_URL,
                environment=LANGFUSE_ENVIRONMENT,
                release=__version__,
            )
        except Exception as exc:
            _warn(f"không khởi tạo được client ({exc}).")
            return None

    return _client


def invoke_graph(
    graph: Any,
    state: dict[str, Any],
    *,
    question: str,
    session_id: str | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Invoke LangGraph with Langfuse callbacks and a root agent observation."""
    client = get_langfuse_client()
    if client is None:
        return graph.invoke(state)

    try:
        handler = IterationAwareCallbackHandler(public_key=LANGFUSE_PUBLIC_KEY)
    except Exception as exc:
        _warn(f"không khởi tạo được callback ({exc}).")
        return graph.invoke(state)

    metadata = {
        "model": OPENAI_MODEL_NAME,
        "maxhops": str(MAX_HOPS),
        "thinking": str(OPENAI_ENABLE_THINKING).lower(),
        "application": "gemini-agentic-rag-demo",
    }
    config = {
        "callbacks": [handler],
        "run_name": "gemini-agentic-rag-graph",
        "tags": ["agentic-rag", "cross-corpus"],
        "metadata": metadata,
    }

    try:
        with client.start_as_current_observation(
            name="gemini-agentic-rag-question",
            as_type="agent",
            input={"question": question},
            metadata=metadata,
        ) as root_observation:
            with propagate_attributes(
                user_id=user_id,
                session_id=session_id,
                metadata=metadata,
                version=__version__,
                tags=["agentic-rag", "cross-corpus"],
                trace_name="gemini-agentic-rag",
            ):
                try:
                    result = graph.invoke(state, config=config)
                except Exception as exc:
                    root_observation.update(
                        level="ERROR",
                        status_message=str(exc)[:500],
                    )
                    raise

                root_observation.update(
                    output={
                        "answer": result.get("answer", ""),
                        "complexity": result.get("complexity", ""),
                        "hop": result.get("hop", 0),
                        "evidence_count": len(result.get("evidence", [])),
                    }
                )
                return result
    finally:
        if LANGFUSE_FLUSH_ON_RUN:
            client.flush()
