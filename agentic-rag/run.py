"""
═══════════════════════════════════════════════════════════════════════
RUNNER — Chạy Agentic RAG Demo
═══════════════════════════════════════════════════════════════════════

Usage:
    uv run python run.py
    uv run python run.py "Khách muốn chuyển 300 triệu qua mobile app có được không?"
    uv run python run.py --chat
"""

import sys

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from agent import run_question
from documents import DOCUMENTS
from tracing import langfuse_status

console = Console()


DEMO_QUESTIONS = [
    # {
    #     "question": "Khách hàng cá nhân muốn chuyển 300 triệu qua mobile app trong cùng một ngày thì có được không?",
    #     "description": "Cần tìm giới hạn giao dịch và điều kiện kênh mobile",
    # },
    # {
    #     "question": "Khách báo có giao dịch thẻ lạ từ 2 ngày trước. Nhân viên phải xử lý theo các bước nào?",
    #     "description": "Cần kết hợp chính sách khóa thẻ và quy trình dispute",
    # },
    # {
    #     "question": "Một startup mới mở tài khoản doanh nghiệp cần chuẩn bị giấy tờ gì và khi nào phải chuyển tuyến kiểm duyệt?",
    #     "description": "Cần tìm onboarding doanh nghiệp và escalation",
    # },
        {
        "question": "tôi cần đăng kí kết hôn",
        "description": "Cần các thủ tục gì",
    },
]


def print_intro() -> None:
    tracing = langfuse_status()
    if tracing["configured"]:
        tracing_line = f"  📡 Langfuse tracing: enabled ({tracing['host']})"
    elif tracing["enabled"]:
        tracing_line = "  📡 Langfuse tracing: disabled (missing keys)"
    else:
        tracing_line = "  📡 Langfuse tracing: disabled"

    console.print()
    console.print(Panel.fit(
        "[bold cyan]🤖 AGENTIC RAG PATTERN[/bold cyan]\n"
        "[dim]Query planning → retrieve → grade → rewrite → cited answer[/dim]\n\n"
        "Knowledge base nội bộ mô phỏng FinFlow Bank:\n"
        f"  📚 {len(DOCUMENTS)} tài liệu markdown\n"
        "  🔎 Retriever local BM25-style\n"
        "  🧪 LLM tự đánh giá evidence\n"
        "  ✍️ Tự rewrite query nếu thiếu chứng cứ\n"
        f"{tracing_line}\n\n"
        "[dim]Mục tiêu: cho thấy RAG có thể trở thành một agent có vòng điều khiển.[/dim]",
        border_style="cyan",
        padding=(1, 3),
    ))


def run_demo() -> None:
    print_intro()

    for idx, item in enumerate(DEMO_QUESTIONS, 1):
        console.print()
        console.print(Rule(
            f"📌 Demo {idx}/{len(DEMO_QUESTIONS)}: {item['description']}",
            style="bold white",
        ))
        run_question(item["question"])
        console.print("─" * 80)

    console.print()
    console.print(Panel.fit(
        "[bold green]✅ Demo hoàn tất![/bold green]\n"
        "Agent đã tự lập query, retrieve tài liệu, grade evidence và trả lời có citation.",
        border_style="green",
        padding=(1, 2),
    ))


def run_interactive() -> None:
    print_intro()
    console.print(Panel.fit(
        "[bold cyan]AGENTIC RAG CHAT[/bold cyan]\n"
        "[dim]Gõ 'sources' để xem KB, 'quit' để thoát[/dim]",
        border_style="cyan",
        padding=(0, 2),
    ))

    while True:
        console.print()
        user_input = console.input("[bold cyan]❓ Bạn: [/bold cyan]")
        cmd = user_input.strip().lower()

        if cmd in ("quit", "exit", "q"):
            console.print("[dim]Tạm biệt![/dim]")
            break
        if cmd == "sources":
            for doc in DOCUMENTS:
                console.print(f"  • [cyan]{doc.id}[/cyan] — {doc.title} ({doc.source})")
            continue
        if not user_input.strip():
            continue

        run_question(user_input.strip())


def main() -> None:
    args = [arg for arg in sys.argv[1:] if arg.strip()]

    if "--chat" in args:
        run_interactive()
        return

    custom_question = " ".join(arg for arg in args if arg != "--chat").strip()
    if custom_question:
        print_intro()
        run_question(custom_question)
    else:
        run_demo()


if __name__ == "__main__":
    main()
