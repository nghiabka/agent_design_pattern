"""
Agentic RAG graph with controllable routing, evidence grading, and guardrails.

The demo follows the workflow in `new_workflow_diagram.md` in a pragmatic way:
input guard -> intent router -> reasoner contract -> schema validation ->
multi-query retrieval -> CRAG-style grading -> context control -> loop budget ->
evidence-bound answer -> output guard.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any, Literal

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

from agentic_rag.observability import build_langfuse_config, flush_langfuse
from agentic_rag.retriever import SearchResult, knowledge_base
from agentic_rag.schemas import (
    AgenticRAGState,
    Evidence,
    ReasonerContract,
    RetrievalJudgeDecision,
)
from agentic_rag.settings import (
    MAX_RETRIEVAL_ROUNDS,
    OPENAI_API_BASE,
    OPENAI_API_KEY,
    OPENAI_MODEL_NAME,
)

console = Console()

MAX_CONTEXT_EVIDENCE = 5
CITATION_RE = re.compile(r"\[(KB-\d{3})\]")


def create_llm(temperature: float = 0) -> ChatOpenAI:
    return ChatOpenAI(
        model=OPENAI_MODEL_NAME,
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_API_BASE,
        temperature=temperature,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )


INTENT_ROUTER_PROMPT = """Bạn là intent router cho chatbot Agentic RAG của FinFlow Bank.

Câu hỏi của user:
{question}

Phân loại thành một route:

- "chitchat": lời chào, cảm ơn, tạm biệt, small talk, hỏi chatbot là ai,
  hỏi khả năng chung, hoặc câu xã giao không cần knowledge base.
- "rag": câu hỏi về chính sách, quy trình, điều kiện, phí, hạn mức,
  sản phẩm, khiếu nại, chuyển tuyến, hoặc cần căn cứ từ knowledge base.
- "out_of_scope": câu hỏi không liên quan FinFlow Bank/policy/knowledge base.

Quy tắc:
- Nếu không chắc giữa "rag" và "out_of_scope", chọn "rag".
- Không tự trả lời chính sách ở bước này.

Trả về JSON chính xác, không thêm text ngoài:

{{
  "route": "rag",
  "intent": "ý định ngắn",
  "reason": "lý do ngắn"
}}
"""

REASONER_CONTRACT_PROMPT = """Bạn là Reasoner Core cho hệ thống Agentic RAG.

Không trả lời trực tiếp. Mỗi lần chỉ xuất một action contract dạng JSON để graph
kiểm soát retrieval, retry và audit.

Câu hỏi user đã che PII:
{question}

Search history:
{history}

Evidence hiện có:
{evidence}

Failure reflection notes từ vòng trước:
{failure_notes}

Nhiệm vụ:
- Chuẩn hóa intent thành một truy vấn chính.
- Tách câu hỏi phức tạp thành 2-4 retrieval queries đa dạng, ưu tiên tiếng Việt
  và keyword xuất hiện trong policy.
- Liệt kê required_evidence: các thông tin bắt buộc phải có trước khi trả lời.
- Nếu câu hỏi quá mơ hồ, action = "clarify".
- Nếu không có hướng retrieval hợp lý sau các failure notes, action = "fallback".
- Nếu evidence hiện có đã đủ, action = "finalize".
- Demo này chưa có side-effect tools, không dùng action "use_tool".

Trả về JSON chính xác, không thêm text ngoài:

{{
  "action": "retrieve",
  "rewritten_query": "truy vấn chính đã chuẩn hóa",
  "retrieval_queries": [
    "query cụ thể 1",
    "query cụ thể 2"
  ],
  "plan": ["bước cần thực hiện"],
  "required_evidence": ["thông tin bắt buộc cần tìm"],
  "confidence": 0.8,
  "stop_reason": ""
}}
"""

JUDGE_PROMPT = """Bạn là Retrieval Grader trong Agentic RAG theo phong cách CRAG.

Câu hỏi gốc:
{question}

Required evidence:
{required_evidence}

Retrieval queries vừa dùng:
{queries}

Evidence hiện có:
{evidence}

