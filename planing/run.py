"""
═══════════════════════════════════════════════════════════════════════
RUNNER — Chạy Planning Agent Demo
═══════════════════════════════════════════════════════════════════════

Usage:
    uv run python run.py
    uv run python run.py "Yêu cầu du lịch tùy chọn"
"""

import sys

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from planner import run_planner

console = Console()

DEMO_GOALS = [
    "Mình muốn đi du lịch Đà Nẵng 4 ngày từ Hà Nội, 2 người, "
    "ngân sách tầm trung. Muốn biết thời tiết, chỗ ở, và chỗ chơi.",
]


def main():
    console.print()
    console.print(Panel.fit(
        "[bold cyan]📋 PLANNING PATTERN[/bold cyan]\n"
        "[dim]Travel Planner — Lập kế hoạch nhiều bước[/dim]\n\n"
        "Agent tự tạo plan DYNAMIC dựa trên yêu cầu:\n"
        "  📋 Planner  — Phân tích → tạo danh sách bước\n"
        "  ⚙️  Executor — Thực thi từng bước (gọi tools)\n"
        "  📊 Reporter — Tổng hợp báo cáo cuối\n\n"
        "[dim]Flow: Goal → Plan → Execute (loop) → Report[/dim]",
        border_style="cyan", padding=(1, 3),
    ))

    if len(sys.argv) > 1:
        goals = [" ".join(sys.argv[1:])]
    else:
        goals = DEMO_GOALS

    for i, goal in enumerate(goals, 1):
        if len(goals) > 1:
            console.print()
            console.print(Rule(f"📌 Goal {i}/{len(goals)}", style="bold white"))

        run_planner(goal)

    console.print()
    console.print(Panel.fit(
        "[bold green]✅ Planning hoàn tất![/bold green]\n\n"
        "Planning pattern giúp:\n"
        "  📋 Plan DYNAMIC: tạo bước tùy theo yêu cầu\n"
        "  ⚙️  Execute tuần tự: mỗi bước dùng đúng tool\n"
        "  📊 Tổng hợp: kết quả nhiều nguồn → 1 báo cáo\n\n"
        "[dim]Tip: uv run python run.py \"Yêu cầu tùy chọn\"[/dim]",
        border_style="green", padding=(1, 2),
    ))


if __name__ == "__main__":
    main()
