"""Shared schemas for the 5-agent Gemini Agentic RAG workflow."""

from __future__ import annotations

from typing import Any, TypedDict

from pydantic import BaseModel, Field


# ── Evidence ────────────────────────────────────────────────────────────────

class Evidence(TypedDict):
    source_id: str
    title: str
    source: str
    corpus: str
    score: float
    snippet: str
    content: str


# ── LangGraph State ─────────────────────────────────────────────────────────

class GeminiRAGState(TypedDict):
    # User input
    question: str

    # 1. Orchestrator
    complexity: str  # "simple" | "complex"
    orchestrator_reason: str

    # 2. Planning Agent
    plan: dict[str, Any]  # selected_corpora, strategy, reason

    # 3. Query Rewriter
    sub_queries: list[dict[str, Any]]  # [{query, target_corpus}]

    # 4. Search Fanout
    evidence: list[Evidence]

    # 5. Sufficient Context
    sufficiency: dict[str, Any]  # sufficient, missing_pieces, reason, confidence

    # Loop control
    hop: int
    max_hops: int
    hop_history: list[dict[str, Any]]  # [{hop, corpora, queries, result}]

    # Output
    answer: str


# ── Pydantic models for LLM output parsing ─────────────────────────────────

class OrchestratorDecision(BaseModel):
    complexity: str = Field(default="complex", description="simple or complex")
    reason: str = ""
    suggested_corpora: list[str] = Field(default_factory=list)


class PlanningDecision(BaseModel):
    selected_corpora: list[str] = Field(default_factory=list)
    strategy: str = ""
    reason: str = ""


class SubQuery(BaseModel):
    query: str
    target_corpus: str


class QueryRewriteResult(BaseModel):
    sub_queries: list[SubQuery] = Field(default_factory=list)
    reasoning: str = ""


class SufficiencyDecision(BaseModel):
    sufficient: bool = False
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    covered: list[str] = Field(default_factory=list)
    missing_pieces: list[str] = Field(default_factory=list)
    reason: str = ""
    next_corpora: list[str] = Field(default_factory=list)
    rewrite_hint: str = ""