Nhiệm vụ:
- Chấm relevance: evidence có liên quan trực tiếp câu hỏi không.
- Chấm coverage: required_evidence đã được bao phủ chưa.
- Chấm source_quality: nguồn có đủ cụ thể để citation không.
- Chỉ sufficient=true khi có thể trả lời an toàn chỉ từ evidence.
- Nếu thiếu, viết 1-3 rewrite_queries cụ thể cho vòng sau.
- Không yêu cầu thông tin ngoài knowledge base.

Trả về JSON chính xác, không thêm text ngoài:

{{
  "sufficient": true,
  "coverage_score": 0.9,
  "relevance_score": 0.9,
  "source_quality_score": 0.9,
  "reason": "lý do ngắn",
  "covered": ["điểm đã có chứng cứ"],
  "missing": ["điểm còn thiếu"],
  "accepted_source_ids": ["KB-003"],
  "rewrite_queries": ["query mới nếu chưa đủ"],
  "rewrite_query": "query mới đầu tiên để tương thích trace cũ",
  "reflection_note": "hướng dẫn retry ngắn, không chứa chain-of-thought"
}}
"""

DIRECT_ANSWER_PROMPT = """Bạn là trợ lý Agentic RAG.

User đang chit-chat hoặc hỏi thông tin chung, không cần tra cứu knowledge base.

Câu hỏi:
{question}

Hãy trả lời ngắn gọn, thân thiện bằng tiếng Việt.
Không dùng citation [KB-xxx].
Không dùng emoji.
Nếu user hỏi bạn có thể làm gì, nói rằng bạn có thể trả lời các câu hỏi về
policy trong knowledge base và hiển thị trace retrieval khi cần.
"""

ANSWER_PROMPT = """Bạn là trợ lý ngân hàng nội bộ dùng Agentic RAG.

Chỉ được dùng evidence dưới đây để trả lời. Nếu evidence không đủ,
nói rõ phần nào chưa có trong knowledge base. Không bịa chính sách.

Câu hỏi:
{question}

Required evidence:
{required_evidence}

Judge:
{judge}

Evidence:
{evidence}

Search history:
{history}

