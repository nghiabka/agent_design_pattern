"""
═══════════════════════════════════════════════════════════════════════════════
REFLECTION AGENT — Conversational Agent with Self-Review
═══════════════════════════════════════════════════════════════════════════════

Design Pattern: REFLECTION
───────────────────────────
Sau mỗi lượt trả lời, agent TỰ REVIEW câu trả lời của mình.
Nếu không đạt → sinh lại câu trả lời cải thiện.

Flow:
  START → generator → reflector ──┬── accept → END
              ▲                   │
              │     regenerate    │
              └───────────────────┘
"""

import time
from typing import TypedDict, Annotated

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from config import OPENAI_API_BASE, OPENAI_API_KEY, OPENAI_MODEL_NAME
from prompts import GENERATOR_SYSTEM_PROMPT, REFLECTOR_PROMPT, REGENERATOR_PROMPT
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.rule import Rule

console = Console()

MAX_REFLECTIONS = 2


class ReflectionState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    draft_response: str
    reflection_feedback: str
    reflection_count: int
    verdict: str


def create_llm(temperature: float = 0) -> ChatOpenAI:
    return ChatOpenAI(
        model=OPENAI_MODEL_NAME,
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_API_BASE,
        temperature=temperature,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )


def format_history(messages: list[BaseMessage]) -> str:
    lines = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            lines.append(f"[Khách hàng]: {msg.content}")
        elif isinstance(msg, AIMessage):
            lines.append(f"[Chatbot]: {msg.content}")
    return "\n".join(lines) if lines else "(Chưa có lịch sử)"


# ═══════════════════════════════════════════════════════════════
# Graph Nodes
# ═══════════════════════════════════════════════════════════════

def generator_node(state: ReflectionState) -> ReflectionState:
    """GENERATOR — Tạo hoặc cải thiện câu trả lời."""
    reflection_count = state.get("reflection_count", 0)
    messages = state["messages"]
    llm = create_llm(temperature=0.3)

    if reflection_count == 0:
        # Lần đầu: Generate từ conversation history
        console.print()
        console.print(Rule("💬 GENERATOR — Tạo câu trả lời", style="yellow"))

        start = time.time()
        llm_messages = [SystemMessage(content=GENERATOR_SYSTEM_PROMPT)] + list(messages)
        response = llm.invoke(llm_messages)
        draft = response.content
        elapsed = round(time.time() - start, 2)

        console.print(Panel(
            Markdown(draft),
            title="[bold yellow]📝 Draft Response (v1)[/bold yellow]",
            border_style="yellow", padding=(1, 2),
        ))
        console.print(f"  ⏱️  {elapsed}s")
    else:
        # Regenerate dựa trên reflection feedback
        console.print()
        console.print(Rule(
            f"🔄 REGENERATOR — Cải thiện (v{reflection_count + 1})", style="magenta",
        ))

        start = time.time()
        prompt_filled = REGENERATOR_PROMPT.format(
            conversation_history=format_history(messages),
            old_response=state["draft_response"],
            reflection_feedback=state["reflection_feedback"],
        )
        response = llm.invoke([HumanMessage(content=prompt_filled)])
        draft = response.content
        elapsed = round(time.time() - start, 2)

        console.print(Panel(
            Markdown(draft),
            title=f"[bold magenta]📝 Improved (v{reflection_count + 1})[/bold magenta]",
            border_style="magenta", padding=(1, 2),
        ))
        console.print(f"  ⏱️  {elapsed}s")

    return {"draft_response": draft}


