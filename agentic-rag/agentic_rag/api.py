"""FastAPI backend for the Agentic RAG chatbot.

Run:
    uv run uvicorn backend:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from agentic_rag.documents import DOCUMENTS
from agentic_rag.observability import langfuse_status
from agentic_rag.schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    SourceDocument,
    SourcesResponse,
)
from agentic_rag.service import run_chat
from agentic_rag.settings import MAX_RETRIEVAL_ROUNDS, OPENAI_API_BASE, OPENAI_MODEL_NAME


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


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Process-Time-Seconds"] = f"{time.perf_counter() - start:.3f}"
    return response


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        model=OPENAI_MODEL_NAME,
        openai_api_base=OPENAI_API_BASE,
        max_retrieval_rounds=MAX_RETRIEVAL_ROUNDS,
        documents=len(DOCUMENTS),
        langfuse=langfuse_status(),
    )


@app.get("/sources", response_model=SourcesResponse)
def sources() -> SourcesResponse:
    return SourcesResponse(
        sources=[
            SourceDocument(
                id=doc.id,
                title=doc.title,
                source=doc.source,
                content=doc.content,
            )
            for doc in DOCUMENTS
        ]
    )


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")

    try:
        return run_chat(question, session_id=request.session_id)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"{type(exc).__name__}: {exc}",
        ) from exc
