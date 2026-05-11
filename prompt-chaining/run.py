"""
═══════════════════════════════════════════════════════════════════════
RUNNER — Chạy Prompt Chaining pipeline
═══════════════════════════════════════════════════════════════════════

Usage:
    uv run python run.py                           # Dùng ảnh mặc định
    uv run python run.py path/to/your/image.png    # Dùng ảnh tùy chọn
"""

import sys
import os

from rich.console import Console
from rich.panel import Panel

from chain import run_prompt_chain

console = Console()


def main():
    """Entry point — chạy prompt chain với ảnh mẫu hoặc ảnh user cung cấp."""

    console.print()
    console.print(Panel.fit(
        "[bold cyan]🔗 PROMPT CHAINING PATTERN[/bold cyan]\n"
        "[dim]Multimodal & Multi-step Reasoning Demo[/dim]\n\n"
        "Phân tích ảnh chứa nhiều loại thông tin:\n"
        "  📝 Text nhúng trong ảnh\n"
        "  🏷️  Labels chỉ tới các vùng cụ thể\n"
        "  📊 Bảng dữ liệu giải thích từng label\n\n"
        "[dim]Pipeline: Extract → Link → Interpret[/dim]",
        border_style="cyan",
        padding=(1, 3),
    ))
    console.print()

    # Xác định ảnh đầu vào
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        # Dùng ảnh mẫu mặc định
        image_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "sample_images",
            "patient_report.png",
        )

    if not os.path.exists(image_path):
        console.print(f"[red]✗ Không tìm thấy file ảnh: {image_path}[/red]")
        console.print("[dim]Usage: uv run python run.py [path/to/image.png][/dim]")
        sys.exit(1)

    console.print(f"  🖼️  Ảnh đầu vào: [bold]{os.path.basename(image_path)}[/bold]")
    console.print()

    # Chạy prompt chain
    results = run_prompt_chain(image_path)

    # Kết quả cuối cùng
    if results.get("gates_passed"):
        console.print(Panel.fit(
            "[bold green]✅ Pipeline hoàn tất thành công![/bold green]\n"
            "Tất cả 3 prompts đã được thực thi và gates đều pass.",
            border_style="green",
        ))
    elif "error" in results:
        console.print(Panel.fit(
            f"[bold red]❌ Lỗi: {results['error']}[/bold red]",
            border_style="red",
        ))
    else:
        console.print(Panel.fit(
            "[bold yellow]⚠️ Pipeline dừng sớm — không qua được gate validation.[/bold yellow]",
            border_style="yellow",
        ))


if __name__ == "__main__":
    main()
