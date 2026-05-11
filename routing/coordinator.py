"""
═══════════════════════════════════════════════════════════════════════════════
COORDINATOR — Agent điều phối chính với Routing logic
═══════════════════════════════════════════════════════════════════════════════

Design Pattern: ROUTING (Agent Delegation)
──────────────────────────────────────────
Coordinator agent nhận tin nhắn từ user, phân tích nội dung,
và DELEGATE (chuyển tiếp) tới sub-agent chuyên biệt phù hợp.

Đây KHÔNG phải là Prompt Chaining (tuần tự).
Đây là ROUTING — chọn 1 trong N nhánh dựa trên nội dung yêu cầu.

Flow:
                    ┌──────────────────┐
                    │   User Request   │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │   COORDINATOR    │
                    │  (Phân loại &    │
                    │   Delegate)      │
                    └──┬─────┬─────┬───┘
                       │     │     │
              ┌────────┘     │     └────────┐
              │              │              │
     ┌────────▼──────┐ ┌────▼───────┐ ┌────▼────────┐
     │   BOOKER      │ │   INFO     │ │   UNCLEAR   │
     │  Agent        │ │   Agent    │ │   Agent     │
     │               │ │            │ │  (fallback) │
     │ booking_handler│ │ info_handler│ │ unclear_    │
     │  (flight,     │ │ (weather,  │ │  handler    │
     │   hotel)      │ │  visa...)  │ │             │
     └───────────────┘ └────────────┘ └─────────────┘

Key concept:
  • Coordinator dùng LLM để PHÂN LOẠI yêu cầu → chọn route
  • Mỗi route gọi một sub-agent riêng biệt
  • Sub-agent xử lý yêu cầu với tools chuyên biệt
  • Kết quả sub-agent trả về qua Coordinator → User
"""

import time
from typing import Literal, TypedDict, Annotated

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from config import OPENAI_API_BASE, OPENAI_API_KEY, OPENAI_MODEL_NAME
from agents import create_booker_agent, create_info_agent, create_unclear_agent
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.rule import Rule

console = Console()


# ═══════════════════════════════════════════════════════════════
# State Definition
# ═══════════════════════════════════════════════════════════════

class CoordinatorState(TypedDict):
    """State cho Coordinator graph.

    Attributes:
        messages: Danh sách messages (user + agent).
        route: Route được chọn bởi coordinator ("booker", "info", "unclear").
    """
    messages: Annotated[list[BaseMessage], add_messages]
    route: str


# ═══════════════════════════════════════════════════════════════
# Coordinator LLM — Phân loại yêu cầu
# ═══════════════════════════════════════════════════════════════

COORDINATOR_SYSTEM_PROMPT = """Bạn là Coordinator — agent điều phối chính của hệ thống du lịch.

Nhiệm vụ DUY NHẤT của bạn: Phân loại yêu cầu của khách hàng và chọn ROUTE phù hợp.

Bạn PHẢI trả lời CHÍNH XÁC một trong 3 từ sau (không thêm gì khác):

  booker   — Nếu yêu cầu liên quan đến ĐẶT CHỖ:
               đặt vé máy bay, đặt phòng khách sạn, booking, reservation

  info     — Nếu yêu cầu liên quan đến TRA CỨU THÔNG TIN:
               thời tiết, visa, điểm tham quan, tỷ giá, thông tin chung

  unclear  — Nếu yêu cầu KHÔNG RÕ RÀNG hoặc không thuộc 2 loại trên

CHỈ TRẢ LỜI 1 TỪ DUY NHẤT: booker, info, hoặc unclear.
"""


def create_coordinator_llm() -> ChatOpenAI:
    """Tạo LLM cho Coordinator (classifier)."""
    return ChatOpenAI(
        model=OPENAI_MODEL_NAME,
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_API_BASE,
        temperature=0,
        extra_body={
            "chat_template_kwargs": {"enable_thinking": False},
        },
    )


# ═══════════════════════════════════════════════════════════════
# Graph Nodes
# ═══════════════════════════════════════════════════════════════

