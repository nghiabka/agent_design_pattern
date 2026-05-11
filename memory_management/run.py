"""
═══════════════════════════════════════════════════════════════════════
RUNNER — Chạy Memory Management Chatbot Demo (LangGraph + Docker)
═══════════════════════════════════════════════════════════════════════

Usage:
    uv run python run.py              # Demo với kịch bản mẫu
    uv run python run.py --chat       # Chat tương tác
    uv run python run.py --status     # Xem trạng thái memory
    uv run python run.py --reset      # Xóa long-term memory

Docker:
    docker compose up                 # Chạy demo mode
    docker compose run -it app python run.py --chat   # Interactive
"""

import sys
import os

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from chatbot import MemoryAwareChatbot
from config import SQLITE_DB_PATH

console = Console()

DEFAULT_USER_ID = "demo_user"

# ═══════════════════════════════════════════════════════════════
# Demo — Mô phỏng 2 session để thấy long-term memory hoạt động
# ═══════════════════════════════════════════════════════════════

SESSION_1 = [
    "Xin chào! Mình tên là Minh, là kỹ sư phần mềm",
    "Mình thích uống cà phê và nghe nhạc lofi khi làm việc",
    "Dạo này mình đang gặp khó khăn với việc quản lý thời gian, nhiều deadline quá",
    "Cảm ơn bạn nhé, mình phải đi họp rồi!",
]

SESSION_2 = [
    "Chào bạn, mình quay lại nè!",
    "Bạn còn nhớ mình không? Mình tên gì?",
    "Hôm nay mình muốn tìm hiểu về kỹ thuật Pomodoro",
    "À mà mình cũng mới chuyển sang team AI rồi, thú vị lắm!",
]


def run_demo():
    """Chạy 2 session liên tiếp — showcase long-term memory persistence."""

    console.print()
    console.print(Panel.fit(
        "[bold cyan]🧠 MEMORY MANAGEMENT PATTERN[/bold cyan]\n"
        "[dim]LangGraph + SQLite | Short-term + Long-term Memory[/dim]\n\n"
        "  📝 [yellow]Short-term[/yellow]: Conversation history (LangGraph state)\n"
        "  💾 [magenta]Long-term[/magenta]:  Profile + Preferences (SQLite)\n"
        "  🔍 [blue]Extractor[/blue]:   LLM trích xuất facts (LangGraph node)\n"
        f"  🗄️  [green]Database[/green]:   {SQLITE_DB_PATH}\n\n"
        "  LangGraph Flow:\n"
        "  load_memory → chat → extract_memory → save_memory\n\n"
        "Demo gồm 2 session:\n"
        "  Session 1: User giới thiệu → chatbot ghi nhớ\n"
        "  Session 2: User quay lại → chatbot nhớ thông tin cũ!",
        border_style="cyan", padding=(1, 3),
    ))

    # ── SESSION 1 ─────────────────────────────────────────────
    console.print()
    console.print(Rule("📗 SESSION 1 — Lần đầu gặp mặt", style="bold green"))

    bot1 = MemoryAwareChatbot(user_id=DEFAULT_USER_ID, max_turns=10)

    for msg in SESSION_1:
        bot1.chat(msg)

    bot1.end_session()
    bot1.show_memory_status()

    console.print()
    console.print(Panel.fit(
        "[bold yellow]🔄 Kết thúc Session 1 — Short-term memory bị xóa.\n"
        "   Long-term memory đã persist trong SQLite![/bold yellow]",
        border_style="yellow",
    ))

    # ── SESSION 2 ─────────────────────────────────────────────
    console.print()
    console.print(Rule("📘 SESSION 2 — Quay lại (session mới)", style="bold blue"))
    console.print("[dim]Short-term trống, nhưng long-term memory vẫn còn![/dim]")

    bot2 = MemoryAwareChatbot(user_id=DEFAULT_USER_ID, max_turns=10)

    for msg in SESSION_2:
        bot2.chat(msg)

    bot2.end_session()
    bot2.show_memory_status()

    # ── Tổng kết ──────────────────────────────────────────────
    console.print()
    console.print(Panel.fit(
        "[bold green]✅ Demo hoàn tất![/bold green]\n\n"
        "Key observations:\n"
        "  📗 Session 1: Chatbot ghi nhận tên, nghề, sở thích\n"
        "  📘 Session 2: Chatbot NHỚ user dù short-term trống\n"
        "  💾 Long-term: Persist trong SQLite → giữ qua sessions\n"
        "  🔄 LangGraph: load_memory → chat → extract → save\n"
        "  🐳 Docker: SQLite volume persist qua container restart",
        border_style="green", padding=(1, 2),
    ))


def run_interactive():
    """Chạy chế độ chat tương tác."""
    console.print()
    console.print(Panel.fit(
        "[bold cyan]🧠 MEMORY CHAT — Tương tác[/bold cyan]\n"
        "[dim]'status' = xem memory, 'quit' = thoát[/dim]\n"
        f"[dim]DB: {SQLITE_DB_PATH}[/dim]",
        border_style="cyan",
    ))

    bot = MemoryAwareChatbot(user_id=DEFAULT_USER_ID, max_turns=10)

    while True:
        console.print()
        user_input = console.input("[bold cyan]Bạn: [/bold cyan]")
        cmd = user_input.strip().lower()

        if cmd in ("quit", "exit", "q"):
            bot.end_session()
            console.print("[dim]Tạm biệt! Memory đã được lưu 💾[/dim]")
            break
        if cmd == "status":
            bot.show_memory_status()
            continue
        if not cmd:
            continue

        bot.chat(user_input.strip())


def show_status():
    """Xem trạng thái long-term memory hiện tại."""
    bot = MemoryAwareChatbot(user_id=DEFAULT_USER_ID)
    bot.show_memory_status()


def reset_memory():
    """Xóa long-term memory (SQLite database)."""
    if os.path.exists(SQLITE_DB_PATH):
        os.remove(SQLITE_DB_PATH)
        console.print(f"[green]✅ Long-term memory đã được xóa: {SQLITE_DB_PATH}[/green]")
    else:
        console.print("[dim]Không có memory nào để xóa.[/dim]")


def main():
    if "--chat" in sys.argv:
        run_interactive()
    elif "--status" in sys.argv:
        show_status()
    elif "--reset" in sys.argv:
        reset_memory()
    else:
        run_demo()


if __name__ == "__main__":
    main()
