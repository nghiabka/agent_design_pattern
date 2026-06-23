"""
═══════════════════════════════════════════════════════════════════════
Gemini Enterprise Agentic RAG — 5-Agent Cross-Corpus Workflow
═══════════════════════════════════════════════════════════════════════

Architecture:
  Orchestrator → Planning Agent → Query Rewriter → Search Fanout
  → Sufficient Context Agent → Answer (or loop back to Planning)
"""

from __future__ import annotations

import json
import re
import time
from typing import Any, Literal

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    NotFoundError,
    RateLimitError,
)
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

from gemini_rag.documents import ALL_CORPORA, CORPUS_DESCRIPTIONS
from gemini_rag.retriever import SearchResult, cross_corpus_retriever
from gemini_rag.schemas import Evidence, GeminiRAGState
from gemini_rag.settings import (
    MAX_HOPS,
    OPENAI_API_BASE,
    OPENAI_API_KEY,
    OPENAI_MAX_ATTEMPTS,
    OPENAI_MODEL_NAME,
    OPENAI_TIMEOUT_SECONDS,
)

console = Console()


def _create_llm(temperature: float = 0) -> ChatOpenAI:
    return ChatOpenAI(
        model=OPENAI_MODEL_NAME,
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_API_BASE,
        temperature=temperature,
        timeout=OPENAI_TIMEOUT_SECONDS,
        max_retries=0,
    )


def _invoke_llm(llm: ChatOpenAI, prompt: str):
    """Retry transient model gateway failures without hiding permanent 404s."""
    for attempt in range(1, OPENAI_MAX_ATTEMPTS + 1):
        try:
            return llm.invoke([HumanMessage(content=prompt)])
        except NotFoundError as exc:
            details = f"{exc} {getattr(exc, 'body', '')}".lower()
            if "<html" not in details and "nginx" not in details:
                raise
            error = exc
        except (APIConnectionError, APITimeoutError, InternalServerError, RateLimitError) as exc:
            error = exc

        if attempt >= OPENAI_MAX_ATTEMPTS:
            raise error

        delay = 2 ** (attempt - 1)
        console.print(
            f"  [yellow]Model gateway lỗi tạm thời "
            f"({type(error).__name__}), thử lại {attempt + 1}/{OPENAI_MAX_ATTEMPTS} "
            f"sau {delay}s...[/yellow]"
        )
        time.sleep(delay)

    raise RuntimeError("Không thể gọi model.")


def _extract_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0].strip()

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end >= start:
        text = text[start : end + 1]

    return json.loads(text)


def _format_evidence_short(evidence: list[Evidence]) -> str:
    if not evidence:
        return "Chưa có evidence."
    blocks: list[str] = []
    for item in evidence:
        blocks.append(
            f"[{item['source_id']}] ({item['corpus']}) {item['title']}\n"
            f"Score: {item['score']}\n"
            f"{item['snippet']}"
        )
    return "\n\n---\n\n".join(blocks)


def _format_corpus_descriptions() -> str:
    lines: list[str] = []
    for name, desc in CORPUS_DESCRIPTIONS.items():
        doc_count = len(ALL_CORPORA[name].documents) if name in ALL_CORPORA else 0
        lines.append(f"- **{name}** ({doc_count} docs): {desc}")
    return "\n".join(lines)


def _merge_evidence(existing: list[Evidence], results: list[SearchResult]) -> list[Evidence]:
    by_id: dict[str, Evidence] = {item["source_id"]: item for item in existing}

    for result in results:
        doc = result.document
        new_item: Evidence = {
            "source_id": doc.id,
            "title": doc.title,
            "source": doc.source,
            "corpus": doc.corpus_name,
            "score": result.score,
            "snippet": result.snippet,
            "content": doc.content,
        }
        current = by_id.get(doc.id)
        if current is None or result.score > current["score"]:
            by_id[doc.id] = new_item

    return sorted(by_id.values(), key=lambda item: item["score"], reverse=True)


# ═══════════════════════════════════════════════════════════════════════
# PROMPTS
# ═══════════════════════════════════════════════════════════════════════

