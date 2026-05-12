"""
═══════════════════════════════════════════════════════════════════════════════
CHATBOT — Conversational AI với Memory Management (LangGraph)
═══════════════════════════════════════════════════════════════════════════════

Design Pattern: MEMORY MANAGEMENT
──────────────────────────────────
Chatbot sử dụng LangGraph để quản lý flow hội thoại với 2 tầng bộ nhớ.
Đã được tối ưu hóa Streaming và Background Extraction:

1. CHAT FLOW (Real-time):
   • load_memory → chat
   • Stream output trực tiếp ra màn hình từng chữ.
   • Xử lý thẻ <think> mờ đi.

2. EXTRACTION FLOW (Background Thread):
   • extract_memory → save_memory
   • Chạy ngầm, không block trải nghiệm gõ phím của người dùng.
"""

import time
import threading
import sys

from langchain_core.messages import HumanMessage, BaseMessage

from graph import build_chat_graph, build_extraction_graph, _get_ltm
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.rule import Rule

console = Console()


# ═══════════════════════════════════════════════════════════════
# MEMORY-AWARE CHATBOT (Streaming + Async version)
# ═══════════════════════════════════════════════════════════════

class MemoryAwareChatbot:
    """Chatbot với Short-term + Long-term Memory, powered by LangGraph.

    Mỗi lượt hội thoại:
      1. Gọi chat_graph (load_memory → chat) với streaming.
      2. In câu trả lời trực tiếp ra màn hình.
      3. Cập nhật short-term memory (RAM).
      4. Spawn 1 thread phụ để chạy extraction_graph (lưu facts vào SQLite).
    """

    def __init__(self, user_id: str, max_turns: int = 10):
        self.user_id = user_id
        self.max_turns = max_turns
        self.messages: list[BaseMessage] = []
        self.turn_count = 0

        # Compile LangGraph
        self.chat_graph = build_chat_graph()
        self.extraction_graph = build_extraction_graph()

        # Ensure LongTermMemory is initialized
        self.ltm = _get_ltm(user_id)

    def stream_chat_generator(self, user_message: str):
        """Generator trả về từng chunk text cho Web API (SSE)."""
        self.turn_count += 1
        
        state = {
            "user_id": self.user_id,
            "messages": list(self.messages),
            "user_message": user_message,
            "long_term_context": "",
            "ai_response": "",
            "extracted_memory": {},
        }
        
        final_state = state
        
        for mode, data in self.chat_graph.stream(state, stream_mode=["messages", "updates"]):
            if mode == "messages":
                msg, metadata = data
                if metadata.get("langgraph_node") == "chat":
                    if msg.content:
                        yield msg.content
                    elif getattr(msg, "tool_calls", None):
                        for tool_call in msg.tool_calls:
                            yield f"\n\n*(🛠️ Đang gọi hệ thống MCP: {tool_call['name']}...)*\n\n"
            elif mode == "updates":
                if "chat" in data:
                    final_state.update(data["chat"])
        
        # Cập nhật local state
        ai_response = final_state.get("ai_response", "")
        self.messages = final_state.get("messages", self.messages)
        self._trim_messages()
        
        # Chạy Background Extraction
        extraction_state = {
            "user_id": self.user_id,
            "messages": list(self.messages),
            "user_message": user_message,
            "long_term_context": final_state.get("long_term_context", ""),
            "ai_response": ai_response,
            "extracted_memory": {},
        }
        threading.Thread(
            target=self._run_background_extraction,
            args=(extraction_state,),
            daemon=True
        ).start()

    def chat(self, user_message: str) -> str:
        self.turn_count += 1

        console.print()
        console.print(Panel.fit(
            f"[bold white]💬 \"{user_message}\"[/bold white]",
            title=f"[bold cyan]TURN {self.turn_count}[/bold cyan]",
            border_style="cyan", padding=(0, 2),
        ))

        console.print(
            f"  [dim]🧠 Short-term: {len(self.messages)} messages"
            f" ({self.turn_count - 1} turns, max {self.max_turns})[/dim]"
        )

        start = time.time()
        
        # Initial State for chat_graph
        state = {
            "user_id": self.user_id,
            "messages": list(self.messages),
            "user_message": user_message,
            "long_term_context": "",
            "ai_response": "",
            "extracted_memory": {},
        }

        console.print("\n[bold green]🤖 Response[/bold green]")
        console.print("╭───────────────────────────────────────────────────╮", style="green")
        print("│ ", end="")
        
        # ── 1. Streaming Real-time ────────────────────────────
        in_think_block = False
        final_state = state
        ai_response_text = ""
        
        for mode, data in self.chat_graph.stream(state, stream_mode=["messages", "updates"]):
            if mode == "messages":
                msg, metadata = data
                if metadata.get("langgraph_node") == "chat":
                    if msg.content:
                        chunk = msg.content
                    elif getattr(msg, "tool_calls", None):
                        for tc in msg.tool_calls:
                            chunk = f"\n*(🛠️ Đang gọi hệ thống MCP: {tc['name']}...)*\n"
                    else:
                        continue
                        
                    # Xử lý hiển thị thẻ <think>
                    if "<think>" in chunk:
                        in_think_block = True
                        parts = chunk.split("<think>")
                        print(parts[0], end="")
                        print("\033[90m<think>", end="") # Xám mờ
                        if len(parts) > 1:
                            print(parts[1], end="")
                    elif "</think>" in chunk:
                        parts = chunk.split("</think>")
                        print(parts[0], end="")
                        print("</think>\033[0m", end="") # Hết xám mờ
                        in_think_block = False
                        if len(parts) > 1:
                            print(parts[1], end="")
                    else:
                        # Thay newline thành newline + margin để giữ UI đẹp
                        chunk = chunk.replace("\n", "\n│ ")
                        
                        if in_think_block:
                            print(f"\033[90m{chunk}\033[0m", end="")
                        else:
                            print(chunk, end="")
                            
                    sys.stdout.flush()
                    
            elif mode == "updates":
                # Lấy state cập nhật từ node `chat`
                if "chat" in data:
                    final_state.update(data["chat"])
        
        print() # Newline sau khi stream xong
        console.print("╰───────────────────────────────────────────────────╯", style="green")
        
        elapsed = round(time.time() - start, 2)
        console.print(f"  ⏱️  {elapsed}s (Real-time generation)")

        # ── 2. Cập nhật local state ───────────────────────────
        ai_response = final_state.get("ai_response", "")
        self.messages = final_state.get("messages", self.messages)
        self._trim_messages()

        # ── 3. Chạy Background Extraction ─────────────────────
        # Tạo state mới cho extraction_graph dựa trên kết quả chat
        extraction_state = {
            "user_id": self.user_id,
            "messages": list(self.messages),
            "user_message": user_message,
            "long_term_context": final_state.get("long_term_context", ""),
            "ai_response": ai_response,
            "extracted_memory": {},
        }
        
        # Spawn thread chạy ngầm
        bg_thread = threading.Thread(
            target=self._run_background_extraction,
            args=(extraction_state,),
            daemon=True
        )
        bg_thread.start()

        return ai_response

    def _run_background_extraction(self, extraction_state: dict):
        """Hàm chạy ngầm graph trích xuất bộ nhớ."""
        # console.print(f"  [dim]🔄 [Bg] Bắt đầu phân tích & lưu trí nhớ...[/dim]")
        self.extraction_graph.invoke(extraction_state)

    def _trim_messages(self):
        """Sliding window — giữ max N turns."""
        max_messages = self.max_turns * 2
        if len(self.messages) > max_messages:
            removed = len(self.messages) - max_messages
            self.messages = self.messages[removed:]
            console.print(
                f"  [dim]📎 Short-term: trimmed {removed} messages"
                f" (giữ {self.max_turns} turns)[/dim]"
            )

    def end_session(self):
        """Kết thúc session — lưu summary vào long-term memory."""
        if self.turn_count > 0:
            console.print()
            console.print(Rule("💾 Lưu session summary", style="dim"))

            topics = []
            for m in self.messages:
                if isinstance(m, HumanMessage):
                    topics.append(m.content[:50])

            summary = (
                f"Session {self.turn_count} turns. "
                f"Topics: {'; '.join(topics[:5])}"
            )
            self.ltm.add_conversation_summary(summary)
            console.print(f"  [dim]📜 Summary saved: {summary[:80]}[/dim]")

    def show_memory_status(self):
        """Hiển thị trạng thái cả 2 loại memory."""
        console.print()
        console.print(Rule("🧠 Memory Status", style="magenta"))
        console.print(
            f"  Short-term: {len(self.messages)} messages"
            f" ({self.turn_count} turns, max {self.max_turns})"
        )
        self.ltm.print_status()
