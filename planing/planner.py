"""
═══════════════════════════════════════════════════════════════════════════════
PLANNING AGENT — Lập kế hoạch nhiều bước trước khi thực thi
═══════════════════════════════════════════════════════════════════════════════

Design Pattern: PLANNING
─────────────────────────
Agent KHÔNG thực thi ngay. Thay vào đó:
  1. PHÂN TÍCH yêu cầu → tạo plan (danh sách bước)
  2. THỰC THI từng bước trong plan (gọi tools)
  3. TỔNG HỢP kết quả → báo cáo cuối

Khác với Prompt Chaining (hard-coded steps),
Planning tạo plan DYNAMIC dựa trên yêu cầu user.

Flow:
  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────┐
  │  User Goal   │────▶│   PLANNER    │────▶│   EXECUTOR   │────▶│  REPORT  │
  │              │     │  (Tạo plan)  │     │  (Chạy plan) │     │  (Tổng   │
  │              │     │              │     │              │     │   hợp)   │
  └──────────────┘     └──────────────┘     └──────────────┘     └──────────┘
                             │                     │
                       ┌─────▼─────┐         ┌─────▼──────┐
                       │ Plan:     │         │ Step 1 ✅  │
                       │ 1. ...    │         │ Step 2 ✅  │
                       │ 2. ...    │         │ Step 3 ✅  │
                       │ 3. ...    │         │ Step 4 🔄  │
                       └───────────┘         └────────────┘
"""

import json
import time
from typing import TypedDict, Annotated

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from config import OPENAI_API_BASE, OPENAI_API_KEY, OPENAI_MODEL_NAME
from tools import ALL_TOOLS
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.rule import Rule
from rich.table import Table

console = Console()


# ═══════════════════════════════════════════════════════════════
# State Definition
# ═══════════════════════════════════════════════════════════════

class PlanningState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    user_goal: str
    plan: list[dict]           # List of steps: [{step, description, tool, args}]
    current_step: int
    step_results: list[str]    # Results from each executed step
    final_report: str


# ═══════════════════════════════════════════════════════════════
# LLM Factory
# ═══════════════════════════════════════════════════════════════

def create_llm(temperature: float = 0) -> ChatOpenAI:
    return ChatOpenAI(
        model=OPENAI_MODEL_NAME,
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_API_BASE,
        temperature=temperature,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )


# ═══════════════════════════════════════════════════════════════
# PROMPTS
# ═══════════════════════════════════════════════════════════════

PLANNER_PROMPT = """Bạn là một Travel Planner chuyên nghiệp.

Nhiệm vụ: Phân tích yêu cầu du lịch và tạo KẾ HOẠCH THỰC HIỆN (plan).

Bạn có các tools sau:
  • search_flights(origin, destination, date) — Tìm chuyến bay
  • search_hotels(destination, checkin, nights) — Tìm khách sạn
  • get_weather(destination, date) — Tra thời tiết
  • get_attractions(destination) — Điểm tham quan
  • estimate_budget(flight_cost, hotel_cost, days, travelers) — Ước tính ngân sách

Yêu cầu của khách hàng:
{user_goal}

Hãy tạo plan theo format JSON sau (CHÍNH XÁC, không thêm text ngoài):

```json
[
  {{
    "step": 1,
    "description": "Mô tả bước này",
    "tool": "tên_tool",
    "args": {{"param1": "value1", "param2": "value2"}}
  }},
  {{
    "step": 2,
    "description": "...",
    "tool": "...",
    "args": {{}}
  }}
]
```

Quy tắc:
  1. Sắp xếp thứ tự hợp lý (tra cứu trước → đặt sau)
  2. Bước cuối LUÔN là estimate_budget
  3. Tối thiểu 3 bước, tối đa 6 bước
  4. Nếu thiếu info (ngày, số người), dùng giá trị mặc định hợp lý
  5. CHỈ trả về JSON, KHÔNG giải thích
"""

