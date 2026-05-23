"""
═══════════════════════════════════════════════════════════════════════════════
AGENTIC RAG — Retrieval agent có vòng lặp tự kiểm tra chứng cứ
═══════════════════════════════════════════════════════════════════════════════

Design Pattern: AGENTIC RAG
───────────────────────────
RAG thường: User question → retrieve 1 lần → generate answer.

Agentic RAG thêm quyền tự điều phối:
  1. PLAN QUERY     — chuyển câu hỏi thành truy vấn tìm kiếm tốt hơn
  2. RETRIEVE       — gọi retrieval tool trên knowledge base
  3. GRADE          — tự đánh giá chứng cứ đã đủ chưa
  4. REWRITE        — nếu thiếu, viết lại query và tìm tiếp
  5. ANSWER         — trả lời có citation, chỉ dựa trên evidence

Flow:
  ┌──────────┐   ┌────────────┐   ┌──────────┐   ┌────────────┐
  │ Question │──▶│ Plan Query │──▶│ Retrieve │──▶│ Grade Docs │
  └──────────┘   └────────────┘   └──────────┘   └─────┬──────┘
                                                        │
                              enough evidence? ┌───────┴───────┐
                                                ▼               ▼
                                          ┌──────────┐   ┌──────────┐
                                          │  Answer  │◀──│ Rewrite  │
                                          └──────────┘   └──────────┘
"""

from __future__ import annotations

import json
import time
from typing import Literal

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

from agentic_rag.observability import build_langfuse_config, flush_langfuse
from agentic_rag.retriever import SearchResult, knowledge_base
from agentic_rag.schemas import AgenticRAGState, Evidence
from agentic_rag.settings import (
    MAX_RETRIEVAL_ROUNDS,
    OPENAI_API_BASE,
    OPENAI_API_KEY,
    OPENAI_MODEL_NAME,
)

console = Console()


def create_llm(temperature: float = 0) -> ChatOpenAI:
    return ChatOpenAI(
        model=OPENAI_MODEL_NAME,
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_API_BASE,
        temperature=temperature,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )


QUERY_PLANNER_PROMPT = """Bạn là query planner cho một hệ thống Agentic RAG.

Câu hỏi của user:
{question}

Hãy tạo truy vấn retrieval ngắn gọn để tìm tài liệu chính sách liên quan.
Trả về JSON chính xác, không thêm text ngoài:

{{
  "intent": "ý định cần trả lời",
  "query": "truy vấn tìm kiếm tốt nhất",
  "must_find": ["điểm chứng cứ cần tìm 1", "điểm chứng cứ cần tìm 2"]
}}
"""

JUDGE_PROMPT = """Bạn là Retrieval Judge trong Agentic RAG.

Câu hỏi gốc:
{question}

Truy vấn vừa dùng:
{query}

Evidence hiện có:
{evidence}

Nhiệm vụ:
- Đánh giá evidence đã đủ để trả lời câu hỏi chưa.
- Nếu chưa đủ, viết lại query cụ thể hơn cho vòng retrieve tiếp theo.
- Không yêu cầu thông tin ngoài knowledge base.

Trả về JSON chính xác, không thêm text ngoài:

{{
  "sufficient": true,
  "reason": "lý do ngắn",
  "missing": ["điểm còn thiếu"],
  "rewrite_query": "query mới nếu chưa đủ, hoặc chuỗi rỗng nếu đã đủ"
}}
"""

ANSWER_PROMPT = """Bạn là trợ lý ngân hàng nội bộ dùng Agentic RAG.

Chỉ được dùng evidence dưới đây để trả lời. Nếu evidence không đủ,
nói rõ phần nào chưa có trong knowledge base. Không bịa chính sách.

Câu hỏi:
{question}

Evidence:
{evidence}

Search history:
{history}

Yêu cầu output:
- Trả lời bằng tiếng Việt.
- Nêu kết luận trực tiếp trước.
- Mỗi ý chính cần citation dạng [KB-xxx].
- Nếu có nhiều bước xử lý, trình bày theo checklist ngắn.
"""


def _extract_json(raw: str) -> dict:
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


