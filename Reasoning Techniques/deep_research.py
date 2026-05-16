"""
═══════════════════════════════════════════════════════════════════════════════
DEEP RESEARCH AGENT — Research loop with Reflection
═══════════════════════════════════════════════════════════════════════════════

Design Pattern: REASONING TECHNIQUE / DEEP RESEARCH WITH REFLECTION
────────────────────────────────────────────────────────────────────
Agent tự động nghiên cứu theo vòng lặp:
  1. generate_query  — tạo truy vấn tìm kiếm ban đầu
  2. web_research    — chạy tìm kiếm web và tóm tắt nguồn
  3. reflection      — tự đánh giá đủ/chưa đủ thông tin
  4. finalize_answer — tổng hợp câu trả lời cuối có citation

Flow:
  START → generate_query → web_research → reflection ──┬── đủ → finalize_answer → END
                               ▲                       │
                               └──── chưa đủ ──────────┘

Ví dụ này phỏng theo graph structure của google-gemini/
gemini-fullstack-langgraph-quickstart, nhưng dùng OpenAI-compatible
ChatOpenAI config giống các pattern khác trong repo.
"""

from __future__ import annotations

import json
import operator
import time
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import Send
from pydantic import BaseModel, Field
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

from config import (
    ANSWER_MODEL_NAME,
    FINAL_NOTES_MAX_CHARS,
    INITIAL_SEARCH_QUERY_COUNT,
    MAX_RESEARCH_LOOPS,
    OPENAI_API_BASE,
    OPENAI_API_KEY,
    OPENAI_MAX_COMPLETION_TOKENS,
    OPENAI_TIMEOUT_SECONDS,
    QUERY_MODEL_NAME,
    REFLECTION_NOTES_MAX_CHARS,
    REFLECTION_MODEL_NAME,
    SEARCH_MAX_RESULTS,
    SEARCH_RESULTS_MAX_CHARS,
    SEARCH_SNIPPET_MAX_CHARS,
    RESEARCH_NOTE_MAX_CHARS,
    SOURCES_MAX_CHARS,
    USE_STRUCTURED_OUTPUT,
)
from prompts import (
    ANSWER_PROMPT,
    QUERY_WRITER_PROMPT,
    REFLECTION_PROMPT,
    WEB_RESEARCH_PROMPT,
    get_current_date,
)

console = Console()


# ═══════════════════════════════════════════════════════════════
# State and Schemas
# ═══════════════════════════════════════════════════════════════

class Source(TypedDict):
    id: str
    title: str
    url: str
    snippet: str


class DeepResearchState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]
    user_question: str
    queries_to_run: list[str]
    search_queries: Annotated[list[str], operator.add]
    research_notes: Annotated[list[str], operator.add]
    sources_gathered: Annotated[list[Source], operator.add]
    is_sufficient: bool
    knowledge_gap: str
    follow_up_queries: list[str]
    research_loop_count: int
    initial_search_query_count: int
    max_research_loops: int
    final_answer: str


class WebResearchState(TypedDict, total=False):
    user_question: str
    search_query: str
    query_id: int


class SearchQueryList(BaseModel):
    rationale: str = Field(description="Lý do chọn các truy vấn")
    queries: list[str] = Field(description="Danh sách truy vấn tìm kiếm")


class ReflectionResult(BaseModel):
    is_sufficient: bool = Field(description="True nếu thông tin đã đủ")
    knowledge_gap: str = Field(description="Thông tin còn thiếu, rỗng nếu đã đủ")
    follow_up_queries: list[str] = Field(description="Truy vấn follow-up nếu chưa đủ")


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def create_llm(model: str | None = None, temperature: float = 0) -> ChatOpenAI:
    return ChatOpenAI(
        model=model or QUERY_MODEL_NAME,
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_API_BASE,
        temperature=temperature,
        max_completion_tokens=OPENAI_MAX_COMPLETION_TOKENS,
        timeout=OPENAI_TIMEOUT_SECONDS,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )


def get_research_topic(state: DeepResearchState) -> str:
    if state.get("user_question"):
        return state["user_question"]

    messages = state.get("messages", [])
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return str(message.content)
    return ""


def extract_json_object(text: str) -> dict[str, Any]:
    raw = text.strip()
    if "```json" in raw:
        raw = raw.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in raw:
        raw = raw.split("```", 1)[1].split("```", 1)[0].strip()
    else:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            raw = raw[start:end + 1]
    return json.loads(raw)


def truncate_text(text: str, max_chars: int) -> str:
    """Keep prompts inside local model context limits."""
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "\n...[truncated]"