REPORTER_PROMPT = """Bạn là Travel Planner chuyên nghiệp.

Yêu cầu gốc của khách hàng:
{user_goal}

Dưới đây là kết quả từ các bước thực hiện:

{all_results}

Nhiệm vụ: Tổng hợp kết quả thành BÁO CÁO KẾ HOẠCH DU LỊCH hoàn chỉnh.

Format báo cáo:

# 🗺️ Kế hoạch du lịch

## Tổng quan
(Tóm tắt chuyến đi)

## Lịch trình đề xuất
(Sắp xếp theo ngày)

## Chi phí dự kiến
(Bảng chi phí tổng hợp)

## Lưu ý & Gợi ý
(Tips hữu ích cho chuyến đi)

Trả lời bằng tiếng Việt, chi tiết và hữu ích.
"""


# ═══════════════════════════════════════════════════════════════
# Graph Nodes
# ═══════════════════════════════════════════════════════════════

def planner_node(state: PlanningState) -> PlanningState:
    """Node 1: PLANNER — Phân tích yêu cầu, tạo plan.

    LLM đọc yêu cầu user → output danh sách bước (JSON).
    Plan được tạo DYNAMIC dựa trên yêu cầu cụ thể.
    """
    console.print()
    console.print(Rule("📋 PLANNER — Tạo kế hoạch thực hiện", style="bold yellow"))
    console.print()

    start = time.time()
    llm = create_llm(temperature=0)

    prompt = PLANNER_PROMPT.format(user_goal=state["user_goal"])
    response = llm.invoke([HumanMessage(content=prompt)])
    raw = response.content.strip()
    elapsed = round(time.time() - start, 2)

    # Parse JSON plan
    try:
        # Tìm JSON trong response (có thể wrapped trong ```json...```)
        json_str = raw
        if "```json" in raw:
            json_str = raw.split("```json")[1].split("```")[0]
        elif "```" in raw:
            json_str = raw.split("```")[1].split("```")[0]
        plan = json.loads(json_str.strip())
    except (json.JSONDecodeError, IndexError):
        console.print(f"[red]⚠ Không parse được JSON, raw response:[/red]")
        console.print(f"[dim]{raw[:500]}[/dim]")
        # Fallback plan
        plan = [
            {"step": 1, "description": "Tra cứu thời tiết", "tool": "get_weather",
             "args": {"destination": "điểm đến", "date": "2025-07-01"}},
            {"step": 2, "description": "Tìm chuyến bay", "tool": "search_flights",
             "args": {"origin": "Hà Nội", "destination": "điểm đến", "date": "2025-07-01"}},
            {"step": 3, "description": "Tìm khách sạn", "tool": "search_hotels",
             "args": {"destination": "điểm đến", "checkin": "2025-07-01", "nights": 3}},
        ]

    # Hiển thị plan
    table = Table(title="📋 Plan", border_style="yellow", show_lines=True)
    table.add_column("Step", style="bold", width=6)
    table.add_column("Mô tả", width=35)
    table.add_column("Tool", style="cyan", width=20)
    table.add_column("Args", style="dim", width=35)

    for step in plan:
        args_str = ", ".join(f"{k}={v}" for k, v in step.get("args", {}).items())
        table.add_row(
            str(step["step"]),
            step["description"],
            step.get("tool", "—"),
            args_str[:60],
        )

    console.print(table)
    console.print(f"  ⏱️  {elapsed}s | {len(plan)} bước")

    return {"plan": plan, "current_step": 0, "step_results": []}


