"""
═══════════════════════════════════════════════════════════════════════
RUNNER — Chạy Parallelization A/B Testing Demo
═══════════════════════════════════════════════════════════════════════

Demo chạy parallel generation cho nhiều chủ đề khác nhau,
showcase tốc độ song song vs tuần tự.

Usage:
    uv run python run.py
    uv run python run.py "Chủ đề tùy chọn của bạn"
"""

import asyncio
import sys

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from parallel import run_ab_testing

console = Console()


# ═══════════════════════════════════════════════════════════════
# Demo Topics
# ═══════════════════════════════════════════════════════════════

DEMO_TOPICS = [
    "Trí tuệ nhân tạo đang thay đổi ngành giáo dục Việt Nam năm 2025",
    "Giới trẻ Việt Nam và xu hướng làm việc từ xa sau đại dịch",
    "Biến đổi khí hậu ảnh hưởng đến nông nghiệp đồng bằng sông Cửu Long",
]


async def main():
    """Entry point — chạy A/B Testing pipeline."""

    console.print()
    console.print(Panel.fit(
        "[bold cyan]⚡ PARALLELIZATION PATTERN[/bold cyan]\n"
        "[dim]A/B Testing & Multiple Options Generation[/dim]\n\n"
        "Tạo ĐỒNG THỜI nhiều phiên bản tiêu đề bài viết:\n"
        "  🎨 [yellow]Variant A[/yellow] — Sáng tạo / Gây tò mò (temp=0.9)\n"
        "  📰 [blue]Variant B[/blue]  — Chuyên nghiệp / Uy tín (temp=0.3)\n"
        "  📖 [magenta]Variant C[/magenta]  — Storytelling / Cảm xúc (temp=0.7)\n\n"
        "Sau đó Evaluator so sánh & chọn best option.\n\n"
        "[dim]Pipeline: Parallel Generate → Evaluate → Select Best[/dim]",
        border_style="cyan",
        padding=(1, 3),
    ))

    # Xác định topics
    if len(sys.argv) > 1:
        topics = [" ".join(sys.argv[1:])]
    else:
        topics = DEMO_TOPICS[:1]  # Chạy 1 topic mặc định cho demo nhanh

    # ── Chạy pipeline cho mỗi topic ──────────────────────────
    for i, topic in enumerate(topics, 1):
        if len(topics) > 1:
            console.print()
            console.print(Rule(
                f"📌 Topic {i}/{len(topics)}",
                style="bold white",
            ))

        result = run_ab_testing(topic)
        await result

        console.print()
        console.print("─" * 70)

    # ── Tổng kết ──────────────────────────────────────────────
    console.print()
    console.print(Panel.fit(
        "[bold green]✅ A/B Testing hoàn tất![/bold green]\n\n"
        "Parallelization pattern giúp:\n"
        "  🚀 Tốc độ: 3 variants chạy song song, nhanh gấp ~3x\n"
        "  🎯 Chất lượng: So sánh & chọn best option\n"
        "  🔄 Đa dạng: Mỗi variant có style riêng\n\n"
        "[dim]Tip: Chạy với topic tùy chọn:[/dim]\n"
        "[dim]  uv run python run.py \"Chủ đề của bạn\"[/dim]",
        border_style="green",
        padding=(1, 2),
    ))


if __name__ == "__main__":
    asyncio.run(main())