ORCHESTRATOR_PROMPT = """Bạn là Orchestrator Agent trong hệ thống Agentic RAG cross-corpus.

Câu hỏi của user:
{question}

Các corpus có sẵn:
{corpus_descriptions}

Nhiệm vụ: đánh giá câu hỏi thuộc loại nào:

- "simple": câu hỏi chỉ cần tìm trong 1 corpus duy nhất, không cần kết nối thông tin.
  Ví dụ: "Server SRV-042 có cấu hình gì?" → chỉ cần corpus infra.
- "complex": câu hỏi cần thông tin từ NHIỀU corpus hoặc cần multi-hop reasoning.
  Ví dụ: "Ai phụ trách server có incident nhiều nhất?" → cần infra + hr.

Trả về JSON chính xác:
{{
  "complexity": "simple",
  "reason": "lý do ngắn",
  "suggested_corpora": ["corpus1", "corpus2"]
}}"""

PLANNING_PROMPT = """Bạn là Planning Agent. Dựa trên câu hỏi và corpus descriptions,
chọn corpus nào cần search và chiến lược tìm kiếm.

Câu hỏi:
{question}

Các corpus có sẵn:
{corpus_descriptions}

Evidence hiện có:
{current_evidence}

Hop history:
{hop_history}

Nhiệm vụ:
- Chọn 1-3 corpus phù hợp nhất cho HOP hiện tại.
- Nếu đã có evidence từ hop trước, chọn corpus BỔ SUNG để lấp missing pieces.
- Giải thích chiến lược ngắn gọn.

Trả về JSON:
{{
  "selected_corpora": ["corpus1"],
  "strategy": "mô tả chiến lược tìm kiếm",
  "reason": "tại sao chọn corpus này"
}}"""

QUERY_REWRITER_PROMPT = """Bạn là Query Rewriter Agent. Tách câu hỏi phức tạp thành sub-queries
được tối ưu cho từng corpus.

Câu hỏi gốc:
{question}

Corpus được chọn: {selected_corpora}

Evidence hiện có:
{current_evidence}

Missing pieces cần tìm:
{missing_pieces}

Nhiệm vụ:
- Tạo 1-3 sub-queries cụ thể, ngắn gọn.
- Mỗi sub-query gắn với 1 target corpus.
- Dùng từ khóa và thuật ngữ phù hợp với nội dung corpus.
- Nếu evidence trước có chứa ID (ví dụ SRV-042), dùng ID đó trong sub-query mới.

Trả về JSON:
{{
  "sub_queries": [
    {{"query": "câu truy vấn cụ thể", "target_corpus": "corpus_name"}},
    {{"query": "câu truy vấn khác", "target_corpus": "corpus_name"}}
  ],
  "reasoning": "giải thích ngắn"
}}"""

SUFFICIENT_CONTEXT_PROMPT = """Bạn là Sufficient Context Agent — quality gate quan trọng nhất.

Dựa trên paper "Sufficient Context" (ICLR 2025): đánh giá xem evidence hiện có
có ĐỦ THÔNG TIN để một "diligent reader" trả lời CHÍNH XÁC và ĐẦY ĐỦ câu hỏi không.

Câu hỏi:
{question}

Evidence hiện có:
{evidence}

Hop history:
{hop_history}

Nhiệm vụ:
1. Liệt kê thông tin CẦN CÓ để trả lời câu hỏi.
2. Kiểm tra evidence đã COVER những gì.
3. Xác định MISSING PIECES — thông tin còn thiếu.
4. Quyết định:
   - sufficient=true: evidence đủ để trả lời chính xác.
   - sufficient=false: thiếu thông tin quan trọng, cần tìm thêm.

Lưu ý:
- KHÔNG đánh giá relevance — chỉ đánh giá SUFFICIENCY.
- Nếu câu hỏi yêu cầu thông tin từ nhiều nguồn và chỉ có 1, đó là INSUFFICIENT.
- Nếu thiếu, gợi ý corpus nào nên tìm tiếp.

Trả về JSON:
{{
  "sufficient": false,
  "confidence": 0.7,
  "covered": ["thông tin đã có"],
  "missing_pieces": ["thông tin còn thiếu"],
  "reason": "lý do chi tiết",
  "next_corpora": ["corpus cần tìm thêm"],
  "rewrite_hint": "gợi ý query cho hop tiếp"
}}"""

