"""
═══════════════════════════════════════════════════════════════════════════════
SMART HOME AGENT — LLM Agent điều khiển nhà thông minh qua Tool Calls
═══════════════════════════════════════════════════════════════════════════════

Design Pattern: TOOL CALL (Function Calling)
─────────────────────────────────────────────
LLM agent nhận yêu cầu bằng ngôn ngữ tự nhiên từ user,
HIỂU Ý ĐỊNH, và GỌI ĐÚNG TOOL với ĐÚNG THAM SỐ để thực thi.

Đây là pattern cơ bản nhất của agentic AI:
  User nói → LLM hiểu → LLM chọn tool → Tool thực thi → LLM tổng hợp

Flow:
  ┌─────────────┐     ┌──────────────┐     ┌──────────────┐
  │ "Tắt đèn    │────▶│   LLM Agent  │────▶│  Tool Call:  │
  │  phòng khách"│     │  (Hiểu ý,   │     │ control_light│
  └─────────────┘     │  chọn tool)  │     │ (room, off)  │
                      └──────┬───────┘     └──────┬───────┘
                             │                    │
                             │    tool result      │
                             │◀───────────────────┘
                             │
                      ┌──────▼───────┐
                      │ "Đã tắt đèn  │
                      │  phòng khách" │
                      └──────────────┘

LLM có thể gọi NHIỀU tools trong 1 lượt nếu cần:
  "Tắt đèn và điều hòa phòng khách" → 2 tool calls
"""

import time

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from config import OPENAI_API_BASE, OPENAI_API_KEY, OPENAI_MODEL_NAME
from tools import ALL_TOOLS
from smart_home import smart_home
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.rule import Rule

console = Console()


# ═══════════════════════════════════════════════════════════════
# System Prompt — Smart Home Agent
# ═══════════════════════════════════════════════════════════════

AGENT_SYSTEM_PROMPT = """Bạn là trợ lý nhà thông minh (Smart Home Assistant).

Bạn có thể điều khiển các thiết bị trong nhà thông qua các tools có sẵn:
  💡 control_light    — Bật/tắt, chỉnh độ sáng, đổi màu đèn
  🌡️ control_ac       — Bật/tắt, chỉnh nhiệt độ, đổi chế độ điều hòa
  📺 control_tv       — Bật/tắt, chuyển kênh, chỉnh âm lượng TV
  🔒 control_lock     — Khóa/mở khóa cửa
  🎵 control_speaker  — Bật/tắt, phát nhạc, chỉnh âm lượng loa
  📊 get_device_status — Xem trạng thái thiết bị

Các phòng trong nhà:
  • phòng khách (living_room)
  • phòng ngủ (bedroom)
  • nhà bếp (kitchen)
  • cửa chính (entrance)
  • garage

Quy tắc:
  1. Hiểu yêu cầu ngôn ngữ tự nhiên → gọi đúng tool
  2. Nếu yêu cầu liên quan nhiều thiết bị → gọi nhiều tools
  3. Xác nhận kết quả sau khi thực hiện
  4. Nếu không hiểu yêu cầu → hỏi lại
  5. Trả lời bằng tiếng Việt, thân thiện
"""


# ═══════════════════════════════════════════════════════════════
# Create & Run Agent
# ═══════════════════════════════════════════════════════════════

def create_smart_home_agent():
    """Tạo ReAct agent với smart home tools."""
    llm = ChatOpenAI(
        model=OPENAI_MODEL_NAME,
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_API_BASE,
        temperature=0,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )

    return create_react_agent(
        llm,
        tools=ALL_TOOLS,
        prompt=AGENT_SYSTEM_PROMPT,
    )


def run_command(user_message: str) -> str:
    """Chạy agent với 1 yêu cầu từ user.

    Args:
        user_message: Yêu cầu bằng ngôn ngữ tự nhiên.

    Returns:
        Response từ agent.
    """
    console.print()
    console.print(Panel.fit(
        f"[bold white]🗣️ \"{user_message}\"[/bold white]",
        title="[bold cyan]USER COMMAND[/bold cyan]",
        border_style="cyan", padding=(0, 2),
    ))

    start = time.time()
    agent = create_smart_home_agent()

    result = agent.invoke({"messages": [("human", user_message)]})
    elapsed = round(time.time() - start, 2)

    # In chi tiết tool calls
    console.print()
    for msg in result["messages"]:
        msg_type = msg.__class__.__name__
        if msg_type == "AIMessage" and hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                console.print(f"  🔧 Tool call: [cyan]{tc['name']}[/cyan]")
                for k, v in tc["args"].items():
                    console.print(f"       {k}: [yellow]{v}[/yellow]")
        elif msg_type == "ToolMessage":
            console.print(f"  ⚡ Result: [dim]{msg.content}[/dim]")

    final = result["messages"][-1].content

    console.print()
    console.print(Panel(
        Markdown(final),
        title="[bold green]🤖 Smart Home Response[/bold green]",
        border_style="green", padding=(1, 2),
    ))
    console.print(f"  ⏱️  {elapsed}s")

    return final