def executor_node(state: PlanningState) -> PlanningState:
    """Node 2: EXECUTOR — Thực thi từng bước trong plan.

    Lấy bước hiện tại → gọi tool tương ứng → lưu kết quả.
    Mỗi lần gọi chỉ thực thi 1 bước, loop sẽ quay lại cho bước tiếp.
    """
    plan = state["plan"]
    idx = state["current_step"]
    step = plan[idx]

    console.print()
    console.print(Rule(
        f"⚙️  EXECUTOR — Bước {step['step']}/{len(plan)}: {step['description']}",
        style="blue",
    ))

    start = time.time()

    # Tìm tool theo tên
    tool_name = step.get("tool", "")
    tool_map = {t.name: t for t in ALL_TOOLS}
    tool_fn = tool_map.get(tool_name)

    if tool_fn:
        try:
            args = step.get("args", {})
            # Convert numeric strings
            for k, v in args.items():
                if isinstance(v, str) and v.isdigit():
                    args[k] = int(v)
            result = tool_fn.invoke(args)
            console.print(f"  🔧 Tool: [cyan]{tool_name}[/cyan]")
            console.print(Panel(result, border_style="blue", padding=(0, 1)))
        except Exception as e:
            result = f"❌ Lỗi khi gọi {tool_name}: {str(e)}"
            console.print(f"  [red]{result}[/red]")
    else:
        result = f"⚠️ Tool '{tool_name}' không tồn tại — bỏ qua bước này."
        console.print(f"  [yellow]{result}[/yellow]")

    elapsed = round(time.time() - start, 2)
    console.print(f"  ⏱️  {elapsed}s")

    # Cập nhật state
    new_results = list(state["step_results"])
    new_results.append(f"[Bước {step['step']}] {step['description']}:\n{result}")

    return {
        "step_results": new_results,
        "current_step": idx + 1,
    }


def should_continue_executing(state: PlanningState) -> str:
    """Routing: còn bước → tiếp tục, hết bước → qua reporter."""
    if state["current_step"] < len(state["plan"]):
        return "execute"
    else:
        console.print(f"\n  [green]✓ Đã thực thi xong {len(state['plan'])} bước[/green]")
        return "report"


def reporter_node(state: PlanningState) -> PlanningState:
    """Node 3: REPORTER — Tổng hợp kết quả thành báo cáo."""
    console.print()
    console.print(Rule("📊 REPORTER — Tổng hợp báo cáo", style="bold green"))
    console.print()

    start = time.time()
    llm = create_llm(temperature=0.3)

    all_results = "\n\n".join(state["step_results"])
    prompt = REPORTER_PROMPT.format(
        user_goal=state["user_goal"],
        all_results=all_results,
    )

    response = llm.invoke([HumanMessage(content=prompt)])
    report = response.content
    elapsed = round(time.time() - start, 2)

    console.print(Panel(
        Markdown(report),
        title="[bold green]🗺️ BÁO CÁO KẾ HOẠCH DU LỊCH[/bold green]",
        border_style="green", padding=(1, 2),
    ))
    console.print(f"  ⏱️  {elapsed}s")

    return {"final_report": report}


# ═══════════════════════════════════════════════════════════════
# Build LangGraph
# ═══════════════════════════════════════════════════════════════

def build_planning_graph():
    """Xây dựng graph: planner → executor (loop) → reporter.

    START → planner → executor ──┬── executor (loop)
                                 └── reporter → END
    """
    graph = StateGraph(PlanningState)

    graph.add_node("planner", planner_node)
    graph.add_node("executor", executor_node)
    graph.add_node("reporter", reporter_node)

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "executor")
    graph.add_conditional_edges("executor", should_continue_executing, {
        "execute": "executor",
        "report": "reporter",
    })
    graph.add_edge("reporter", END)

    return graph.compile()


# ═══════════════════════════════════════════════════════════════
# Run Planning Agent
# ═══════════════════════════════════════════════════════════════

def run_planner(user_goal: str) -> dict:
    """Chạy Planning agent với yêu cầu user.

    Args:
        user_goal: Yêu cầu du lịch bằng ngôn ngữ tự nhiên.

    Returns:
        Dict chứa plan, step_results, final_report.
    """
    console.print()
    console.print(Panel.fit(
        f"[bold white]🎯 \"{user_goal}\"[/bold white]",
        title="[bold cyan]USER GOAL[/bold cyan]",
        border_style="cyan", padding=(0, 2),
    ))

    pipeline_start = time.time()

    app = build_planning_graph()
    result = app.invoke({
        "messages": [],
        "user_goal": user_goal,
        "plan": [],
        "current_step": 0,
        "step_results": [],
        "final_report": "",
    })

    total = round(time.time() - pipeline_start, 2)

    console.print()
    console.print(Rule("⏱️  Tổng kết", style="cyan"))
    console.print(f"  Plan:     {len(result['plan'])} bước")
    console.print(f"  Executed: {len(result['step_results'])} bước")
    console.print(f"  Tổng:     [bold]{total}s[/bold]")

    return result