ANSWER_PROMPT = """Bạn là Answer Agent trong hệ thống Agentic RAG cross-corpus.

Chỉ được dùng evidence dưới đây để trả lời. Nếu evidence không đủ,
nói rõ phần nào chưa có. Không bịa thông tin.

Câu hỏi:
{question}

Evidence (đã qua Sufficient Context check):
{evidence}

Hop history:
{hop_history}

Yêu cầu:
- Trả lời bằng tiếng Việt.
- Nêu kết luận trực tiếp trước.
- Mỗi ý chính cần citation [SOURCE_ID] từ evidence.
- Nếu thông tin đến từ nhiều corpus, nêu rõ sự kết nối.
- Trình bày có cấu trúc, dễ đọc.
"""

FALLBACK_PROMPT = """Bạn là Answer Agent. Evidence không đủ sau {max_hops} hop.

Câu hỏi: {question}

Evidence tìm được: {evidence}

Missing pieces: {missing_pieces}

Hãy trả lời bằng tiếng Việt:
- Tóm tắt thông tin đã tìm được (có citation).
- Nêu rõ phần nào CHƯA TÌM ĐƯỢC.
- Không bịa thông tin thiếu.
"""


# ═══════════════════════════════════════════════════════════════════════
# NODES
# ═══════════════════════════════════════════════════════════════════════

def orchestrator_node(state: GeminiRAGState) -> GeminiRAGState:
    """Agent 1: Assess query complexity and suggest initial corpora."""
    console.print()
    console.print(Rule("🎯 ORCHESTRATOR — Đánh giá độ phức tạp", style="bold cyan"))

    start = time.time()
    llm = _create_llm(temperature=0)
    prompt = ORCHESTRATOR_PROMPT.format(
        question=state["question"],
        corpus_descriptions=_format_corpus_descriptions(),
    )
    response = _invoke_llm(llm, prompt)
    elapsed = round(time.time() - start, 2)

    try:
        parsed = _extract_json(response.content)
        complexity = str(parsed.get("complexity", "complex")).lower().strip()
        if complexity not in {"simple", "complex"}:
            complexity = "complex"
        reason = str(parsed.get("reason", ""))
        suggested = parsed.get("suggested_corpora", [])
    except (json.JSONDecodeError, TypeError, AttributeError):
        complexity = "complex"
        reason = "Không parse được JSON, mặc định complex."
        suggested = list(ALL_CORPORA.keys())

    style = "green" if complexity == "simple" else "yellow"
    console.print(Panel(
        f"Complexity: [bold {style}]{complexity.upper()}[/bold {style}]\n"
        f"Reason: {reason}\n"
        f"Suggested corpora: {', '.join(suggested) or '—'}",
        border_style=style,
        padding=(0, 1),
    ))
    console.print(f"  ⏱️  {elapsed}s")

    return {
        "complexity": complexity,
        "orchestrator_reason": reason,
        "plan": {"selected_corpora": suggested, "strategy": "initial", "reason": reason},
    }


def planning_agent_node(state: GeminiRAGState) -> GeminiRAGState:
    """Agent 2: Select corpora and plan retrieval strategy."""
    console.print()
    console.print(Rule("📋 PLANNING AGENT — Chọn corpus & chiến lược", style="bold yellow"))

    start = time.time()
    llm = _create_llm(temperature=0)

    hop_history = state.get("hop_history", [])
    prompt = PLANNING_PROMPT.format(
        question=state["question"],
        corpus_descriptions=_format_corpus_descriptions(),
        current_evidence=_format_evidence_short(state.get("evidence", [])),
        hop_history=json.dumps(hop_history, ensure_ascii=False) if hop_history else "Chưa có",
    )
    response = _invoke_llm(llm, prompt)
    elapsed = round(time.time() - start, 2)

    try:
        parsed = _extract_json(response.content)
        selected = parsed.get("selected_corpora", [])
        strategy = parsed.get("strategy", "")
        reason = parsed.get("reason", "")
    except (json.JSONDecodeError, TypeError, AttributeError):
        # Fallback: use sufficiency hints or all corpora
        sufficiency = state.get("sufficiency", {})
        selected = sufficiency.get("next_corpora", list(ALL_CORPORA.keys()))
        strategy = "Fallback: không parse được JSON."
        reason = strategy

    # Validate corpus names
    selected = [c for c in selected if c in ALL_CORPORA] or list(ALL_CORPORA.keys())

    plan = {"selected_corpora": selected, "strategy": strategy, "reason": reason}
    console.print(Panel(
        f"Selected corpora: [bold cyan]{', '.join(selected)}[/bold cyan]\n"
        f"Strategy: {strategy}\n"
        f"Reason: {reason}",
        border_style="yellow",
        padding=(0, 1),
    ))
    console.print(f"  ⏱️  {elapsed}s")

    return {"plan": plan}


