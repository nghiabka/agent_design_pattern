"""
Runner for the Deep Research with Reflection demo.

Usage:
    uv run python run.py
    uv run python run.py "LangGraph memory checkpoint hoạt động thế nào?"
    uv run python run.py --loops 3 --queries 4 "So sánh LangGraph và CrewAI"
"""

import argparse

from rich.console import Console
from rich.panel import Panel

from config import INITIAL_SEARCH_QUERY_COUNT, MAX_RESEARCH_LOOPS
from deep_research import run_deep_research

console = Console()

DEFAULT_QUESTION = (
    "LangGraph được dùng như thế nào để xây dựng agent Deep Research "
    "có vòng lặp tìm kiếm và phản tư?"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Deep Research LangGraph demo with reflection loop.",
    )
    parser.add_argument(
        "question",
        nargs="*",
        help="Câu hỏi nghiên cứu. Nếu bỏ trống sẽ dùng câu hỏi demo.",
    )
    parser.add_argument(
        "--queries",
        type=int,
        default=INITIAL_SEARCH_QUERY_COUNT,
        help="Số truy vấn tìm kiếm ban đầu.",
    )
    parser.add_argument(
        "--loops",
        type=int,
        default=MAX_RESEARCH_LOOPS,
        help="Số vòng reflection/search tối đa.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    question = " ".join(args.question).strip() or DEFAULT_QUESTION

    console.print()
    console.print(Panel.fit(
        "[bold cyan]DEEP RESEARCH WITH REFLECTION[/bold cyan]\n"
        "[dim]LangGraph StateGraph: query -> web search -> reflection loop -> final answer[/dim]\n\n"
        f"[bold]Question:[/bold] {question}\n"
        f"[bold]Initial queries:[/bold] {args.queries}\n"
        f"[bold]Max research loops:[/bold] {args.loops}",
        border_style="cyan",
        padding=(1, 3),
    ))

    result = run_deep_research(
        question=question,
        initial_search_query_count=args.queries,
        max_research_loops=args.loops,
    )

    console.print()
    console.print(Panel.fit(
        "[bold green]Hoàn tất[/bold green]\n\n"
        f"Đã chạy {len(result.get('search_queries', []))} truy vấn.\n"
        f"Đã thu thập {len(result.get('sources_gathered', []))} source.\n"
        f"Reflection loops: {result.get('research_loop_count', 0)}",
        border_style="green",
        padding=(1, 2),
    ))


if __name__ == "__main__":
    main()