def coordinator_node(state: CoordinatorState) -> CoordinatorState:
    """Node 1: Coordinator phân loại yêu cầu → chọn route.

    Coordinator LLM đọc tin nhắn user và trả về ĐÚNG 1 trong 3 routes:
    "booker", "info", "unclear".
    """
    llm = create_coordinator_llm()

    # Lấy tin nhắn cuối cùng của user
    user_message = state["messages"][-1].content

    console.print()
    console.print(Rule("🎯 COORDINATOR — Phân loại yêu cầu", style="bold cyan"))
    console.print(f"  📝 User: [italic]{user_message}[/italic]")

    # Gọi LLM để phân loại
    response = llm.invoke([
        {"role": "system", "content": COORDINATOR_SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ])

    # Parse route từ response
    route_raw = response.content.strip().lower()

    # Chuẩn hóa route (đề phòng LLM trả thừa text)
    if "booker" in route_raw:
        route = "booker"
    elif "info" in route_raw:
        route = "info"
    else:
        route = "unclear"

    console.print(f"  🔀 Route: [bold magenta]{route.upper()}[/bold magenta]")
    console.print()

    return {"route": route}


def booker_node(state: CoordinatorState) -> CoordinatorState:
    """Node 2a: Booker agent xử lý yêu cầu đặt chỗ."""
    console.print(Rule("✈️  BOOKER AGENT — Xử lý đặt chỗ", style="bold yellow"))
    console.print()

    start = time.time()
    agent = create_booker_agent()
    result = agent.invoke({"messages": state["messages"]})
    elapsed = time.time() - start

    final_content = result["messages"][-1].content

    # In các bước trung gian (tool calls)
    for msg in result["messages"]:
        msg_type = msg.__class__.__name__
        if msg_type == "AIMessage" and hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                console.print(f"  🤖 Tool call: [cyan]{tc['name']}[/cyan]({tc['args']})")
        elif msg_type == "ToolMessage":
            console.print(f"  ⚡ Tool result: [dim]{msg.content[:80]}...[/dim]")

    console.print()
    console.print(Panel(
        Markdown(final_content),
        title="[bold yellow]📤 Booker Response[/bold yellow]",
        border_style="yellow",
        padding=(1, 2),
    ))
    console.print(f"  ⏱️  Thời gian: [dim]{round(elapsed, 2)}s[/dim]")

    return {"messages": [AIMessage(content=final_content)]}


def info_node(state: CoordinatorState) -> CoordinatorState:
    """Node 2b: Info agent xử lý yêu cầu tra cứu thông tin."""
    console.print(Rule("ℹ️  INFO AGENT — Tra cứu thông tin", style="bold blue"))
    console.print()

    start = time.time()
    agent = create_info_agent()
    result = agent.invoke({"messages": state["messages"]})
    elapsed = time.time() - start

    final_content = result["messages"][-1].content

    # In các bước trung gian
    for msg in result["messages"]:
        msg_type = msg.__class__.__name__
        if msg_type == "AIMessage" and hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                console.print(f"  🤖 Tool call: [cyan]{tc['name']}[/cyan]({tc['args']})")
        elif msg_type == "ToolMessage":
            console.print(f"  ⚡ Tool result: [dim]{msg.content[:80]}...[/dim]")

    console.print()
    console.print(Panel(
        Markdown(final_content),
        title="[bold blue]📤 Info Response[/bold blue]",
        border_style="blue",
        padding=(1, 2),
    ))
    console.print(f"  ⏱️  Thời gian: [dim]{round(elapsed, 2)}s[/dim]")

    return {"messages": [AIMessage(content=final_content)]}


def unclear_node(state: CoordinatorState) -> CoordinatorState:
    """Node 2c: Unclear agent xử lý yêu cầu không rõ ràng."""
    console.print(Rule("🤔 UNCLEAR AGENT — Yêu cầu không rõ ràng", style="bold red"))
    console.print()

    start = time.time()
    agent = create_unclear_agent()
    result = agent.invoke({"messages": state["messages"]})
    elapsed = time.time() - start

    final_content = result["messages"][-1].content

    console.print(Panel(
        Markdown(final_content),
        title="[bold red]📤 Unclear Response[/bold red]",
        border_style="red",
        padding=(1, 2),
    ))
    console.print(f"  ⏱️  Thời gian: [dim]{round(elapsed, 2)}s[/dim]")

    return {"messages": [AIMessage(content=final_content)]}


# ═══════════════════════════════════════════════════════════════
# Routing Function — Conditional Edge
# ═══════════════════════════════════════════════════════════════

def route_decision(state: CoordinatorState) -> Literal["booker", "info", "unclear"]:
    """Routing function: đọc route từ state → chọn nhánh.

    Đây là trái tim của Routing pattern:
    Coordinator đã phân loại ở node trước, giờ chỉ cần đọc kết quả.
    """
    return state["route"]


# ═══════════════════════════════════════════════════════════════
# Build LangGraph
# ═══════════════════════════════════════════════════════════════

def build_coordinator_graph() -> StateGraph:
    """Xây dựng LangGraph cho Coordinator routing.

    Graph structure:
        START → coordinator → (routing) → booker | info | unclear → END
    """
    graph = StateGraph(CoordinatorState)

    # ── Add nodes ─────────────────────────────────────────────
    graph.add_node("coordinator", coordinator_node)
    graph.add_node("booker", booker_node)
    graph.add_node("info", info_node)
    graph.add_node("unclear", unclear_node)

    # ── Add edges ─────────────────────────────────────────────
    # START → coordinator (luôn bắt đầu bằng phân loại)
    graph.add_edge(START, "coordinator")

    # coordinator → routing (conditional edge)
    graph.add_conditional_edges(
        "coordinator",
        route_decision,
        {
            "booker": "booker",
            "info": "info",
            "unclear": "unclear",
        },
    )

    # Mỗi sub-agent → END (kết thúc sau khi xử lý)
    graph.add_edge("booker", END)
    graph.add_edge("info", END)
    graph.add_edge("unclear", END)

    return graph.compile()


# ═══════════════════════════════════════════════════════════════
# Run Coordinator
# ═══════════════════════════════════════════════════════════════

def run_coordinator(user_message: str) -> str:
    """Chạy Coordinator với một yêu cầu từ user.

    Args:
        user_message: Tin nhắn / yêu cầu của user.

    Returns:
        Response cuối cùng từ sub-agent được delegate.
    """
    console.print()
    console.print(Panel.fit(
        f"[bold white]💬 \"{user_message}\"[/bold white]",
        title="[bold cyan]USER REQUEST[/bold cyan]",
        border_style="cyan",
        padding=(0, 2),
    ))

    start = time.time()

    # Build & invoke graph
    app = build_coordinator_graph()
    result = app.invoke({
        "messages": [HumanMessage(content=user_message)],
        "route": "",
    })

    elapsed = time.time() - start

    # Trích xuất response cuối cùng
    final_response = result["messages"][-1].content

    console.print()
    console.print(Rule("✅ HOÀN TẤT", style="bold green"))
    console.print(f"  ⏱️  Tổng thời gian: [bold]{round(elapsed, 2)}s[/bold]")
    console.print()

    return final_response
