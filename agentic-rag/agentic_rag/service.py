"""Application service layer for running Agentic RAG."""

from __future__ import annotations

import time
from typing import Any

from agentic_rag.graph import run_question as _run_question
from agentic_rag.graph import run_question_state as _run_question_state
from agentic_rag.schemas import AgenticRAGState, ChatResponse


def compact_trace(state: AgenticRAGState, elapsed: float) -> dict[str, Any]:
    return {
        "elapsed": elapsed,
        "guardrail": state.get("guardrail", {}),
        "intent_route": state.get("intent_route", "rag"),
        "intent": state.get("intent", {}),
        "reasoner": state.get("reasoner", {}),
        "required_evidence": state.get("required_evidence", []),
        "rounds": state.get("rounds", 0),
        "retrieval_queries": state.get("retrieval_queries", []),
        "search_history": state.get("search_history", []),
        "judge": state.get("judge", {}),
        "failure_notes": state.get("failure_notes", []),
        "budget": state.get("budget", {}),
        "output_guard": state.get("output_guard", {}),
        "evidence": state.get("evidence", []),
    }


def run_question_state(
    question: str,
    show_question: bool = False,
    session_id: str | None = None,
) -> AgenticRAGState:
    return _run_question_state(
        question=question,
        show_question=show_question,
        session_id=session_id,
    )


def run_question(question: str) -> str:
    return _run_question(question)


def run_chat(question: str, session_id: str | None = None) -> ChatResponse:
    start = time.time()
    state = run_question_state(question, session_id=session_id)
    elapsed = time.time() - start
    return ChatResponse(
        answer=state["answer"],
        response_time_seconds=round(elapsed, 3),
        trace=compact_trace(state, elapsed),
    )
