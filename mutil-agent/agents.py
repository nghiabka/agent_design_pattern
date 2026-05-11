"""
═══════════════════════════════════════════════════════════════════════════════
MULTI-AGENT — Artist Agent + ImageGen Agent (Agent as a Tool)
═══════════════════════════════════════════════════════════════════════════════

Design Pattern: MULTI-AGENT (Agent as a Tool)
──────────────────────────────────────────────
Artist Agent (quản lý sáng tạo) "gọi" ImageGen Agent như một tool.
ImageGen Agent lại sử dụng tool generate_image để tạo ảnh thật.

Cấu trúc lồng nhau:
  Artist Agent ──(gọi như tool)──▶ ImageGen Agent ──(gọi tool)──▶ generate_image
     (sáng tạo)                      (kỹ thuật)                    (tạo file)

Flow:
  ┌──────────────┐     ┌──────────────────┐     ┌──────────────────┐
  │  User Idea   │────▶│  ARTIST AGENT    │────▶│  IMAGEGEN AGENT  │
  │  "Vẽ cảnh   │     │                  │     │  (Agent as Tool) │
  │   hoàng hôn" │     │  1. Nghĩ ý tưởng│     │                  │
  │              │     │  2. Viết prompt  │     │  Nhận prompt     │
  │              │     │     chi tiết     │     │  → gọi API tạo   │
  │              │     │  3. Chọn style   │     │    ảnh           │
  │              │     │  4. "Gọi" agent  │     │  → trả file path │
  │              │     │     ImageGen     │     │                  │
  └──────────────┘     └──────────────────┘     └────────┬─────────┘
                                                         │
                                                ┌────────▼─────────┐
                                                │  generate_image  │
                                                │  (Pillow tool)   │
                                                │  → file .png     │
                                                └──────────────────┘
"""

import time
from typing import TypedDict, Annotated

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent

from config import OPENAI_API_BASE, OPENAI_API_KEY, OPENAI_MODEL_NAME
from image_gen import generate_image
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.rule import Rule

console = Console()


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
# IMAGEGEN AGENT — Tác nhân tạo ảnh (cấp dưới)
# ═══════════════════════════════════════════════════════════════

IMAGEGEN_SYSTEM_PROMPT = """Bạn là ImageGen — chuyên viên kỹ thuật tạo ảnh nghệ thuật.

Nhiệm vụ: Nhận prompt mô tả ảnh và sử dụng tool generate_image để tạo ảnh.

Quy tắc:
  1. Nhận prompt + style từ Artist Agent
  2. Gọi tool generate_image với prompt và style
  3. Trả về kết quả (đường dẫn file + metadata)
  4. LUÔN gọi tool, không tự tạo ảnh
"""


def create_imagegen_agent():
    """Tạo ImageGen agent với tool generate_image."""
    llm = create_llm(temperature=0)
    return create_react_agent(
        llm,
        tools=[generate_image],
        prompt=IMAGEGEN_SYSTEM_PROMPT,
    )


# ═══════════════════════════════════════════════════════════════
# WRAP ImageGen Agent AS A TOOL — "Agent as a Tool"
# ═══════════════════════════════════════════════════════════════
# Đây là core của pattern: biến 1 agent thành 1 tool
# để agent khác có thể "gọi" nó.

@tool
def imagegen_agent_tool(prompt: str, style: str = "default") -> str:
    """Gọi ImageGen Agent để tạo ảnh từ prompt mô tả.

    Đây là một AGENT được wrap thành TOOL.
    Khi Artist Agent gọi tool này, nó sẽ:
      1. Khởi tạo ImageGen Agent
      2. ImageGen Agent nhận prompt
      3. ImageGen Agent gọi generate_image tool
      4. Trả kết quả ngược lại cho Artist Agent

    Args:
        prompt: Mô tả chi tiết ảnh cần tạo (tiếng Anh chi tiết).
        style: Phong cách — "impressionist", "cyberpunk", "watercolor",
               "abstract", "surrealist", "default".

    Returns:
        Kết quả tạo ảnh (file path + metadata).
    """
    console.print()
    console.print(Rule("🖼️  IMAGEGEN AGENT — Đang tạo ảnh...", style="blue"))
    console.print(f"  📝 Prompt: [dim]{prompt[:100]}...[/dim]")
    console.print(f"  🎭 Style:  [cyan]{style}[/cyan]")

    start = time.time()

    agent = create_imagegen_agent()
    request = f"Tạo ảnh với prompt: \"{prompt}\" và style: \"{style}\""
    result = agent.invoke({"messages": [("human", request)]})

    elapsed = round(time.time() - start, 2)

    # Trích xuất tool results
    final = result["messages"][-1].content

    # In tool calls trung gian
    for msg in result["messages"]:
        msg_type = msg.__class__.__name__
        if msg_type == "AIMessage" and hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                console.print(f"  🔧 ImageGen gọi tool: [cyan]{tc['name']}[/cyan]")
        elif msg_type == "ToolMessage":
            console.print(f"  ⚡ Tool result: [dim]{msg.content[:80]}...[/dim]")

    console.print(f"  ⏱️  ImageGen hoàn tất: {elapsed}s")

    return final


# ═══════════════════════════════════════════════════════════════
# State Definition
# ═══════════════════════════════════════════════════════════════

class MultiAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    user_idea: str
    art_prompt: str
    art_style: str
    generation_result: str


# ═══════════════════════════════════════════════════════════════
# ARTIST AGENT — Tác nhân sáng tạo (cấp trên)
# ═══════════════════════════════════════════════════════════════

ARTIST_SYSTEM_PROMPT = """Bạn là Artist — nghệ sĩ sáng tạo cấp cao chuyên nghiệp.

Nhiệm vụ: Nhận ý tưởng từ khách hàng → sáng tạo prompt chi tiết → gọi ImageGen agent để tạo ảnh.

Quy trình:
  1. PHÂN TÍCH ý tưởng của khách hàng
  2. SÁNG TẠO prompt mô tả ảnh thật chi tiết bằng tiếng Anh, bao gồm:
     - Chủ thể chính (subject)
     - Bối cảnh (setting/background)
     - Ánh sáng (lighting)
     - Góc nhìn (perspective/angle)
     - Màu sắc chủ đạo (color palette)
     - Cảm xúc/mood
     - Chi tiết bổ sung (details)
  3. CHỌN style phù hợp: "impressionist", "cyberpunk", "watercolor",
     "abstract", "surrealist", hoặc "default"
  4. GỌI tool imagegen_agent_tool với prompt + style
  5. Trả kết quả cho khách hàng kèm mô tả nghệ thuật

BẠN KHÔNG TỰ VẼ — bạn chỉ sáng tạo prompt rồi GỌI imagegen_agent_tool.
Luôn trả lời bằng tiếng Việt.
"""


def artist_node(state: MultiAgentState) -> MultiAgentState:
    """Node: Artist Agent — sáng tạo + delegate cho ImageGen."""
    console.print()
    console.print(Rule("🎨 ARTIST AGENT — Sáng tạo ý tưởng", style="bold magenta"))
    console.print()

    start = time.time()

    # Artist Agent = ReAct agent với imagegen_agent_tool
    llm = create_llm(temperature=0.7)
    artist_agent = create_react_agent(
        llm,
        tools=[imagegen_agent_tool],
        prompt=ARTIST_SYSTEM_PROMPT,
    )

    user_idea = state["user_idea"]
    result = artist_agent.invoke({
        "messages": [("human", f"Hãy sáng tạo và tạo ảnh nghệ thuật cho ý tưởng sau: {user_idea}")]
    })

    elapsed = round(time.time() - start, 2)

    # Trích xuất thông tin
    final = result["messages"][-1].content
    art_prompt = ""
    art_style = ""
    gen_result = ""

    for msg in result["messages"]:
        msg_type = msg.__class__.__name__
        if msg_type == "AIMessage" and hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                if tc["name"] == "imagegen_agent_tool":
                    art_prompt = tc["args"].get("prompt", "")
                    art_style = tc["args"].get("style", "default")
                    console.print(f"\n  🎨 Artist gọi ImageGen Agent:")
                    console.print(f"     Prompt: [italic]{art_prompt[:100]}...[/italic]")
                    console.print(f"     Style:  [cyan]{art_style}[/cyan]")
        elif msg_type == "ToolMessage":
            gen_result = msg.content

    console.print()
    console.print(Panel(
        Markdown(final),
        title="[bold magenta]🎨 Artist Response[/bold magenta]",
        border_style="magenta", padding=(1, 2),
    ))
    console.print(f"  ⏱️  Tổng thời gian: {elapsed}s")

    return {
        "art_prompt": art_prompt,
        "art_style": art_style,
        "generation_result": gen_result,
        "messages": [AIMessage(content=final)],
    }


# ═══════════════════════════════════════════════════════════════
# Build LangGraph
# ═══════════════════════════════════════════════════════════════

def build_multi_agent_graph():
    """START → artist_node → END"""
    graph = StateGraph(MultiAgentState)
    graph.add_node("artist", artist_node)
    graph.add_edge(START, "artist")
    graph.add_edge("artist", END)
    return graph.compile()


# ═══════════════════════════════════════════════════════════════
# Run Multi-Agent
# ═══════════════════════════════════════════════════════════════

def run_art_creation(user_idea: str) -> dict:
    """Chạy pipeline tạo ảnh nghệ thuật.

    Flow:
      User idea → Artist Agent → (gọi) ImageGen Agent → (gọi) generate_image → File

    Args:
        user_idea: Ý tưởng sáng tạo từ user.

    Returns:
        Dict chứa prompt, style, result.
    """
    console.print()
    console.print(Panel.fit(
        f"[bold white]💡 \"{user_idea}\"[/bold white]",
        title="[bold cyan]USER IDEA[/bold cyan]",
        border_style="cyan", padding=(0, 2),
    ))

    start = time.time()
    app = build_multi_agent_graph()

    result = app.invoke({
        "messages": [],
        "user_idea": user_idea,
        "art_prompt": "",
        "art_style": "",
        "generation_result": "",
    })

    total = round(time.time() - start, 2)

    console.print()
    console.print(Rule("⏱️  Tổng kết", style="cyan"))
    console.print(f"  Ý tưởng:   [dim]{user_idea[:60]}[/dim]")
    console.print(f"  Style:     [cyan]{result.get('art_style', '?')}[/cyan]")
    console.print(f"  Tổng:      [bold]{total}s[/bold]")

    return result
