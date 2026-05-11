"""
═══════════════════════════════════════════════════════════════════════
RUNNER — Chạy Reflection Conversational Agent Demo
═══════════════════════════════════════════════════════════════════════

Demo chạy chatbot hỗ trợ khách hàng TechViet với Reflection pattern.
Mô phỏng hội thoại nhiều lượt, showcase cách agent tự review
và cải thiện câu trả lời trước khi gửi.

Usage:
    uv run python run.py          # Demo với kịch bản mẫu
    uv run python run.py --chat   # Chat tương tác
"""

import sys

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from reflection import ReflectiveConversation

console = Console()


# ═══════════════════════════════════════════════════════════════
# Demo Scenario — Hội thoại mẫu nhiều lượt
# ═══════════════════════════════════════════════════════════════

DEMO_CONVERSATION = [
    # Turn 1: Hỏi về sản phẩm
    "Cho mình hỏi giá điện thoại SmartPhone Pro X bao nhiêu?",

    # Turn 2: Hỏi tiếp về bảo hành (cần duy trì context)
    "Vậy bảo hành bao lâu? Có gói bảo hành mở rộng không?",

    # Turn 3: Yêu cầu phức tạp hơn (cần nhớ context trước đó)
    "Mình muốn mua 1 cái Pro X kèm gói TechCare 2 năm và TechCloud 1TB. "
    "Tổng chi phí bao nhiêu?",
]


def run_demo():
    """Chạy demo với kịch bản hội thoại mẫu."""

    console.print()
    console.print(Panel.fit(
        "[bold cyan]🔍 REFLECTION PATTERN[/bold cyan]\n"
        "[dim]Conversational Agent with Self-Review[/dim]\n\n"
        "Chatbot hỗ trợ khách hàng TechViet:\n"
        "  💬 Generator  — Tạo câu trả lời\n"
        "  🔍 Reflector  — Review chất lượng\n"
        "  🔄 Regenerator — Cải thiện nếu FAIL\n\n"
        "[dim]Flow: Generate → Reflect → (Regenerate) → Accept[/dim]",
        border_style="cyan",
        padding=(1, 3),
    ))

    conv = ReflectiveConversation()

    for i, message in enumerate(DEMO_CONVERSATION, 1):
        console.print()
        console.print(Rule(
            f"📌 Lượt {i}/{len(DEMO_CONVERSATION)}", style="bold white",
        ))
        conv.chat(message)
        console.print()
        console.print("─" * 70)

    # Tổng kết
    console.print()
    console.print(Panel.fit(
        "[bold green]✅ Demo hoàn tất![/bold green]\n\n"
        f"Đã xử lý {len(DEMO_CONVERSATION)} lượt hội thoại.\n"
        "Mỗi lượt, chatbot tự review câu trả lời trước khi gửi,\n"
        "đảm bảo mạch lạc với ngữ cảnh hội thoại trước đó.",
        border_style="green",
        padding=(1, 2),
    ))


def run_interactive():
    """Chạy chế độ chat tương tác."""

    console.print()
    console.print(Panel.fit(
        "[bold cyan]🔍 REFLECTION CHAT — Chế độ tương tác[/bold cyan]\n"
        "[dim]Gõ 'quit' hoặc 'exit' để thoát[/dim]",
        border_style="cyan",
        padding=(0, 2),
    ))

    conv = ReflectiveConversation()

    while True:
        console.print()
        user_input = console.input("[bold cyan]Bạn: [/bold cyan]")
        if user_input.strip().lower() in ("quit", "exit", "q"):
            console.print("[dim]Tạm biệt! 👋[/dim]")
            break
        if not user_input.strip():
            continue
        conv.chat(user_input.strip())


def main():
    if "--chat" in sys.argv:
        run_interactive()
    else:
        run_demo()


if __name__ == "__main__":
    main()
