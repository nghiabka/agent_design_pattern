"""
═══════════════════════════════════════════════════════════════════════
HUMAN-IN-THE-LOOP (HITL) DEMO — PHÊ DUYỆT GIAO DỊCH TÀI CHÍNH
═══════════════════════════════════════════════════════════════════════

Mô hình hóa luồng tương tác cần sự phê duyệt của con người trước khi
thực hiện hành động quan trọng (như chuyển tiền) bằng LangGraph.

Các tính năng được minh họa:
1. interrupt_before: Tự động dừng luồng trước khi chạy Node 'tools'.
2. Xem trạng thái tạm thời (snapshot).
3. Chấp thuận (Approve): Tiếp tục thực thi Graph.
4. Từ chối (Reject): Tự cập nhật State với kết quả hủy bỏ thay vì chạy Node thực.
5. Chỉnh sửa (Modify): Thay đổi tham số truyền vào Tool rồi tiếp tục chạy.
"""

import os
import sys
from typing import Annotated, Literal, Optional
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.rule import Rule

# Cấu hình local config
from config import OPENAI_API_BASE, OPENAI_API_KEY, OPENAI_MODEL_NAME

console = Console()

# ═══════════════════════════════════════════════════════════════
# 1. KHAI BÁO TOOLS
# ═══════════════════════════════════════════════════════════════

@tool
def transfer_money(recipient: str, amount: float) -> str:
    """Thực hiện chuyển khoản tiền đến một người nhận cụ thể."""
    # Giả lập một hành động quan trọng (Giao dịch ngân hàng thực)
    return f"✅ [THÀNH CÔNG] Đã chuyển thành công {amount:,} VNĐ đến tài khoản của {recipient}."

@tool
def check_balance() -> str:
    """Kiểm tra số dư khả dụng của tài khoản hiện tại."""
    return "💰 Số dư khả dụng hiện tại: 50,000,000 VNĐ."

# Gom nhóm các tools lại
tools = [transfer_money, check_balance]
tool_node = ToolNode(tools)

# ═══════════════════════════════════════════════════════════════
# 2. STATE VÀ GRAPH CONFIGURATION
# ═══════════════════════════════════════════════════════════════

class State(TypedDict):
    """State lưu trữ toàn bộ lịch sử hội thoại."""
    messages: Annotated[list[BaseMessage], add_messages]

# Thiết lập Model
llm = ChatOpenAI(
    model=OPENAI_MODEL_NAME,
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_API_BASE,
    temperature=0.1, # Đặt thấp để tránh sáng tạo quá mức với giao dịch
).bind_tools(tools)

# --- Các Nodes chính ---
def call_model(state: State):
    """Node xử lý hội thoại chính của AI."""
    system_msg = SystemMessage(
        content=(
            "Bạn là một Trợ lý Ngân hàng Số an toàn và hữu ích.\n"
            "Quy tắc: Bạn CÓ THỂ tự tra cứu số dư, nhưng khi khách hàng yêu cầu "
            "chuyển tiền, bạn MUST gọi công cụ `transfer_money`.\n"
            "Hãy nói chuyện ngắn gọn, lịch sự."
        )
    )
    messages = [system_msg] + state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}

# --- Hàm điều kiện phân nhánh (Routing) ---
def should_continue(state: State) -> Literal["tools", END]:
    """Kiểm tra xem AI có yêu cầu gọi công cụ (Tool Calls) hay không."""
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END

# --- Khởi tạo và Compile Graph ---
workflow = StateGraph(State)

# Thêm các node
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

# Thiết lập các đường kết nối (Edges)
workflow.add_edge(START, "agent")
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tools": "tools",
        END: END
    }
)
workflow.add_edge("tools", "agent")

# Cần MemorySaver để lưu vết ThreadID phục vụ việc tạm dừng và phục hồi (Interrupt)
memory = MemorySaver()

# CỰC KỲ QUAN TRỌNG: Sử dụng interrupt_before=["tools"] để bắt dừng lại 
# ngay trước khi thực hiện bất kỳ hành động của Tool nào!
graph = workflow.compile(
    checkpointer=memory,
    interrupt_before=["tools"] 
)

# ═══════════════════════════════════════════════════════════════
# 3. HÀM HỖ TRỢ GIAO DIỆN ĐIỀU KHIỂN (HITL CONTROL PANEL)
# ═══════════════════════════════════════════════════════════════

def print_separator(title: str, style: str = "cyan"):
    console.print("\n")
    console.print(Rule(title, style=style))
    console.print("\n")

