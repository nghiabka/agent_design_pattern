"""Application service layer for Gemini Agentic RAG."""

from __future__ import annotations

import time
from typing import Any

from gemini_rag.graph import run_question as _run_question
from gemini_rag.graph import run_question_state as _run_question_state
from gemini_rag.schemas import GeminiRAGState


def compact_trace(state: GeminiRAGState, elapsed: float) -> dict[str, Any]:
    return {
        "elapsed": elapsed,
        "complexity": state.get("complexity", ""),
        "orchestrator_reason": state.get("orchestrator_reason", ""),
        "plan": state.get("plan", {}),
        "sub_queries": state.get("sub_queries", []),
        "sufficiency": state.get("sufficiency", {}),
        "hop": state.get("hop", 0),
        "max_hops": state.get("max_hops", 3),
        "hop_history": state.get("hop_history", []),
        "evidence_count": len(state.get("evidence", [])),
        "evidence_ids": [e["source_id"] for e in state.get("evidence", [])],
    }


def run_question_state(
    question: str,
    show_question: bool = False,
    session_id: str | None = None,
    user_id: str | None = None,
) -> GeminiRAGState:
    return _run_question_state(
        question=question,
        show_question=show_question,
        session_id=session_id,
        user_id=user_id,
    )


def run_question(
    question: str,
    session_id: str | None = None,
    user_id: str | None = None,
) -> str:
    return _run_question(
        question,
        session_id=session_id,
        user_id=user_id,
    )


def run_with_trace(
    question: str,
    session_id: str | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    start = time.time()
    state = run_question_state(
        question,
        show_question=True,
        session_id=session_id,
        user_id=user_id,
    )
    elapsed = time.time() - start
    return {
        "answer": state["answer"],
        "response_time_seconds": round(elapsed, 3),
        "trace": compact_trace(state, elapsed),
    }