Yêu cầu output:
- Trả lời bằng tiếng Việt.
- Nêu kết luận trực tiếp trước.
- Mỗi ý chính cần citation dạng [KB-xxx] từ evidence.
- Nếu có nhiều bước xử lý, trình bày theo checklist ngắn.
- Không dùng citation không xuất hiện trong evidence.
"""


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


def _model_dump(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]


def _dedupe_texts(items: list[str], limit: int | None = None) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        normalized = re.sub(r"\s+", " ", item).strip()
        key = normalized.casefold()
        if not normalized or key in seen:
            continue
        seen.add(key)
        deduped.append(normalized)
        if limit and len(deduped) >= limit:
            break
    return deduped


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


def _mask_sensitive_text(text: str) -> tuple[str, dict[str, str]]:
    masks: dict[str, str] = {}
    protected = text

    patterns = [
        ("EMAIL", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)),
        ("CARD", re.compile(r"\b(?:\d[ -]?){13,19}\b")),
        ("PHONE", re.compile(r"\b(?:\+?84|0)(?:[\s.-]?\d){8,10}\b")),
    ]

    for label, pattern in patterns:
        def replace(match: re.Match[str], label: str = label) -> str:
            token = f"<{label}_{len(masks) + 1}>"
            masks[token] = match.group(0)
            return token

        protected = pattern.sub(replace, protected)

    return protected, masks


def _build_grounded_fallback(state: AgenticRAGState, reason: str) -> str:
    missing = state.get("judge", {}).get("missing") or []
    if missing:
        missing_text = " Các phần còn thiếu: " + "; ".join(missing) + "."
    else:
        missing_text = ""

    source_ids = [item["source_id"] for item in state.get("evidence", [])]
    source_text = ""
    if source_ids:
        source_text = " Evidence hiện có: " + ", ".join(f"[{source_id}]" for source_id in source_ids) + "."

    return (
        "Mình chưa thể tạo câu trả lời đủ chắc từ knowledge base hiện tại. "
        f"Lý do: {reason}.{missing_text}{source_text}"
    )


def input_guard_node(state: AgenticRAGState) -> AgenticRAGState:
    console.print()
    console.print(Rule("🛡️ INPUT GUARD — Kiểm tra an toàn đầu vào", style="bold magenta"))

    question = state["question"].strip()
    protected_question, masks = _mask_sensitive_text(question)

    blocked_patterns = [
        r"\b(ignore|bypass|override)\b.*\b(system|developer|instruction|prompt)\b",
        r"bỏ qua.*(hướng dẫn|quy tắc|system|developer|prompt)",
        r"tiết lộ.*(system prompt|developer message|prompt hệ thống)",
        r"\bjailbreak\b",
    ]
    matched = [
        pattern
        for pattern in blocked_patterns
        if re.search(pattern, question, flags=re.IGNORECASE)
    ]

    if matched:
        guardrail = {
            "status": "blocked",
            "category": "prompt_injection",
            "reason": "Yêu cầu có dấu hiệu cố gắng bỏ qua hoặc tiết lộ hướng dẫn hệ thống.",
            "matched_patterns": matched,
        }
        style = "red"
    else:
        guardrail = {
            "status": "pass",
            "category": "normal",
            "reason": "Input hợp lệ.",
            "pii_masked": bool(masks),
        }
        style = "green"

    console.print(Panel(
        f"Status: [bold {style}]{guardrail['status']}[/bold {style}]\n"
        f"Reason: {guardrail['reason']}\n"
        f"PII masked: {bool(masks)}",
        border_style=style,
        padding=(0, 1),
    ))

    return {
        "protected_question": protected_question,
        "pii_masks": masks,
        "guardrail": guardrail,
    }


def safe_decline_node(state: AgenticRAGState) -> AgenticRAGState:
    reason = state.get("guardrail", {}).get("reason", "Input không đạt guardrail.")
    answer = (
        "Mình không thể hỗ trợ yêu cầu này vì nó có dấu hiệu vi phạm guardrail. "
        "Bạn có thể hỏi lại bằng một câu hỏi nghiệp vụ hoặc policy cụ thể."
    )
    return {
        "answer": answer,
        "intent_route": "blocked",
        "judge": {"sufficient": False, "reason": reason, "missing": []},
        "output_guard": {"status": "pass", "reason": "Blocked by input guardrail."},
    }


def intent_router_node(state: AgenticRAGState) -> AgenticRAGState:
    console.print()
    console.print(Rule("🚦 INTENT ROUTER — Chọn strategy", style="bold cyan"))

    start = time.time()
    llm = create_llm(temperature=0)
    question = state.get("protected_question") or state["question"]
    prompt = INTENT_ROUTER_PROMPT.format(question=question)
    response = llm.invoke([HumanMessage(content=prompt)])
    elapsed = round(time.time() - start, 2)

    try:
        parsed = _extract_json(response.content)
        route = str(parsed.get("route", "rag")).lower().strip()
        if route not in {"chitchat", "rag", "out_of_scope"}:
            route = "rag"
        intent = {
            "route": route,
            "intent": parsed.get("intent", ""),
            "reason": parsed.get("reason", ""),
        }
    except (json.JSONDecodeError, TypeError, AttributeError):
        route = "rag"
        intent = {
            "route": route,
            "intent": "fallback",
            "reason": "Không parse được JSON router, mặc định chạy RAG.",
        }

    style = {
        "chitchat": "green",
        "rag": "blue",
        "out_of_scope": "yellow",
    }[route]
    console.print(Panel(
        f"Route: [bold {style}]{route}[/bold {style}]\n"
        f"Intent: {intent.get('intent') or '—'}\n"
        f"Reason: {intent.get('reason') or '—'}",
        border_style=style,
        padding=(0, 1),
    ))
    console.print(f"  ⏱️  {elapsed}s")

    return {"intent_route": route, "intent": intent}


def direct_answer_node(state: AgenticRAGState) -> AgenticRAGState:
    console.print()
    console.print(Rule("💬 DIRECT ANSWER — Chit-chat không retrieve", style="bold green"))

    start = time.time()
    llm = create_llm(temperature=0.3)
    prompt = DIRECT_ANSWER_PROMPT.format(question=state["question"])
    response = llm.invoke([HumanMessage(content=prompt)])
    elapsed = round(time.time() - start, 2)
    answer = response.content.strip()

    console.print(Panel(
        Markdown(answer),
        title="[bold green]Direct Answer[/bold green]",
        border_style="green",
        padding=(1, 2),
    ))
    console.print(f"  ⏱️  {elapsed}s")

    return {
        "answer": answer,
        "current_query": "",
        "retrieval_queries": [],
        "search_history": [],
        "evidence": [],
        "rounds": 0,
        "judge": {
            "sufficient": True,
            "reason": "Chit-chat routed to direct answer.",
            "missing": [],
            "rewrite_query": "",
        },
    }


def decline_node(state: AgenticRAGState) -> AgenticRAGState:
    console.print()
    console.print(Rule("↩️ DECLINE ROUTER — Ngoài phạm vi KB", style="bold yellow"))

    answer = (
        "Mình chỉ hỗ trợ các câu hỏi liên quan đến policy, quy trình và sản phẩm "
        "trong knowledge base FinFlow Bank. Bạn hãy hỏi lại bằng một câu hỏi thuộc phạm vi này."
    )
    console.print(Panel(answer, border_style="yellow", padding=(0, 1)))
    return {
        "answer": answer,
        "judge": {
            "sufficient": False,
            "reason": "Out-of-scope routed to decline.",
            "missing": [],
            "rewrite_query": "",
        },
    }


def _normalize_reasoner_contract(
    payload: dict[str, Any],
    state: AgenticRAGState,
) -> dict[str, Any]:
    payload = dict(payload or {})
    allowed_actions = {"retrieve", "clarify", "finalize", "fallback"}
    action = str(payload.get("action") or "retrieve").lower().strip()
    if action not in allowed_actions:
        action = "retrieve"
    payload["action"] = action

    question = state.get("protected_question") or state["question"]
    rewritten = str(
        payload.get("rewritten_query")
        or payload.get("query")
        or state.get("current_query")
        or question
    ).strip()
    payload["rewritten_query"] = rewritten

    required_evidence = _as_list(
        payload.get("required_evidence")
        or payload.get("must_find")
        or state.get("required_evidence")
    )
    payload["required_evidence"] = required_evidence

    raw_queries = _as_list(payload.get("retrieval_queries"))
    if action == "retrieve":
        raw_queries = [*raw_queries, rewritten, question]
    elif not raw_queries and rewritten:
        raw_queries = [rewritten]
    payload["retrieval_queries"] = _dedupe_texts(raw_queries, limit=4)

    payload["plan"] = _as_list(payload.get("plan"))
    payload["stop_reason"] = str(payload.get("stop_reason") or "").strip()

    try:
        contract = ReasonerContract.model_validate(payload)
    except ValidationError:
        contract = ReasonerContract(
            action="retrieve",
            rewritten_query=question,
            retrieval_queries=[question],
            plan=["Fallback: dùng nguyên câu hỏi để retrieve."],
            required_evidence=required_evidence,
            confidence=0.0,
            stop_reason="schema_validation_failed",
        )

    contract_dict = _model_dump(contract)
    if contract_dict["action"] == "retrieve" and not contract_dict["retrieval_queries"]:
        contract_dict["retrieval_queries"] = [question]
    return contract_dict


def reasoner_core_node(state: AgenticRAGState) -> AgenticRAGState:
    console.print()
    console.print(Rule("🧠 REASONER CORE — Rewrite, plan, action contract", style="bold yellow"))

    start = time.time()
    llm = create_llm(temperature=0)
    question = state.get("protected_question") or state["question"]
    prompt = REASONER_CONTRACT_PROMPT.format(
        question=question,
        history=" → ".join(state.get("search_history", [])) or "Chưa có",
        evidence=_format_evidence(state.get("evidence", []), include_content=False),
        failure_notes="\n".join(state.get("failure_notes", [])) or "Chưa có",
    )
    response = llm.invoke([HumanMessage(content=prompt)])
    elapsed = round(time.time() - start, 2)

    try:
        raw_contract = _extract_json(response.content)
    except (json.JSONDecodeError, TypeError, AttributeError):
        raw_contract = {
            "action": "retrieve",
            "rewritten_query": question,
            "retrieval_queries": [question],
            "plan": ["Fallback: không parse được JSON từ Reasoner Core."],
            "required_evidence": state.get("required_evidence", []),
            "confidence": 0.0,
            "stop_reason": "json_parse_failed",
        }

    console.print(Panel(
        json.dumps(raw_contract, ensure_ascii=False, indent=2),
        title="[bold yellow]Raw Contract[/bold yellow]",
        border_style="yellow",
        padding=(0, 1),
    ))
    console.print(f"  ⏱️  {elapsed}s")
    return {"reasoner": raw_contract}


def action_validator_node(state: AgenticRAGState) -> AgenticRAGState:
    console.print()
    console.print(Rule("✅ ACTION VALIDATOR — Strict schema", style="bold cyan"))

    contract = _normalize_reasoner_contract(state.get("reasoner", {}), state)
    current_query = contract["retrieval_queries"][0] if contract["retrieval_queries"] else contract["rewritten_query"]

    console.print(Panel(
        f"Action: [bold cyan]{contract['action']}[/bold cyan]\n"
        f"Confidence: {contract['confidence']}\n"
        f"Current query: {current_query}\n"
        f"Required evidence: {'; '.join(contract['required_evidence']) or '—'}",
        border_style="cyan",
        padding=(0, 1),
    ))

    return {
        "reasoner": contract,
        "current_query": current_query,
        "retrieval_queries": contract["retrieval_queries"],
        "required_evidence": contract["required_evidence"],
    }


def retrieve_node(state: AgenticRAGState) -> AgenticRAGState:
    queries = state.get("retrieval_queries") or [state["current_query"]]
    queries = _dedupe_texts(queries, limit=4)
    round_no = state["rounds"] + 1

    console.print()
    console.print(Rule(f"🔎 RETRIEVE — Vòng {round_no}/{MAX_RETRIEVAL_ROUNDS}", style="bold blue"))

    start = time.time()
    all_results: list[SearchResult] = []
    for query in queries:
        console.print(f"  Query: [cyan]{query}[/cyan]")
        all_results.extend(knowledge_base.search(query, top_k=4))
    elapsed = round(time.time() - start, 2)

    merged_for_table = _merge_evidence([], all_results)
    table = Table(title="Retrieved Documents", border_style="blue", show_lines=True)
    table.add_column("Source", style="bold cyan", width=10)
    table.add_column("Score", justify="right", width=7)
    table.add_column("Title", width=28)
    table.add_column("Snippet", style="dim", width=62)

    for item in merged_for_table:
        table.add_row(item["source_id"], str(item["score"]), item["title"], item["snippet"])

    if merged_for_table:
        console.print(table)
    else:
        console.print("[yellow]Không tìm thấy tài liệu phù hợp.[/yellow]")
    console.print(f"  ⏱️  {elapsed}s | {len(merged_for_table)} unique docs")

    history = _dedupe_texts([*state.get("search_history", []), *queries])
    return {
        "rounds": round_no,
        "search_history": history,
        "evidence": _merge_evidence(state.get("evidence", []), all_results),
    }


def grade_evidence_node(state: AgenticRAGState) -> AgenticRAGState:
    console.print()
    console.print(Rule("🧪 RETRIEVAL GRADER — CRAG evidence quality", style="bold magenta"))

    start = time.time()
    llm = create_llm(temperature=0)
    prompt = JUDGE_PROMPT.format(
        question=state["question"],
        required_evidence="\n".join(state.get("required_evidence", [])) or "Không rõ",
        queries="\n".join(state.get("retrieval_queries", [])) or state.get("current_query", ""),
        evidence=_format_evidence(state.get("evidence", []), include_content=False),
    )
    response = llm.invoke([HumanMessage(content=prompt)])
    elapsed = round(time.time() - start, 2)

    try:
        parsed = _extract_json(response.content)
        if parsed.get("rewrite_query") and not parsed.get("rewrite_queries"):
            parsed["rewrite_queries"] = [parsed["rewrite_query"]]
        decision = RetrievalJudgeDecision.model_validate(parsed)
        judge = _model_dump(decision)
    except (json.JSONDecodeError, TypeError, AttributeError, ValidationError):
        has_evidence = bool(state.get("evidence"))
        rewrite_query = " ".join([state["question"], *state.get("required_evidence", [])]).strip()
        judge = _model_dump(RetrievalJudgeDecision(
            sufficient=has_evidence,
            coverage_score=0.5 if has_evidence else 0.0,
            relevance_score=0.5 if has_evidence else 0.0,
            source_quality_score=0.5 if has_evidence else 0.0,
            reason="Fallback judge: không parse được JSON từ LLM.",
            missing=[] if has_evidence else state.get("required_evidence", []),
            accepted_source_ids=[item["source_id"] for item in state.get("evidence", [])[:3]],
            rewrite_queries=[rewrite_query] if rewrite_query else [],
            rewrite_query=rewrite_query,
            reflection_note="Retry bằng câu hỏi gốc kết hợp required evidence.",
        ))

    if judge.get("rewrite_queries") and not judge.get("rewrite_query"):
        judge["rewrite_query"] = judge["rewrite_queries"][0]

    status = "ĐỦ" if judge["sufficient"] else "CHƯA ĐỦ"
    style = "green" if judge["sufficient"] else "yellow"
    console.print(Panel(
        f"[bold {style}]{status}[/bold {style}]\n"
        f"Coverage: {judge.get('coverage_score')} | "
        f"Relevance: {judge.get('relevance_score')} | "
        f"Source: {judge.get('source_quality_score')}\n"
        f"Reason: {judge.get('reason', '')}\n"
        f"Missing: {', '.join(judge.get('missing', [])) or '—'}\n"
        f"Rewrite: {'; '.join(judge.get('rewrite_queries', [])) or '—'}",
        border_style=style,
        padding=(0, 1),
    ))
    console.print(f"  ⏱️  {elapsed}s")

    return {"judge": judge}


def context_control_node(state: AgenticRAGState) -> AgenticRAGState:
    console.print()
    console.print(Rule("🧹 CONTEXT CONTROL — Trim evidence + failure notes", style="bold blue"))

    evidence = state.get("evidence", [])
    judge = state.get("judge", {})
    accepted = set(judge.get("accepted_source_ids") or [])

    if accepted and judge.get("sufficient"):
        controlled_evidence = [
            item for item in evidence if item["source_id"] in accepted
        ][:MAX_CONTEXT_EVIDENCE]
    elif accepted:
        accepted_items = [item for item in evidence if item["source_id"] in accepted]
        remaining_items = [item for item in evidence if item["source_id"] not in accepted]
        controlled_evidence = [*accepted_items, *remaining_items][:MAX_CONTEXT_EVIDENCE]
    else:
        controlled_evidence = evidence[:MAX_CONTEXT_EVIDENCE]

    updates: dict[str, Any] = {"evidence": controlled_evidence}
    notes = list(state.get("failure_notes", []))

    if not judge.get("sufficient"):
        note = (
            judge.get("reflection_note")
            or judge.get("reason")
            or "Evidence chưa đủ, cần query cụ thể hơn."
        )
        if note and note not in notes:
            notes.append(str(note))
        updates["failure_notes"] = notes[-5:]

        rewrite_queries = _dedupe_texts(_as_list(judge.get("rewrite_queries") or judge.get("rewrite_query")), limit=4)
        if rewrite_queries:
            updates["retrieval_queries"] = rewrite_queries
            updates["current_query"] = rewrite_queries[0]

    console.print(
        f"  Kept evidence: [cyan]{len(controlled_evidence)}[/cyan] | "
        f"Failure notes: [yellow]{len(updates.get('failure_notes', notes))}[/yellow]"
    )
    return updates


def loop_budget_node(state: AgenticRAGState) -> AgenticRAGState:
    console.print()
    console.print(Rule("⏳ LOOP BUDGET — Kiểm tra retry budget", style="bold cyan"))

    sufficient = bool(state.get("judge", {}).get("sufficient"))
    rounds = state.get("rounds", 0)
    remaining = max(MAX_RETRIEVAL_ROUNDS - rounds, 0)
    exhausted = not sufficient and rounds >= MAX_RETRIEVAL_ROUNDS
    next_step = "answer" if sufficient else "fallback" if exhausted else "reasoner_core"

    budget = {
        "rounds": rounds,
        "max_rounds": MAX_RETRIEVAL_ROUNDS,
        "remaining_rounds": remaining,
        "exhausted": exhausted,
        "next": next_step,
    }
    console.print(Panel(
        f"Rounds: {rounds}/{MAX_RETRIEVAL_ROUNDS}\n"
        f"Remaining: {remaining}\n"
        f"Next: {next_step}",
        border_style="cyan",
        padding=(0, 1),
    ))
    return {"budget": budget}


def clarify_question_node(state: AgenticRAGState) -> AgenticRAGState:
    required = state.get("required_evidence") or ["thông tin cụ thể hơn về yêu cầu"]
    answer = (
        "Mình cần thêm thông tin để tra cứu đúng policy. "
        "Bạn hãy bổ sung: " + "; ".join(required[:3]) + "."
    )
    return {
        "answer": answer,
        "judge": {
            "sufficient": False,
            "reason": "Reasoner requested clarification.",
            "missing": required,
        },
    }


def fallback_node(state: AgenticRAGState) -> AgenticRAGState:
    console.print()
    console.print(Rule("🧯 FALLBACK — Không đủ evidence", style="bold red"))

    reason = state.get("judge", {}).get("reason") or state.get("reasoner", {}).get("stop_reason") or "Không đủ evidence."
    answer = _build_grounded_fallback(state, reason)
    console.print(Panel(answer, border_style="red", padding=(0, 1)))
    return {"answer": answer}


def answer_node(state: AgenticRAGState) -> AgenticRAGState:
    console.print()
    console.print(Rule("🧾 ANSWER — Tổng hợp có citation", style="bold green"))

    start = time.time()
    llm = create_llm(temperature=0.2)
    prompt = ANSWER_PROMPT.format(
        question=state["question"],
        required_evidence="\n".join(state.get("required_evidence", [])) or "Không rõ",
        judge=json.dumps(state.get("judge", {}), ensure_ascii=False),
        evidence=_format_evidence(state.get("evidence", []), include_content=True),
        history=" → ".join(state.get("search_history", [])) or "Chưa có",
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


def output_guard_node(state: AgenticRAGState) -> AgenticRAGState:
    console.print()
    console.print(Rule("🧷 OUTPUT GUARD — Groundedness/citation check", style="bold magenta"))

    if state.get("intent_route") != "rag" or not state.get("judge", {}).get("sufficient"):
        guard = {"status": "pass", "reason": "No grounded RAG answer required."}
        console.print(Panel("Pass", border_style="green", padding=(0, 1)))
        return {"output_guard": guard}

    answer = state.get("answer", "")
    citations = set(CITATION_RE.findall(answer))
    evidence_ids = {item["source_id"] for item in state.get("evidence", [])}
    invalid_citations = sorted(citations - evidence_ids)
    missing_citations = not citations and bool(evidence_ids)

    if invalid_citations or missing_citations:
        reason = "Citation không hợp lệ." if invalid_citations else "Câu trả lời thiếu citation."
        guard = {
            "status": "replaced",
            "reason": reason,
            "citations": sorted(citations),
            "invalid_citations": invalid_citations,
            "evidence_ids": sorted(evidence_ids),
        }
        fallback = _build_grounded_fallback(state, reason)
        console.print(Panel(reason, border_style="red", padding=(0, 1)))
        return {"answer": fallback, "output_guard": guard}

    guard = {
        "status": "pass",
        "reason": "Answer citations are grounded in retrieved evidence.",
        "citations": sorted(citations),
        "evidence_ids": sorted(evidence_ids),
    }
    console.print(Panel("Pass", border_style="green", padding=(0, 1)))
    return {"output_guard": guard}


def route_after_input_guard(state: AgenticRAGState) -> Literal["safe_decline", "intent_router"]:
    if state.get("guardrail", {}).get("status") == "blocked":
        return "safe_decline"
    return "intent_router"


def route_after_intent(state: AgenticRAGState) -> Literal["direct_answer", "decline", "reasoner_core"]:
    route = state.get("intent_route")
    if route == "chitchat":
        return "direct_answer"
    if route == "out_of_scope":
        return "decline"
    return "reasoner_core"


def route_after_action_validator(
    state: AgenticRAGState,
) -> Literal["retrieve", "clarify_question", "fallback", "answer"]:
    action = state.get("reasoner", {}).get("action", "retrieve")
    if action == "clarify":
        return "clarify_question"
    if action == "fallback":
        return "fallback"
    if action == "finalize":
        return "answer" if state.get("evidence") else "fallback"
    return "retrieve"


def route_after_budget(state: AgenticRAGState) -> Literal["answer", "reasoner_core", "fallback"]:
    budget = state.get("budget", {})
    next_step = budget.get("next")
    if next_step == "answer":
        return "answer"
    if next_step == "fallback":
        return "fallback"
    return "reasoner_core"


def build_agentic_rag_graph():
    workflow = StateGraph(AgenticRAGState)
    workflow.add_node("input_guard", input_guard_node)
    workflow.add_node("safe_decline", safe_decline_node)
    workflow.add_node("intent_router", intent_router_node)
    workflow.add_node("direct_answer", direct_answer_node)
    workflow.add_node("decline", decline_node)
    workflow.add_node("reasoner_core", reasoner_core_node)
    workflow.add_node("action_validator", action_validator_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("grade_evidence", grade_evidence_node)
    workflow.add_node("context_control", context_control_node)
    workflow.add_node("loop_budget", loop_budget_node)
    workflow.add_node("clarify_question", clarify_question_node)
    workflow.add_node("fallback", fallback_node)
    workflow.add_node("answer", answer_node)
    workflow.add_node("output_guard", output_guard_node)

    workflow.add_edge(START, "input_guard")
    workflow.add_conditional_edges(
        "input_guard",
        route_after_input_guard,
        {
            "safe_decline": "safe_decline",
            "intent_router": "intent_router",
        },
    )
    workflow.add_edge("safe_decline", END)

    workflow.add_conditional_edges(
        "intent_router",
        route_after_intent,
        {
            "direct_answer": "direct_answer",
            "decline": "decline",
            "reasoner_core": "reasoner_core",
        },
    )
    workflow.add_edge("direct_answer", "output_guard")
    workflow.add_edge("decline", "output_guard")

    workflow.add_edge("reasoner_core", "action_validator")
    workflow.add_conditional_edges(
        "action_validator",
        route_after_action_validator,
        {
            "retrieve": "retrieve",
            "clarify_question": "clarify_question",
            "fallback": "fallback",
            "answer": "answer",
        },
    )
    workflow.add_edge("retrieve", "grade_evidence")
    workflow.add_edge("grade_evidence", "context_control")
    workflow.add_edge("context_control", "loop_budget")
    workflow.add_conditional_edges(
        "loop_budget",
        route_after_budget,
        {
            "answer": "answer",
            "reasoner_core": "reasoner_core",
            "fallback": "fallback",
        },
    )

    workflow.add_edge("clarify_question", "output_guard")
    workflow.add_edge("fallback", "output_guard")
    workflow.add_edge("answer", "output_guard")
    workflow.add_edge("output_guard", END)

    return workflow.compile()


def create_initial_state(question: str) -> AgenticRAGState:
    return {
        "question": question,
        "protected_question": question,
        "pii_masks": {},
        "guardrail": {},
        "intent_route": "rag",
        "intent": {},
        "reasoner": {},
        "current_query": "",
        "retrieval_queries": [],
        "required_evidence": [],
        "search_history": [],
        "evidence": [],
        "rounds": 0,
        "judge": {},
        "failure_notes": [],
        "budget": {},
        "output_guard": {},
        "answer": "",
    }


def run_question_state(
    question: str,
    show_question: bool = False,
    session_id: str | None = None,
) -> AgenticRAGState:
    """Run the Agentic RAG graph and return the final state."""
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
