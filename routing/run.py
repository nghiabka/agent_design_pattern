"""
═══════════════════════════════════════════════════════════════════════
RUNNER — Chạy Coordinator Routing Agent
═══════════════════════════════════════════════════════════════════════

Demo chạy Coordinator với nhiều loại yêu cầu khác nhau
để showcase routing logic delegate tới đúng sub-agent.

Usage:
    uv run python run.py
"""

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from coordinator import run_coordinator

console = Console()


# ═══════════════════════════════════════════════════════════════
# Demo Requests — Các yêu cầu mẫu
# ═══════════════════════════════════════════════════════════════

DEMO_REQUESTS = [
    # ── Booking requests → Booker agent ──────────────────────
    {
        "message": "Tôi muốn đặt vé máy bay đi Tokyo ngày 15/06/2025 cho 2 người",
        "expected_route": "booker",
        "description": "Đặt vé máy bay",
    },
    {
        "message": "Đặt phòng khách sạn ở Bangkok 3 đêm từ ngày 20/07",
        "expected_route": "booker",
        "description": "Đặt phòng khách sạn",
    },

    # ── Info requests → Info agent ────────────────────────────
    {
        "message": "Thời tiết ở Singapore tuần này thế nào?",
        "expected_route": "info",
        "description": "Tra cứu thời tiết",
    },
    {
        "message": "Tôi cần thông tin visa du lịch Nhật Bản",
        "expected_route": "info",
        "description": "Thông tin visa",
    },

    # ── Unclear requests → Unclear agent ─────────────────────
    {
        "message": "Xin chào, bạn là ai?",
        "expected_route": "unclear",
        "description": "Yêu cầu không rõ ràng",
    },
]


def main():
    """Entry point — chạy demo Coordinator Routing."""

    console.print()
    console.print(Panel.fit(
        "[bold cyan]🔀 ROUTING PATTERN[/bold cyan]\n"
        "[dim]Coordinator Agent Delegation Demo[/dim]\n\n"
        "Coordinator phân loại yêu cầu user và delegate tới:\n"
        "  ✈️  [yellow]Booker[/yellow]  — Đặt vé máy bay, khách sạn\n"
        "  ℹ️  [blue]Info[/blue]     — Tra cứu thời tiết, visa, điểm tham quan\n"
        "  🤔 [red]Unclear[/red]  — Yêu cầu không rõ ràng\n\n"
        "[dim]Flow: User → Coordinator → Route → Sub-Agent → Response[/dim]",
        border_style="cyan",
        padding=(1, 3),
    ))

    # ── Chạy từng demo request ────────────────────────────────
    for i, demo in enumerate(DEMO_REQUESTS, 1):
        console.print()
        console.print(Rule(
            f"📌 Demo {i}/{len(DEMO_REQUESTS)}: {demo['description']}",
            style="bold white",
        ))
        console.print(f"  [dim]Expected route: {demo['expected_route']}[/dim]")

        response = run_coordinator(demo["message"])

        console.print()
        console.print("─" * 70)

    # ── Tổng kết ──────────────────────────────────────────────
    console.print()
    console.print(Panel.fit(
        "[bold green]✅ Demo hoàn tất![/bold green]\n\n"
        f"Đã chạy {len(DEMO_REQUESTS)} requests qua Coordinator:\n"
        f"  • Booking requests → [yellow]Booker Agent[/yellow]\n"
        f"  • Info requests    → [blue]Info Agent[/blue]\n"
        f"  • Unclear requests → [red]Unclear Agent[/red]",
        border_style="green",
        padding=(1, 2),
    ))


if __name__ == "__main__":
    main()