def _format_evidence(evidence: list[Evidence], include_content: bool = False) -> str:
    if not evidence:
        return "Chưa có evidence."

    blocks: list[str] = []
    for item in evidence:
        body = item["content"] if include_content else item["snippet"]
        blocks.append(
            f"[{item['source_id']}] {item['title']}\n"
            f"Source: {item['source']} | Score: {item['score']}\n"
            f"{body}"
        )
    return "\n\n---\n\n".join(blocks)


def _merge_evidence(existing: list[Evidence], results: list[SearchResult]) -> list[Evidence]:
    by_id = {item["source_id"]: item for item in existing}

    for result in results:
        doc = result.document
        current = by_id.get(doc.id)
        next_item: Evidence = {
            "source_id": doc.id,
            "title": doc.title,
            "source": doc.source,
            "score": result.score,
            "snippet": result.snippet,
            "content": doc.content,
        }
        if current is None or result.score > current["score"]:
            by_id[doc.id] = next_item

    return sorted(by_id.values(), key=lambda item: item["score"], reverse=True)


def plan_query_node(state: AgenticRAGState) -> AgenticRAGState:
    console.print()
    console.print(Rule("🧭 PLAN QUERY — Tối ưu truy vấn retrieval", style="bold yellow"))

    start = time.time()
    llm = create_llm(temperature=0)
    prompt = QUERY_PLANNER_PROMPT.format(question=state["question"])
    response = llm.invoke([HumanMessage(content=prompt)])
    elapsed = round(time.time() - start, 2)

    try:
        parsed = _extract_json(response.content)
        query = parsed.get("query") or state["question"]
        intent = parsed.get("intent", "Không rõ")
        must_find = parsed.get("must_find", [])
    except (json.JSONDecodeError, TypeError, AttributeError):
        query = state["question"]
        intent = "Fallback: dùng nguyên câu hỏi"
        must_find = []

    console.print(f"  Intent: [yellow]{intent}[/yellow]")
    console.print(f"  Query:  [cyan]{query}[/cyan]")
    if must_find:
        console.print(f"  Need:   [dim]{'; '.join(must_find)}[/dim]")
    console.print(f"  ⏱️  {elapsed}s")

    return {
        "current_query": query,
        "search_history": [],
        "evidence": [],
        "rounds": 0,
        "judge": {},
        "answer": "",
    }


def retrieve_node(state: AgenticRAGState) -> AgenticRAGState:
    query = state["current_query"]
    round_no = state["rounds"] + 1

    console.print()
    console.print(Rule(f"🔎 RETRIEVE — Vòng {round_no}/{MAX_RETRIEVAL_ROUNDS}", style="bold blue"))
    console.print(f"  Query: [cyan]{query}[/cyan]")

    start = time.time()
    results = knowledge_base.search(query, top_k=4)
    elapsed = round(time.time() - start, 2)

    table = Table(title="Retrieved Documents", border_style="blue", show_lines=True)
    table.add_column("Source", style="bold cyan", width=10)
    table.add_column("Score", justify="right", width=7)
    table.add_column("Title", width=28)
    table.add_column("Snippet", style="dim", width=62)

    for result in results:
        doc = result.document
        table.add_row(doc.id, str(result.score), doc.title, result.snippet)

    if results:
        console.print(table)
    else:
        console.print("[yellow]Không tìm thấy tài liệu phù hợp.[/yellow]")
    console.print(f"  ⏱️  {elapsed}s | {len(results)} docs")

    return {
        "rounds": round_no,
        "search_history": [*state["search_history"], query],
        "evidence": _merge_evidence(state["evidence"], results),
    }