def handle_hitl(config: dict):
    """
    Bảng điều khiển can thiệp con người (Human-in-the-loop Control Panel).
    Cho phép phê duyệt, từ chối hoặc chỉnh sửa tham số trước khi chạy Tool.
    """
    # 1. Lấy Snapshot của Graph hiện tại (đang trong trạng thái TẠM DỪNG)
    snapshot = graph.get_state(config)
    
    # Kiểm tra xem graph có đang bị chặn thật hay không
    if not snapshot.next:
        return # Không có node tiếp theo để chạy (Graph đã kết thúc bình thường)
        
    last_message = snapshot.values["messages"][-1]
    
    # Chỉ can thiệp nếu tin nhắn cuối cùng yêu cầu gọi tool
    if not getattr(last_message, "tool_calls", None):
        return

    tool_calls = last_message.tool_calls
    
    print_separator("🔔 CẢNH BÁO BẢO MẬT: CẦN PHÊ DUYỆT TỪ NGƯỜI DÙNG", style="bold yellow")
    
    table = Table(title="Các hành động đang chờ xử lý", show_header=True, header_style="bold magenta")
    table.add_column("ID Giao Dịch", style="dim")
    table.add_column("Tên Hành Động (Tool)", style="cyan")
    table.add_column("Tham Số / Dữ Liệu", style="green")
    
    for tc in tool_calls:
        table.add_row(tc["id"], tc["name"], str(tc["args"]))
        
    console.print(table)
    console.print("\n[bold yellow]Hệ thống đang tạm dừng để chờ bạn quyết định.[/bold yellow]")
    console.print("Vui lòng chọn một trong các tùy chọn sau:")
    console.print("[bold cyan][A][/bold cyan] Chấp thuận (Approve) - Cho phép chạy giao dịch này.")
    console.print("[bold red][R][/bold red] Từ chối (Reject) - Hủy bỏ giao dịch và báo lại cho AI.")
    console.print("[bold green][M][/bold green] Chỉnh sửa (Modify) - Sửa lại số tiền hoặc người nhận trước khi chạy.")
    
    choice = Prompt.ask("\nLựa chọn của bạn", choices=["a", "r", "m"], default="a").lower()
    
    if choice == "a":
        # --- TRƯỜNG HỢP 1: CHẤP THUẬN ---
        console.print("[bold cyan]👉 Bạn đã duyệt hành động. Đang tiếp tục thực thi...[/bold cyan]")
        # Chỉ cần chạy tiếp stream với Input là None, Graph sẽ tự đọc State hiện có để chạy Node 'tools'
        for event in graph.stream(None, config, stream_mode="values"):
            pass
            
    elif choice == "r":
        # --- TRƯỜNG HỢP 2: TỪ CHỐI ---
        console.print("[bold red]❌ Bạn đã từ chối giao dịch. Hủy bỏ lệnh gọi tool...[/bold red]")
        
        # Để hủy bỏ một cách sạch sẽ trong LangGraph:
        # Chúng ta TỰ TẠO ToolMessage giả lập phản hồi lỗi/từ chối từ người dùng.
        # Cập nhật vào State dưới danh nghĩa Node 'tools' (as_node="tools").
        # Việc này đánh lừa Graph rằng Node 'tools' đã chạy xong và trả về lý do từ chối.
        
        tool_cancellation_messages = []
        for tc in tool_calls:
            tool_cancellation_messages.append(
                ToolMessage(
                    content=f"⚠️ [GIAO DỊCH BỊ HỦY] Người dùng đã từ chối cấp quyền thực hiện hành động này ({tc['name']}).",
                    tool_call_id=tc["id"],
                    name=tc["name"]
                )
            )
            
        # Cập nhật trạng thái như thể Node 'tools' vừa hoàn thành
        graph.update_state(
            config,
            {"messages": tool_cancellation_messages},
            as_node="tools"
        )
        
        # Chạy tiếp để quay lại luồng Node 'agent' nhằm phản hồi người dùng
        for event in graph.stream(None, config, stream_mode="values"):
            pass
            
    elif choice == "m":
        # --- TRƯỜNG HỢP 3: CHỈNH SỬA THAM SỐ ---
        console.print("[bold green]✏️ Chế độ Chỉnh sửa Giao dịch:[/bold green]")
        
        modified_tool_calls = []
        for tc in tool_calls:
            new_args = tc["args"].copy()
            console.print(f"\n[bold yellow]Đang sửa thông số cho Tool: {tc['name']}[/bold yellow]")
            
            for k, v in tc["args"].items():
                new_v = Prompt.ask(f"Sửa trường [{k}]", default=str(v))
                
                # Ép kiểu lại nếu là số
                if isinstance(v, (int, float)):
                    try:
                        new_v = float(new_v) if "." in new_v or isinstance(v, float) else int(new_v)
                    except ValueError:
                        pass
                new_args[k] = new_v
                
            new_tc = tc.copy()
            new_tc["args"] = new_args
            modified_tool_calls.append(new_tc)
            
        # Cập nhật State của tin nhắn cuối cùng (đổi tham số của tool_calls)
        # Tạo ra một tin nhắn AI mới có cùng ID để LangGraph ghi đè lên tin nhắn cũ
        new_ai_message = AIMessage(
            content=last_message.content,
            tool_calls=modified_tool_calls,
            id=last_message.id
        )
        
        console.print("[bold yellow]🔄 Đang cập nhật lại State với thông số mới...[/bold yellow]")
        # Cập nhật state dưới tư cách Node 'agent' (ghi đè tin nhắn AI trước đó)
        graph.update_state(
            config,
            {"messages": [new_ai_message]},
            as_node="agent"
        )
        
        # Sau khi sửa, hỏi lại xem người dùng muốn chạy tiếp không
        if Confirm.ask("✅ Đã sửa đổi xong. Bạn có muốn TIẾP TỤC THỰC THI với thông số mới này?", default=True):
            for event in graph.stream(None, config, stream_mode="values"):
                pass
        else:
            # Tái đệ quy gọi lại menu HITL nếu người dùng đổi ý
            handle_hitl(config)

