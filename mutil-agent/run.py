"""
═══════════════════════════════════════════════════════════════════════
RUNNER — Chạy Multi-Agent Art Creation Demo
═══════════════════════════════════════════════════════════════════════

Usage:
    uv run python run.py
    uv run python run.py "Ý tưởng nghệ thuật tùy chọn"
"""

import sys

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from agents import run_art_creation

console = Console()

DEMO_IDEAS = [
    "Một cảnh hoàng hôn trên biển với thuyền buồm cổ điển, "
    "ánh nắng vàng phản chiếu trên mặt nước lấp lánh",

    "Một thành phố tương lai cyberpunk về đêm, "
    "đèn neon xanh tím phản chiếu trên mặt đường ướt",

    "Khu rừng cổ thụ bí ẩn với ánh sáng xuyên qua tán lá, "
    "có con suối nhỏ chảy giữa những tảng đá phủ rêu",
]


def main():
    console.print()
    console.print(Panel.fit(
        "[bold cyan]🤝 MULTI-AGENT PATTERN[/bold cyan]\n"
        "[dim]Agent as a Tool — Art Creation Pipeline[/dim]\n\n"
        "Hai tác nhân phối hợp tạo ảnh nghệ thuật:\n"
        "  🎨 [magenta]Artist Agent[/magenta]   — Sáng tạo prompt chi tiết\n"
        "  🖼️ [blue]ImageGen Agent[/blue]  — Tạo ảnh từ prompt (Agent as Tool)\n\n"
        "[dim]Flow: User idea → Artist → ImageGen → File .png[/dim]",
        border_style="cyan", padding=(1, 3),
    ))

    if len(sys.argv) > 1:
        ideas = [" ".join(sys.argv[1:])]
    else:
        ideas = DEMO_IDEAS[:1]  # Chạy 1 demo mặc định

    for i, idea in enumerate(ideas, 1):
        if len(ideas) > 1:
            console.print()
            console.print(Rule(f"📌 Idea {i}/{len(ideas)}", style="bold white"))

        run_art_creation(idea)
        console.print()
        console.print("─" * 70)

    console.print()
    console.print(Panel.fit(
        "[bold green]✅ Art Creation hoàn tất![/bold green]\n\n"
        "Multi-Agent pattern (Agent as a Tool):\n"
        "  🎨 Artist Agent sáng tạo prompt\n"
        "  🖼️ ImageGen Agent tạo ảnh (được gọi như 1 tool)\n"
        "  📁 Ảnh output lưu tại thư mục output/\n\n"
        "[dim]Tip: uv run python run.py \"Ý tưởng của bạn\"[/dim]",
        border_style="green", padding=(1, 2),
    ))


if __name__ == "__main__":
    main()