def query_rewriter_node(state: GeminiRAGState) -> GeminiRAGState:
    """Agent 3: Decompose query into targeted sub-queries."""
    console.print()
    console.print(Rule("✏️  QUERY REWRITER — Tách sub-queries", style="bold magenta"))

    start = time.time()
    llm = _create_llm(temperature=0)

    selected_corpora = state.get("plan", {}).get("selected_corpora", [])
    sufficiency = state.get("sufficiency", {})
    missing = sufficiency.get("missing_pieces", [])

    prompt = QUERY_REWRITER_PROMPT.format(
        question=state["question"],
        selected_corpora=", ".join(selected_corpora),
        current_evidence=_format_evidence_short(state.get("evidence", [])),
        missing_pieces=", ".join(missing) if missing else "Chưa xác định",
    )
    response = _invoke_llm(llm, prompt)
    elapsed = round(time.time() - start, 2)

    try:
        parsed = _extract_json(response.content)
        raw_queries = parsed.get("sub_queries", [])
        sub_queries = []
        for sq in raw_queries:
            target = sq.get("target_corpus", "")
            if target not in ALL_CORPORA and selected_corpora:
                target = selected_corpora[0]
            sub_queries.append({"query": sq.get("query", ""), "target_corpus": target})
    except (json.JSONDecodeError, TypeError, AttributeError):
        sub_queries = [
            {"query": state["question"], "target_corpus": c}
            for c in selected_corpora
        ]

    # Filter out empty queries
    sub_queries = [sq for sq in sub_queries if sq.get("query")]

    if not sub_queries:
        sub_queries = [{"query": state["question"], "target_corpus": selected_corpora[0]}]

    for idx, sq in enumerate(sub_queries, 1):
        console.print(f"  {idx}. [cyan]{sq['target_corpus']}[/cyan] ← \"{sq['query']}\"")
    console.print(f"  ⏱️  {elapsed}s")

    return {"sub_queries": sub_queries}


def search_fanout_node(state: GeminiRAGState) -> GeminiRAGState:
    """Agent 4: Execute sub-queries across corpora and aggregate results."""
    hop = state.get("hop", 0) + 1
    console.print()
    console.print(Rule(f"🔎 SEARCH FANOUT — Hop {hop}/{state.get('max_hops', MAX_HOPS)}", style="bold blue"))

    start = time.time()
    sub_queries = state.get("sub_queries", [])
    all_results: list[SearchResult] = []

    for sq in sub_queries:
        query = sq["query"]
        corpus_name = sq["target_corpus"]
        console.print(f"  [{corpus_name}] Query: [cyan]{query}[/cyan]")
        results = cross_corpus_retriever.search(query, corpus_names=[corpus_name], top_k=3)
        all_results.extend(results)
        console.print(f"    → {len(results)} results")

    elapsed = round(time.time() - start, 2)

    merged = _merge_evidence(state.get("evidence", []), all_results)

    # Display results table
    if all_results:
        table = Table(title=f"Hop {hop} Results", border_style="blue", show_lines=True)
        table.add_column("Source", style="bold cyan", width=12)
        table.add_column("Corpus", width=10)
        table.add_column("Score", justify="right", width=7)
        table.add_column("Title", width=30)
        table.add_column("Snippet", style="dim", width=50)

        seen: set[str] = set()
        for r in all_results:
            if r.document.id not in seen:
                seen.add(r.document.id)
                table.add_row(
                    r.document.id,
                    r.document.corpus_name,
                    str(r.score),
                    r.document.title,
                    r.snippet[:80] + "..." if len(r.snippet) > 80 else r.snippet,
                )
        console.print(table)
    else:
        console.print("  [yellow]Không tìm thấy kết quả.[/yellow]")

    console.print(f"  ⏱️  {elapsed}s | Total evidence: {len(merged)}")

    # Record hop history
    hop_record = {
        "hop": hop,
        "corpora": list({sq["target_corpus"] for sq in sub_queries}),
        "queries": [sq["query"] for sq in sub_queries],
        "new_docs": [r.document.id for r in all_results],
    }
    hop_history = list(state.get("hop_history", []))
    hop_history.append(hop_record)

    return {"evidence": merged, "hop": hop, "hop_history": hop_history}