# ═══════════════════════════════════════════════════════════════
# 4. VÒNG LẶP HỘI THOẠI CHÍNH (CHAT LOOP)
# ═══════════════════════════════════════════════════════════════

def main():
    # Khởi tạo ThreadID cố định cho phiên làm việc này (yêu cầu bởi checkpointing)
    thread_id = "user_session_123"
    config = {"configurable": {"thread_id": thread_id}}
    
    print_separator("🏦 CHÀO MỪNG BẠN ĐẾN VỚI HITL FINANCIAL BOT 🏦", style="bold green")
    console.print(
        "Đây là demo minh họa cơ chế [bold blue]Human-In-The-Loop[/bold blue] trong LangGraph.\n"
        "🤖 [bold cyan]AI có thể giúp bạn[/bold cyan]:\n"
        " - Kiểm tra số dư tài khoản (Tự động chạy, không cần phê duyệt).\n"
        " - Chuyển tiền tới ai đó (Bắt buộc cần sự phê duyệt của bạn trước khi thực thi!).\n"
    )
    console.print("Gõ [bold red]'exit'[/bold red] hoặc [bold red]'quit'[/bold red] để kết thúc chương trình.\n")

    while True:
        try:
            user_input = console.input("\n[bold blue]Bạn 👤:[/bold blue] ")
            if user_input.lower() in ["exit", "quit", "q"]:
                console.print("[bold yellow]Cảm ơn bạn đã sử dụng dịch vụ! Tạm biệt.[/bold yellow]")
                break
                
            if not user_input.strip():
                continue

            # Đưa input của User vào luồng Graph
            inputs = {"messages": [HumanMessage(content=user_input)]}
            
            # Thực thi graph
            console.print("[dim]🤖 Trợ lý đang phân tích yêu cầu...[/dim]")
            
            # Ta dùng state stream
            final_state = None
            for event in graph.stream(inputs, config, stream_mode="values"):
                final_state = event
                
            # Kiểm tra xem sau khi chạy xong một lượt, Graph có bị ngắt (Interrupt) không
            snapshot = graph.get_state(config)
            
            if snapshot.next:
                # PHÁT HIỆN ĐANG BỊ TẠM DỪNG (Bởi interrupt_before=['tools'])
                # Gọi bảng điều khiển HITL để người dùng can thiệp
                handle_hitl(config)
                
                # Sau khi kết thúc luồng HITL, in câu trả lời cuối cùng của AI nếu có
                snapshot = graph.get_state(config)
                messages = snapshot.values["messages"]
                if messages and isinstance(messages[-1], AIMessage) and messages[-1].content:
                     console.print(f"\n[bold green]Trợ lý 🤖:[/bold green] {messages[-1].content}")
            else:
                # Chạy bình thường không bị gián đoạn (hoặc đã hoàn tất sau conditional logic)
                messages = snapshot.values["messages"]
                if messages:
                    last_msg = messages[-1]
                    if isinstance(last_msg, AIMessage) and last_msg.content:
                        console.print(f"\n[bold green]Trợ lý 🤖:[/bold green] {last_msg.content}")
                        
        except KeyboardInterrupt:
            console.print("\n[bold yellow]Đã dừng chương trình.[/bold yellow]")
            break
        except Exception as e:
            console.print(f"\n[bold red]❌ Đã xảy ra lỗi: {str(e)}[/bold red]")

if __name__ == "__main__":
    main()
