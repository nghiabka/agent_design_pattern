"""Shared schemas for the Agentic RAG backend, graph, and frontend."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

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
    protected_question: str
    pii_masks: dict[str, str]
    guardrail: dict[str, Any]
    intent_route: str
    intent: dict[str, Any]
    reasoner: dict[str, Any]
    current_query: str
    retrieval_queries: list[str]
    required_evidence: list[str]
    search_history: list[str]
    evidence: list[Evidence]
    rounds: int
    judge: dict[str, Any]
    failure_notes: list[str]
    budget: dict[str, Any]
    output_guard: dict[str, Any]
    answer: str


class ReasonerContract(BaseModel):
    action: Literal["retrieve", "clarify", "finalize", "fallback"] = "retrieve"
    rewritten_query: str = ""
    retrieval_queries: list[str] = Field(default_factory=list)
    plan: list[str] = Field(default_factory=list)
    required_evidence: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    stop_reason: str = ""


class RetrievalJudgeDecision(BaseModel):
    sufficient: bool = False
    coverage_score: float = Field(default=0.0, ge=0.0, le=1.0)
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    source_quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    reason: str = ""
    covered: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    accepted_source_ids: list[str] = Field(default_factory=list)
    rewrite_queries: list[str] = Field(default_factory=list)
    rewrite_query: str = ""
    reflection_note: str = ""


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
