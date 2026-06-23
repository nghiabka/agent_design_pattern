"""
═══════════════════════════════════════════════════════════════════════
RUNNER — Gemini Enterprise Agentic RAG Demo
═══════════════════════════════════════════════════════════════════════

Usage:
    uv run python run.py
    uv run python run.py "Server nào có incident nhiều nhất? Ai phụ trách?"
    uv run python run.py --chat
"""

import sys
from uuid import uuid4

from openai import OpenAIError
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

from gemini_rag.documents import ALL_CORPORA, ALL_DOCUMENTS
from gemini_rag.service import run_question

console = Console()


DEMO_QUESTIONS = [
    {
        "question": "Server nào có incident nhiều nhất tháng trước? Ai phụ trách server đó?",
        "description": "Multi-hop: infra (incident log) → hr (nhân viên phụ trách)",
        "expected_hops": ["infra", "hr"],
    },
    {
        "question": "Chi phí vận hành DC Hà Nội Q1/2025 có vượt budget không? Nếu vượt thì do nguyên nhân gì?",
        "description": "Multi-hop: finance (expenses + budget) → infra (sự cố gây chi phí)",
        "expected_hops": ["finance", "infra"],
    },
    {
        "question": "Team nào đang overload nhất? Có dự án nào sắp deadline có blocker không?",
        "description": "Multi-hop: projects (workload + milestones) → hr (team info)",
        "expected_hops": ["projects", "hr"],
    },
]


def print_intro() -> None:
    # Build corpus summary
    corpus_lines = []
    for name, corpus in ALL_CORPORA.items():
        corpus_lines.append(f"  📁 [cyan]{name}[/cyan] — {len(corpus.documents)} docs")

    console.print()
    console.print(Panel.fit(
        "[bold cyan]🏢 GEMINI ENTERPRISE AGENTIC RAG[/bold cyan]\n"
        "[dim]5-Agent Cross-Corpus Retrieval Pattern[/dim]\n\n"
        "Agents:\n"
        "  🎯 Orchestrator → 📋 Planning → ✏️ Query Rewriter\n"
        "  → 🔎 Search Fanout → 🔍 Sufficient Context → 🧾 Answer\n\n"
        f"Knowledge Base — TechVN IT Helpdesk:\n"
        + "\n".join(corpus_lines) + "\n"
        f"  📚 {len(ALL_DOCUMENTS)} documents total\n\n"
        "[dim]Demo multi-hop queries across data islands.[/dim]",
        border_style="cyan",
        padding=(1, 3),
    ))


def run_demo() -> None:
    print_intro()
    session_id = f"demo-{uuid4().hex}"

    for idx, item in enumerate(DEMO_QUESTIONS, 1):
        console.print()
        console.print(Rule(
            f"📌 Demo {idx}/{len(DEMO_QUESTIONS)}: {item['description']}",
            style="bold white",
        ))
        console.print(f"  Expected hops: {' → '.join(item['expected_hops'])}")
        run_question(item["question"], session_id=session_id)
        console.print("─" * 80)

    console.print()
    console.print(Panel.fit(
        "[bold green]✅ Demo hoàn tất![/bold green]\n"
        "5 agents đã phối hợp: orchestrate → plan → rewrite → search → sufficiency check → answer.",
        border_style="green",
        padding=(1, 2),
    ))


def run_interactive() -> None:
    print_intro()
    session_id = f"chat-{uuid4().hex}"
    console.print(Panel.fit(
        "[bold cyan]CROSS-CORPUS RAG CHAT[/bold cyan]\n"
        "[dim]Gõ 'corpora' để xem KB, 'quit' để thoát[/dim]",
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
        if cmd == "corpora":
            table = Table(title="Knowledge Base Corpora", border_style="cyan", show_lines=True)
            table.add_column("Corpus", style="bold cyan", width=12)
            table.add_column("Docs", justify="right", width=6)
            table.add_column("Description", width=60)
            for name, corpus in ALL_CORPORA.items():
                table.add_row(name, str(len(corpus.documents)), corpus.description[:80])
            console.print(table)
            continue
        if not user_input.strip():
            continue

        try:
            run_question(user_input.strip(), session_id=session_id)
        except OpenAIError as exc:
            console.print(Panel(
                f"Không gọi được model sau nhiều lần thử:\n{exc}",
                title="[bold red]MODEL ERROR[/bold red]",
                border_style="red",
                padding=(0, 1),
            ))


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