def invoke_structured(
    llm: ChatOpenAI,
    prompt: str,
    schema: type[BaseModel],
) -> BaseModel:
    """Use structured output when possible, then fall back to JSON parsing."""
    if USE_STRUCTURED_OUTPUT:
        try:
            result = llm.with_structured_output(schema).invoke([HumanMessage(content=prompt)])
            if isinstance(result, schema):
                return result
            return schema.model_validate(result)
        except Exception:
            pass

    json_prompt = (
        f"{prompt}\n\n"
        "Quan trọng: chỉ trả về JSON hợp lệ, không markdown, không giải thích."
    )
    response = llm.invoke([HumanMessage(content=json_prompt)])
    content = str(response.content).strip()
    if not content:
        raise ValueError("LLM returned empty content while JSON output was required.")
    return schema.model_validate(extract_json_object(content))


def invoke_text(llm: ChatOpenAI, prompt: str) -> str:
    response = llm.invoke([HumanMessage(content=prompt)])
    content = str(response.content).strip()
    if not content:
        raise ValueError("LLM returned empty content.")
    return content


def load_search_client():
    try:
        from ddgs import DDGS

        return DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS

            return DDGS
        except ImportError as exc:
            raise RuntimeError(
                "Thiếu thư viện search. Chạy `uv sync` trong thư mục này để cài `ddgs`."
            ) from exc


def search_web(query: str, query_id: int, max_results: int = SEARCH_MAX_RESULTS) -> list[Source]:
    DDGS = load_search_client()

    with DDGS() as ddgs:
        raw_results = list(ddgs.text(query, max_results=max_results))

    sources: list[Source] = []
    for index, item in enumerate(raw_results, 1):
        url = item.get("href") or item.get("url") or ""
        if not url:
            continue
        sources.append({
            "id": f"S{query_id + 1}-{index}",
            "title": truncate_text(item.get("title") or "Untitled", 160),
            "url": url,
            "snippet": truncate_text(
                item.get("body") or item.get("snippet") or "",
                SEARCH_SNIPPET_MAX_CHARS,
            ),
        })
    return sources


def format_search_results(
    sources: list[Source],
    max_chars: int = SEARCH_RESULTS_MAX_CHARS,
) -> str:
    if not sources:
        return "(Không có kết quả tìm kiếm khả dụng.)"

    blocks = []
    for source in sources:
        blocks.append(
            f"[{source['id']}]\n"
            f"Title: {source['title']}\n"
            f"URL: {source['url']}\n"
            f"Snippet: {source['snippet']}"
        )
    return truncate_text("\n\n".join(blocks), max_chars)


def format_research_notes(
    notes: list[str],
    max_chars: int = REFLECTION_NOTES_MAX_CHARS,
) -> str:
    if not notes:
        return "(Chưa có ghi chú nghiên cứu.)"

    trimmed_notes = [
        truncate_text(note, RESEARCH_NOTE_MAX_CHARS)
        for note in notes
    ]
    return truncate_text("\n\n---\n\n".join(trimmed_notes), max_chars)


def format_sources(
    sources: list[Source],
    max_chars: int = SOURCES_MAX_CHARS,
) -> str:
    if not sources:
        return "(Chưa có nguồn.)"

    seen: set[str] = set()
    lines: list[str] = []
    for source in sources:
        key = source["url"]
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"- [{source['id']}] {source['title']} — {source['url']}")
    return truncate_text("\n".join(lines), max_chars)


def build_search_note_from_sources(query: str, sources: list[Source]) -> str:
    if not sources:
        return f"Không thu thập được kết quả web cho truy vấn `{query}`."

    lines = [
        f"Ghi chú fallback cho truy vấn `{query}` vì LLM không tóm tắt được kết quả:",
    ]
    for source in sources:
        snippet = source["snippet"] or "(Không có snippet.)"
        lines.append(f"- [{source['id']}] {source['title']}: {snippet}")
    return truncate_text("\n".join(lines), RESEARCH_NOTE_MAX_CHARS)


def build_fallback_answer(question: str, notes: str, sources: str) -> str:
    return (
        "# Kết quả nghiên cứu\n\n"
        "LLM không tổng hợp được câu trả lời cuối, nên đây là bản fallback từ "
        "các ghi chú đã thu thập.\n\n"
        f"## Câu hỏi\n{question}\n\n"
        f"## Ghi chú\n{notes}\n\n"
        f"## Nguồn\n{sources}"
    )


def show_queries(title: str, queries: list[str], rationale: str | None = None) -> None:
    table = Table(title=title, border_style="yellow", show_lines=True)
    table.add_column("#", justify="right", width=4)
    table.add_column("Search query", style="cyan")
    for idx, query in enumerate(queries, 1):
        table.add_row(str(idx), query)
    console.print(table)
    if rationale:
        console.print(f"[dim]Rationale: {rationale}[/dim]")