def sufficient_context_node(state: GeminiRAGState) -> GeminiRAGState:
    """Agent 5: Evaluate if evidence is sufficient to answer the question."""
    console.print()
    console.print(Rule("🔍 SUFFICIENT CONTEXT AGENT — Đánh giá sufficiency", style="bold green"))

    start = time.time()
    llm = _create_llm(temperature=0)

    prompt = SUFFICIENT_CONTEXT_PROMPT.format(
        question=state["question"],
        evidence=_format_evidence_short(state.get("evidence", [])),
        hop_history=json.dumps(state.get("hop_history", []), ensure_ascii=False),
    )
    response = _invoke_llm(llm, prompt)
    elapsed = round(time.time() - start, 2)

    try:
        parsed = _extract_json(response.content)
        sufficiency = {
            "sufficient": bool(parsed.get("sufficient", False)),
            "confidence": float(parsed.get("confidence", 0.0)),
            "covered": parsed.get("covered", []),
            "missing_pieces": parsed.get("missing_pieces", []),
            "reason": parsed.get("reason", ""),
            "next_corpora": parsed.get("next_corpora", []),
            "rewrite_hint": parsed.get("rewrite_hint", ""),
        }
    except (json.JSONDecodeError, TypeError, AttributeError):
        has_evidence = bool(state.get("evidence"))
        sufficiency = {
            "sufficient": has_evidence,
            "confidence": 0.5 if has_evidence else 0.0,
            "covered": [],
            "missing_pieces": [],
            "reason": "Không parse được JSON từ LLM.",
            "next_corpora": [],
            "rewrite_hint": "",
        }

    status = "✅ SUFFICIENT" if sufficiency["sufficient"] else "❌ INSUFFICIENT"
    style = "green" if sufficiency["sufficient"] else "red"
    console.print(Panel(
        f"[bold {style}]{status}[/bold {style}]\n"
        f"Confidence: {sufficiency['confidence']}\n"
        f"Covered: {', '.join(sufficiency['covered']) or '—'}\n"
        f"Missing: {', '.join(sufficiency['missing_pieces']) or '—'}\n"
        f"Reason: {sufficiency['reason']}\n"
        f"Next corpora: {', '.join(sufficiency['next_corpora']) or '—'}",
        border_style=style,
        padding=(0, 1),
    ))
    console.print(f"  ⏱️  {elapsed}s")

    return {"sufficiency": sufficiency}


def answer_node(state: GeminiRAGState) -> GeminiRAGState:
    """Generate final answer from sufficient evidence."""
    console.print()
    console.print(Rule("🧾 ANSWER — Tổng hợp có citation", style="bold green"))

    start = time.time()
    llm = _create_llm(temperature=0.2)

    evidence_text = _format_evidence_short(state.get("evidence", []))
    hop_history = json.dumps(state.get("hop_history", []), ensure_ascii=False)

    prompt = ANSWER_PROMPT.format(
        question=state["question"],
        evidence=evidence_text,
        hop_history=hop_history,
    )
    response = _invoke_llm(llm, prompt)
    elapsed = round(time.time() - start, 2)
    answer = response.content.strip()

    console.print(Panel(
        answer,
        title="[bold green]Final Answer[/bold green]",
        border_style="green",
        padding=(1, 2),
    ))
    console.print(f"  ⏱️  {elapsed}s")

    return {"answer": answer}