def grade_evidence_node(state: AgenticRAGState) -> AgenticRAGState:
    console.print()
    console.print(Rule("🧪 GRADE — Kiểm tra evidence đã đủ chưa", style="bold magenta"))

    start = time.time()
    llm = create_llm(temperature=0)
    prompt = JUDGE_PROMPT.format(
        question=state["question"],
        query=state["current_query"],
        evidence=_format_evidence(state["evidence"], include_content=False),
    )
    response = llm.invoke([HumanMessage(content=prompt)])
    elapsed = round(time.time() - start, 2)

    try:
        judge = _extract_json(response.content)
        judge["sufficient"] = bool(judge.get("sufficient", False))
        judge.setdefault("reason", "")
        judge.setdefault("missing", [])
        judge.setdefault("rewrite_query", "")
    except (json.JSONDecodeError, TypeError, AttributeError):
        judge = {
            "sufficient": bool(state["evidence"]),
            "reason": "Fallback judge: không parse được JSON từ LLM.",
            "missing": [],
            "rewrite_query": state["question"],
        }

    status = "ĐỦ" if judge["sufficient"] else "CHƯA ĐỦ"
    style = "green" if judge["sufficient"] else "yellow"
    console.print(Panel(
        f"[bold {style}]{status}[/bold {style}]\n"
        f"Reason: {judge.get('reason', '')}\n"
        f"Missing: {', '.join(judge.get('missing', [])) or '—'}\n"
        f"Rewrite: {judge.get('rewrite_query', '') or '—'}",
        border_style=style,
        padding=(0, 1),
    ))
    console.print(f"  ⏱️  {elapsed}s")

    return {"judge": judge}


def rewrite_query_node(state: AgenticRAGState) -> AgenticRAGState:
    judge = state["judge"]
    missing = " ".join(judge.get("missing", []))
    rewritten = judge.get("rewrite_query") or f"{state['question']} {missing}".strip()

    console.print()
    console.print(Rule("✍️ REWRITE — Tạo query mới", style="bold yellow"))
    console.print(f"  Next query: [cyan]{rewritten}[/cyan]")

    return {"current_query": rewritten}


def answer_node(state: AgenticRAGState) -> AgenticRAGState:
    console.print()
    console.print(Rule("🧾 ANSWER — Tổng hợp có citation", style="bold green"))

    start = time.time()
    llm = create_llm(temperature=0.2)
    prompt = ANSWER_PROMPT.format(
        question=state["question"],
        evidence=_format_evidence(state["evidence"], include_content=True),
        history=" → ".join(state["search_history"]) or "Chưa có",
    )
    response = llm.invoke([HumanMessage(content=prompt)])
    elapsed = round(time.time() - start, 2)
    answer = response.content.strip()

    console.print(Panel(
        Markdown(answer),
        title="[bold green]Final Answer[/bold green]",
        border_style="green",
        padding=(1, 2),
    ))
    console.print(f"  ⏱️  {elapsed}s")

    return {"answer": answer}


def route_after_grade(state: AgenticRAGState) -> Literal["answer", "rewrite"]:
    if state["judge"].get("sufficient"):
        return "answer"
    if state["rounds"] >= MAX_RETRIEVAL_ROUNDS:
        return "answer"
    return "rewrite"


def build_agentic_rag_graph():
    workflow = StateGraph(AgenticRAGState)
    workflow.add_node("plan_query", plan_query_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("grade_evidence", grade_evidence_node)
    workflow.add_node("rewrite_query", rewrite_query_node)
    workflow.add_node("answer", answer_node)

    workflow.add_edge(START, "plan_query")
    workflow.add_edge("plan_query", "retrieve")
    workflow.add_edge("retrieve", "grade_evidence")
    workflow.add_conditional_edges(
        "grade_evidence",
        route_after_grade,
        {
            "answer": "answer",
            "rewrite": "rewrite_query",
        },
    )
    workflow.add_edge("rewrite_query", "retrieve")
    workflow.add_edge("answer", END)

    return workflow.compile()


def create_initial_state(question: str) -> AgenticRAGState:
    return {
        "question": question,
        "current_query": "",
        "search_history": [],
        "evidence": [],
        "rounds": 0,
        "judge": {},
        "answer": "",
    }


def run_question_state(
    question: str,
    show_question: bool = False,
    session_id: str | None = None,
) -> AgenticRAGState:
    """Run the Agentic RAG graph and return the final state.

    Streamlit uses this richer result to show search history, judge output,
    retrieved evidence, and the final answer in the chat UI.
    """
    if show_question:
        console.print()
        console.print(Panel.fit(
            f"[bold white]{question}[/bold white]",
            title="[bold cyan]USER QUESTION[/bold cyan]",
            border_style="cyan",
            padding=(0, 2),
        ))

    graph = build_agentic_rag_graph()
    config = build_langfuse_config(question, session_id=session_id)
    try:
        return graph.invoke(create_initial_state(question), config=config)
    finally:
        flush_langfuse()


def run_question(question: str) -> str:
    result = run_question_state(question, show_question=True)
    return result["answer"]