def reflector_node(state: ReflectionState) -> ReflectionState:
    """REFLECTOR — Review câu trả lời, đánh giá chất lượng."""
    reflection_count = state.get("reflection_count", 0)

    console.print()
    console.print(Rule(
        f"🔍 REFLECTOR — Review lần {reflection_count + 1}/{MAX_REFLECTIONS}", style="cyan",
    ))

    start = time.time()
    llm = create_llm(temperature=0)

    prompt_filled = REFLECTOR_PROMPT.format(
        conversation_history=format_history(state["messages"]),
        last_response=state["draft_response"],
    )
    response = llm.invoke([HumanMessage(content=prompt_filled)])
    feedback = response.content
    elapsed = round(time.time() - start, 2)

    # Parse verdict
    verdict = "PASS"
    if "VERDICT: FAIL" in feedback.upper() or "VERDICT:FAIL" in feedback.upper():
        verdict = "FAIL"

    color = "green" if verdict == "PASS" else "red"
    console.print(Panel(
        Markdown(feedback),
        title=f"[bold {color}]🔍 Reflection Feedback[/bold {color}]",
        border_style=color, padding=(1, 2),
    ))
    console.print(f"  📊 Verdict: [bold {color}]{verdict}[/bold {color}]")
    console.print(f"  ⏱️  {elapsed}s")

    return {
        "reflection_feedback": feedback,
        "reflection_count": reflection_count + 1,
        "verdict": verdict,
    }


def should_continue(state: ReflectionState) -> str:
    """PASS → accept, FAIL (chưa max) → regenerate, FAIL (max) → accept."""
    verdict = state.get("verdict", "PASS")
    count = state.get("reflection_count", 0)

    if verdict == "PASS":
        console.print(f"\n  [green]✓ PASS — Đạt chất lượng[/green]")
        return "accept"
    elif count >= MAX_REFLECTIONS:
        console.print(f"\n  [yellow]⚠ Đạt giới hạn {MAX_REFLECTIONS} lần — dùng bản cuối[/yellow]")
        return "accept"
    else:
        console.print(f"\n  [red]✗ FAIL — Cần cải thiện (còn {MAX_REFLECTIONS - count} lần)[/red]")
        return "regenerate"


def accept_node(state: ReflectionState) -> ReflectionState:
    """Chấp nhận draft và thêm vào messages."""
    final = state["draft_response"]
    console.print()
    console.print(Rule("✅ ACCEPTED", style="bold green"))
    console.print(Panel(
        Markdown(final),
        title="[bold green]📤 Final Response[/bold green]",
        border_style="green", padding=(1, 2),
    ))
    return {"messages": [AIMessage(content=final)]}


# ═══════════════════════════════════════════════════════════════
# Build LangGraph
# ═══════════════════════════════════════════════════════════════

def build_reflection_graph():
    """START → generator → reflector → accept | generator (loop)."""
    graph = StateGraph(ReflectionState)

    graph.add_node("generator", generator_node)
    graph.add_node("reflector", reflector_node)
    graph.add_node("accept", accept_node)

    graph.add_edge(START, "generator")
    graph.add_edge("generator", "reflector")
    graph.add_conditional_edges("reflector", should_continue, {
        "accept": "accept",
        "regenerate": "generator",
    })
    graph.add_edge("accept", END)

    return graph.compile()


# ═══════════════════════════════════════════════════════════════
# Conversational Interface — Giữ state qua nhiều lượt
# ═══════════════════════════════════════════════════════════════

class ReflectiveConversation:
    """Quản lý hội thoại nhiều lượt với reflection."""

    def __init__(self):
        self.messages: list[BaseMessage] = []
        self.turn_count = 0
        self.graph = build_reflection_graph()

    def chat(self, user_message: str) -> str:
        """Xử lý 1 lượt hội thoại với reflection."""
        self.turn_count += 1
        console.print()
        console.print(Panel.fit(
            f"[bold white]💬 \"{user_message}\"[/bold white]",
            title=f"[bold cyan]TURN {self.turn_count}[/bold cyan]",
            border_style="cyan", padding=(0, 2),
        ))

        self.messages.append(HumanMessage(content=user_message))
        start = time.time()

        result = self.graph.invoke({
            "messages": list(self.messages),
            "draft_response": "",
            "reflection_feedback": "",
            "reflection_count": 0,
            "verdict": "",
        })

        elapsed = round(time.time() - start, 2)
        final = result["draft_response"]
        self.messages.append(AIMessage(content=final))

        console.print()
        console.print(f"  ⏱️  Turn time: [bold]{elapsed}s[/bold]")
        console.print(f"  🔄 Reflections: {result['reflection_count']}")
        console.print(f"  📜 History: {len(self.messages)} messages")

        return final