def fallback_node(state: GeminiRAGState) -> GeminiRAGState:
    """Generate partial answer when hop budget is exhausted."""
    console.print()
    console.print(Rule("🧯 FALLBACK — Hết budget, trả lời một phần", style="bold red"))

    start = time.time()
    llm = _create_llm(temperature=0.2)

    missing = state.get("sufficiency", {}).get("missing_pieces", [])
    prompt = FALLBACK_PROMPT.format(
        max_hops=state.get("max_hops", MAX_HOPS),
        question=state["question"],
        evidence=_format_evidence_short(state.get("evidence", [])),
        missing_pieces=", ".join(missing) if missing else "Không xác định",
    )
    response = _invoke_llm(llm, prompt)
    elapsed = round(time.time() - start, 2)
    answer = response.content.strip()

    console.print(Panel(
        answer,
        title="[bold red]Fallback Answer[/bold red]",
        border_style="red",
        padding=(1, 2),
    ))
    console.print(f"  ⏱️  {elapsed}s")

    return {"answer": answer}


# ═══════════════════════════════════════════════════════════════════════
# ROUTING
# ═══════════════════════════════════════════════════════════════════════

def route_after_sufficiency(state: GeminiRAGState) -> Literal["answer", "planning_agent", "fallback"]:
    """Route based on sufficiency check and hop budget."""
    sufficiency = state.get("sufficiency", {})
    hop = state.get("hop", 0)
    max_hops = state.get("max_hops", MAX_HOPS)

    if sufficiency.get("sufficient"):
        return "answer"

    if hop >= max_hops:
        return "fallback"

    return "planning_agent"


# ═══════════════════════════════════════════════════════════════════════
# GRAPH BUILDER
# ═══════════════════════════════════════════════════════════════════════

def build_gemini_rag_graph():
    """Build the 5-agent LangGraph workflow."""
    workflow = StateGraph(GeminiRAGState)

    # Add nodes
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("planning_agent", planning_agent_node)
    workflow.add_node("query_rewriter", query_rewriter_node)
    workflow.add_node("search_fanout", search_fanout_node)
    workflow.add_node("sufficient_context", sufficient_context_node)
    workflow.add_node("answer", answer_node)
    workflow.add_node("fallback", fallback_node)

    # Edges
    workflow.add_edge(START, "orchestrator")
    workflow.add_edge("orchestrator", "planning_agent")
    workflow.add_edge("planning_agent", "query_rewriter")
    workflow.add_edge("query_rewriter", "search_fanout")
    workflow.add_edge("search_fanout", "sufficient_context")

    # Conditional: sufficient → answer, insufficient → loop or fallback
    workflow.add_conditional_edges(
        "sufficient_context",
        route_after_sufficiency,
        {
            "answer": "answer",
            "planning_agent": "planning_agent",
            "fallback": "fallback",
        },
    )

    workflow.add_edge("answer", END)
    workflow.add_edge("fallback", END)

    return workflow.compile()


def create_initial_state(question: str) -> GeminiRAGState:
    return {
        "question": question,
        "complexity": "",
        "orchestrator_reason": "",
        "plan": {},
        "sub_queries": [],
        "evidence": [],
        "sufficiency": {},
        "hop": 0,
        "max_hops": MAX_HOPS,
        "hop_history": [],
        "answer": "",
    }


def run_question_state(question: str, show_question: bool = True) -> GeminiRAGState:
    """Run the 5-agent graph and return the final state."""
    if show_question:
        console.print()
        console.print(Panel.fit(
            f"[bold white]{question}[/bold white]",
            title="[bold cyan]USER QUESTION[/bold cyan]",
            border_style="cyan",
            padding=(0, 2),
        ))

    graph = build_gemini_rag_graph()
    return graph.invoke(create_initial_state(question))


def run_question(question: str) -> str:
    result = run_question_state(question, show_question=True)
    return result["answer"]
