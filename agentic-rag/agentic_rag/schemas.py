"""Shared schemas for the Agentic RAG backend, graph, and frontend."""

from __future__ import annotations

from typing import Any, TypedDict

from pydantic import BaseModel, Field


class Evidence(TypedDict):
    source_id: str
    title: str
    source: str
    score: float
    snippet: str
    content: str


class AgenticRAGState(TypedDict):
    question: str
    current_query: str
    search_history: list[str]
    evidence: list[Evidence]
    rounds: int
    judge: dict[str, Any]
    answer: str


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    session_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    response_time_seconds: float
    trace: dict[str, Any]


class SourceDocument(BaseModel):
    id: str
    title: str
    source: str
    content: str


class SourcesResponse(BaseModel):
    sources: list[SourceDocument]


class HealthResponse(BaseModel):
    status: str
    model: str
    openai_api_base: str
    max_retrieval_rounds: int
    documents: int
    langfuse: dict[str, str | bool]
