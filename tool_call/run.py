"""
═══════════════════════════════════════════════════════════════════════
RUNNER — Chạy Smart Home Agent Demo
═══════════════════════════════════════════════════════════════════════

Usage:
    uv run python run.py              # Demo với kịch bản mẫu
    uv run python run.py --chat       # Chat tương tác
"""

import sys

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from agent import run_command
from smart_home import smart_home

console = Console()


# ═══════════════════════════════════════════════════════════════
# Demo Commands
# ═══════════════════════════════════════════════════════════════

DEMO_COMMANDS = [
    # ── Đơn giản: 1 tool call ────────────────────────────────
    {
        "command": "Tắt đèn phòng khách",
        "description": "Điều khiển đèn — 1 tool call",
    },
    {
        "command": "Xem trạng thái tất cả thiết bị trong phòng khách",
        "description": "Tra cứu trạng thái — get_device_status",
    },

    # ── Phức tạp hơn: nhiều params ───────────────────────────
    {
        "command": "Bật điều hòa phòng ngủ, đặt 22 độ chế độ cool",
        "description": "Điều khiển AC với nhiều tham số",
    },

    # ── Multi-tool: nhiều thiết bị cùng lúc ──────────────────
    {
        "command": "Mình đi ngủ rồi. Tắt đèn nhà bếp, tắt TV, và khóa cửa chính giúp mình.",
        "description": "Multi-tool call — 3 thiết bị cùng lúc",
    },

    # ── Ngữ cảnh: yêu cầu tự nhiên ──────────────────────────
    {
        "command": "Phát nhạc Lofi chill ở phòng khách, âm lượng nhỏ thôi khoảng 30%",
        "description": "Yêu cầu tự nhiên — agent cần hiểu ý",
    },
]


def run_demo():
    """Chạy demo với các lệnh mẫu."""

    console.print()
    console.print(Panel.fit(
        "[bold cyan]🏠 TOOL CALL PATTERN[/bold cyan]\n"
        "[dim]Smart Home Agent — Điều khiển nhà thông minh[/dim]\n\n"
        "Agent hiểu ngôn ngữ tự nhiên → gọi đúng tool:\n"
        "  💡 control_light    — Đèn\n"
        "  🌡️ control_ac       — Điều hòa\n"
        "  📺 control_tv       — TV\n"
        "  🔒 control_lock     — Khóa cửa\n"
        "  🎵 control_speaker  — Loa\n"
        "  📊 get_device_status — Xem trạng thái\n\n"
        "[dim]Flow: User nói → LLM hiểu → Tool call → Kết quả[/dim]",
        border_style="cyan", padding=(1, 3),
    ))

    # In trạng thái ban đầu
    console.print()
    console.print(Rule("🏠 Trạng thái ban đầu", style="dim"))
    smart_home.print_status()

    # Chạy từng command
    for i, demo in enumerate(DEMO_COMMANDS, 1):
        console.print()
        console.print(Rule(
            f"📌 Demo {i}/{len(DEMO_COMMANDS)}: {demo['description']}",
            style="bold white",
        ))
        run_command(demo["command"])
        console.print("─" * 70)

    # In trạng thái cuối
    console.print()
    console.print(Rule("🏠 Trạng thái sau khi chạy", style="bold cyan"))
    smart_home.print_status()

    # Action log
    if smart_home.action_log:
        console.print()
        console.print(Rule("📋 Action Log", style="dim"))
        for entry in smart_home.action_log:
            console.print(f"  • {entry}")

    console.print()
    console.print(Panel.fit(
        "[bold green]✅ Demo hoàn tất![/bold green]\n\n"
        f"Đã thực thi {len(DEMO_COMMANDS)} lệnh điều khiển nhà thông minh.\n"
        f"Tổng cộng {len(smart_home.action_log)} thay đổi thiết bị.",
        border_style="green", padding=(1, 2),
    ))


def run_interactive():
    """Chạy chế độ chat tương tác."""

    console.print()
    console.print(Panel.fit(
        "[bold cyan]🏠 SMART HOME CHAT[/bold cyan]\n"
        "[dim]Gõ 'status' để xem trạng thái, 'quit' để thoát[/dim]",
        border_style="cyan", padding=(0, 2),
    ))
    smart_home.print_status()

    while True:
        console.print()
        user_input = console.input("[bold cyan]🗣️ Bạn: [/bold cyan]")
        cmd = user_input.strip().lower()

        if cmd in ("quit", "exit", "q"):
            console.print("[dim]Tạm biệt! 👋[/dim]")
            break
        if cmd == "status":
            smart_home.print_status()
            continue
        if not cmd:
            continue

        run_command(user_input.strip())


def main():
    if "--chat" in sys.argv:
        run_interactive()
    else:
        run_demo()


if __name__ == "__main__":
    main()