# ═══════════════════════════════════════════════════════════════
# Graph Nodes
# ═══════════════════════════════════════════════════════════════

def generate_query(state: DeepResearchState) -> DeepResearchState:
    """Generate initial web search queries."""
    question = get_research_topic(state)
    number_queries = state.get("initial_search_query_count", INITIAL_SEARCH_QUERY_COUNT)

    console.print()
    console.print(Rule("GENERATE_QUERY — Tạo truy vấn tìm kiếm", style="bold yellow"))

    start = time.time()
    prompt = QUERY_WRITER_PROMPT.format(
        current_date=get_current_date(),
        research_topic=question,
        number_queries=number_queries,
    )
    llm = create_llm(model=QUERY_MODEL_NAME, temperature=0.2)
    try:
        result = invoke_structured(llm, prompt, SearchQueryList)
        queries = [query.strip() for query in result.queries if query.strip()][:number_queries]
        rationale = getattr(result, "rationale", "")
    except Exception as exc:
        console.print(f"[yellow]Không tạo được query bằng LLM, dùng câu hỏi gốc. Lỗi: {exc}[/yellow]")
        queries = [question]
        rationale = "Fallback: dùng trực tiếp câu hỏi gốc làm search query."
    elapsed = round(time.time() - start, 2)

    if not queries:
        queries = [question]

    show_queries("Initial Queries", queries, rationale)
    console.print(f"  Time: {elapsed}s")

    return {
        "user_question": question,
        "queries_to_run": queries,
    }


def continue_to_web_research(state: DeepResearchState) -> list[Send]:
    """Fan out every query into a separate web_research branch."""
    return [
        Send("web_research", {
            "user_question": get_research_topic(state),
            "search_query": query,
            "query_id": index,
        })
        for index, query in enumerate(state.get("queries_to_run", []))
    ]


def web_research(state: WebResearchState) -> DeepResearchState:
    """Run web search and convert raw results into a cited research note."""
    query = state["search_query"]
    query_id = state.get("query_id", 0)
    question = state.get("user_question", query)

    console.print()
    console.print(Rule(f"WEB_RESEARCH — {query}", style="blue"))

    start = time.time()
    try:
        sources = search_web(query, query_id=query_id)
        search_results = format_search_results(sources)
    except Exception as exc:
        sources = []
        search_results = f"(Search failed: {exc})"

    if sources:
        llm = create_llm(model=QUERY_MODEL_NAME, temperature=0)
        prompt = WEB_RESEARCH_PROMPT.format(
            research_topic=question,
            search_query=query,
            search_results=search_results,
        )
        try:
            note = truncate_text(invoke_text(llm, prompt), RESEARCH_NOTE_MAX_CHARS)
        except Exception as exc:
            console.print(f"[yellow]LLM web summary failed, dùng snippet fallback. Lỗi: {exc}[/yellow]")
            note = build_search_note_from_sources(query, sources)
    else:
        note = (
            f"Không thu thập được kết quả web cho truy vấn `{query}`.\n\n"
            f"Chi tiết: {search_results}"
        )

    elapsed = round(time.time() - start, 2)
    console.print(Panel(Markdown(note), title="Research Note", border_style="blue"))
    console.print(f"  Sources: {len(sources)} | Time: {elapsed}s")

    return {
        "search_queries": [query],
        "research_notes": [note],
        "sources_gathered": sources,
    }


def reflection(state: DeepResearchState) -> DeepResearchState:
    """Evaluate whether the gathered evidence is sufficient."""
    loop_count = state.get("research_loop_count", 0) + 1
    question = get_research_topic(state)
    notes = format_research_notes(
        state.get("research_notes", []),
        max_chars=REFLECTION_NOTES_MAX_CHARS,
    )

    console.print()
    console.print(Rule(
        f"REFLECTION — Đánh giá đủ/chưa đủ (loop {loop_count})",
        style="bold magenta",
    ))

    start = time.time()
    prompt = REFLECTION_PROMPT.format(
        current_date=get_current_date(),
        research_topic=question,
        research_notes=notes,
    )
    llm = create_llm(model=REFLECTION_MODEL_NAME, temperature=0)
    try:
        result = invoke_structured(llm, prompt, ReflectionResult)
    except Exception as exc:
        console.print(f"[yellow]Reflection failed, chuyển sang finalize. Lỗi: {exc}[/yellow]")
        result = ReflectionResult(
            is_sufficient=True,
            knowledge_gap=f"Reflection fallback do lỗi model: {exc}",
            follow_up_queries=[],
        )
    elapsed = round(time.time() - start, 2)

    status = "ĐỦ" if result.is_sufficient else "CHƯA ĐỦ"
    color = "green" if result.is_sufficient else "red"
    console.print(Panel(
        f"[bold]{status}[/bold]\n\nKnowledge gap: {result.knowledge_gap or '(không có)'}",
        title="Reflection Result",
        border_style=color,
    ))

    if result.follow_up_queries:
        show_queries("Follow-up Queries", result.follow_up_queries)
    console.print(f"  Time: {elapsed}s")

    return {
        "is_sufficient": result.is_sufficient,
        "knowledge_gap": result.knowledge_gap,
        "follow_up_queries": result.follow_up_queries,
        "research_loop_count": loop_count,
    }


