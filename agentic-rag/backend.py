"""FastAPI backend for the Agentic RAG chatbot.

Run:
    uv run uvicorn backend:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent import AgenticRAGState, run_question_state
from config import MAX_RETRIEVAL_ROUNDS, OPENAI_API_BASE, OPENAI_MODEL_NAME
from documents import DOCUMENTS
from tracing import langfuse_status


app = FastAPI(
    title="Agentic RAG Backend",
    description="Backend API for Agentic RAG chat, retrieval trace, sources, and Langfuse tracing.",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    session_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    trace: dict[str, Any]


def compact_trace(state: AgenticRAGState, elapsed: float) -> dict[str, Any]:
    return {
        "elapsed": elapsed,
        "rounds": state.get("rounds", 0),
        "search_history": state.get("search_history", []),
        "judge": state.get("judge", {}),
        "evidence": state.get("evidence", []),
    }


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "model": OPENAI_MODEL_NAME,
        "openai_api_base": OPENAI_API_BASE,
        "max_retrieval_rounds": MAX_RETRIEVAL_ROUNDS,
        "documents": len(DOCUMENTS),
        "langfuse": langfuse_status(),
    }


@app.get("/sources")
def sources() -> dict[str, Any]:
    return {
        "sources": [
            {
                "id": doc.id,
                "title": doc.title,
                "source": doc.source,
                "content": doc.content,
            }
            for doc in DOCUMENTS
        ]
    }


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")

    start = time.time()
    try:
        state = run_question_state(question, session_id=request.session_id)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"{type(exc).__name__}: {exc}",
        ) from exc

    return ChatResponse(
        answer=state["answer"],
        trace=compact_trace(state, time.time() - start),
    )