def evaluate_research(state: DeepResearchState) -> str | list[Send]:
    """Conditional edge: continue researching or finalize."""
    max_loops = state.get("max_research_loops", MAX_RESEARCH_LOOPS)
    loop_count = state.get("research_loop_count", 0)
    follow_up_queries = state.get("follow_up_queries", [])

    if state.get("is_sufficient") or loop_count >= max_loops or not follow_up_queries:
        console.print("[green]→ Route: finalize_answer[/green]")
        return "finalize_answer"

    console.print("[yellow]→ Route: web_research (follow-up)[/yellow]")
    query_offset = len(state.get("search_queries", []))
    return [
        Send("web_research", {
            "user_question": get_research_topic(state),
            "search_query": query,
            "query_id": query_offset + index,
        })
        for index, query in enumerate(follow_up_queries)
    ]


def finalize_answer(state: DeepResearchState) -> DeepResearchState:
    """Synthesize final answer from all notes and gathered sources."""
    question = get_research_topic(state)
    notes = format_research_notes(
        state.get("research_notes", []),
        max_chars=FINAL_NOTES_MAX_CHARS,
    )
    sources = format_sources(state.get("sources_gathered", []))

    console.print()
    console.print(Rule("FINALIZE_ANSWER — Tổng hợp câu trả lời cuối", style="bold green"))

    start = time.time()
    prompt = ANSWER_PROMPT.format(
        current_date=get_current_date(),
        research_topic=question,
        research_notes=notes,
        sources=sources,
    )
    llm = create_llm(model=ANSWER_MODEL_NAME, temperature=0)
    try:
        final_answer = invoke_text(llm, prompt)
    except Exception as exc:
        console.print(f"[yellow]Final answer LLM failed, dùng fallback. Lỗi: {exc}[/yellow]")
        final_answer = build_fallback_answer(question, notes, sources)
    elapsed = round(time.time() - start, 2)

    console.print(Panel(
        Markdown(final_answer),
        title="Final Answer",
        border_style="green",
        padding=(1, 2),
    ))
    console.print(f"  Time: {elapsed}s")

    return {
        "final_answer": final_answer,
        "messages": [AIMessage(content=final_answer)],
    }


# ═══════════════════════════════════════════════════════════════
# Build LangGraph
# ═══════════════════════════════════════════════════════════════

def build_deep_research_graph():
    builder = StateGraph(DeepResearchState)

    builder.add_node("generate_query", generate_query)
    builder.add_node("web_research", web_research)
    builder.add_node("reflection", reflection)
    builder.add_node("finalize_answer", finalize_answer)

    builder.add_edge(START, "generate_query")
    builder.add_conditional_edges(
        "generate_query",
        continue_to_web_research,
        ["web_research"],
    )
    builder.add_edge("web_research", "reflection")
    builder.add_conditional_edges(
        "reflection",
        evaluate_research,
        ["web_research", "finalize_answer"],
    )
    builder.add_edge("finalize_answer", END)

    return builder.compile()


def run_deep_research(
    question: str,
    initial_search_query_count: int = INITIAL_SEARCH_QUERY_COUNT,
    max_research_loops: int = MAX_RESEARCH_LOOPS,
) -> DeepResearchState:
    graph = build_deep_research_graph()
    initial_state: DeepResearchState = {
        "messages": [HumanMessage(content=question)],
        "user_question": question,
        "queries_to_run": [],
        "search_queries": [],
        "research_notes": [],
        "sources_gathered": [],
        "is_sufficient": False,
        "knowledge_gap": "",
        "follow_up_queries": [],
        "research_loop_count": 0,
        "initial_search_query_count": initial_search_query_count,
        "max_research_loops": max_research_loops,
        "final_answer": "",
    }
    return graph.invoke(initial_state)
