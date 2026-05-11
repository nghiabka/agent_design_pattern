"""
═══════════════════════════════════════════════════════════════════════════════
PARALLEL GENERATOR — A/B Testing với Parallelization Pattern
═══════════════════════════════════════════════════════════════════════════════

Design Pattern: PARALLELIZATION (A/B Testing)
──────────────────────────────────────────────
Thay vì chạy tuần tự (A → B → C), pattern này chạy ĐỒNG THỜI
nhiều LLM calls cùng lúc, sau đó so sánh và chọn kết quả tốt nhất.

Tại sao Parallelization?
─────────────────────────
  ✗ Tuần tự:  A(5s) → B(5s) → C(5s) = 15s tổng
  ✓ Song song: A(5s) | B(5s) | C(5s) = 5s tổng (3x nhanh hơn!)

Flow:
                         ┌──────────────────┐
                         │   User Input     │
                         │  (Topic/Article) │
                         └────────┬─────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
           ┌───────▼──────┐ ┌────▼───────┐ ┌───▼────────┐
           │  VARIANT A   │ │ VARIANT B  │ │ VARIANT C  │
           │  Creative /  │ │ Professional│ │ Storytelling│
           │  Curious     │ │ / Authorit.│ │ / Emotional│
           │  temp=0.9    │ │ temp=0.3   │ │ temp=0.7   │
           └───────┬──────┘ └────┬───────┘ └───┬────────┘
                    │             │             │
                    └─────────────┼─────────────┘
                                  │  (all results)
                         ┌────────▼─────────┐
                         │   EVALUATOR      │
                         │  (Compare &      │
                         │   Select Best)   │
                         └────────┬─────────┘
                                  │
                         ┌────────▼─────────┐
                         │  🏆 Best Option  │
                         └──────────────────┘

Key concepts:
  • asyncio.gather() — Chạy 3 LLM calls đồng thời
  • Mỗi variant dùng prompt KHÁC NHAU + temperature KHÁC NHAU
  • Evaluator so sánh kết quả và chọn best option
  • Tổng thời gian ≈ max(variant_times) thay vì sum(variant_times)
"""

import asyncio
import time

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from config import OPENAI_API_BASE, OPENAI_API_KEY, OPENAI_MODEL_NAME
from prompts import VARIANTS, EVALUATOR_PROMPT
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.rule import Rule
from rich.table import Table
from rich.live import Live

console = Console()


# ═══════════════════════════════════════════════════════════════
# LLM Factory — Tạo LLM với temperature tùy chỉnh
# ═══════════════════════════════════════════════════════════════

def create_llm(temperature: float = 0) -> ChatOpenAI:
    """Tạo LLM instance với temperature tùy chỉnh.

    Mỗi variant dùng temperature khác nhau:
      - Variant A (sáng tạo):    temp=0.9 → đa dạng, bất ngờ
      - Variant B (chuyên nghiệp): temp=0.3 → ổn định, chính xác
      - Variant C (storytelling):  temp=0.7 → cân bằng
    """
    return ChatOpenAI(
        model=OPENAI_MODEL_NAME,
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_API_BASE,
        temperature=temperature,
        extra_body={
            "chat_template_kwargs": {"enable_thinking": False},
        },
    )


# ═══════════════════════════════════════════════════════════════
# Single Variant Generator (async)
# ═══════════════════════════════════════════════════════════════

async def generate_variant(
    topic: str,
    variant: dict,
) -> dict:
    """Tạo 1 tiêu đề variant (async — chạy song song được).

    Args:
        topic: Chủ đề bài viết.
        variant: Dict chứa name, label, prompt, temperature.

    Returns:
        Dict chứa kết quả: name, label, headline, elapsed.
    """
    name = variant["name"]
    label = variant["label"]
    prompt_template = variant["prompt"]
    temperature = variant["temperature"]

    console.print(f"  🚀 [{name}] Bắt đầu generate — [dim]{label} (temp={temperature})[/dim]")

    start = time.time()

    llm = create_llm(temperature=temperature)
    prompt_filled = prompt_template.format(topic=topic)

    # ainvoke cho async call
    response = await llm.ainvoke([HumanMessage(content=prompt_filled)])
    headline = response.content.strip().strip('"').strip("'")

    elapsed = round(time.time() - start, 2)
    console.print(f"  ✅ [{name}] Hoàn tất trong {elapsed}s")

    return {
        "name": name,
        "label": label,
        "headline": headline,
        "elapsed": elapsed,
    }


# ═══════════════════════════════════════════════════════════════
# Parallel Generator — Chạy tất cả variants đồng thời
# ═══════════════════════════════════════════════════════════════

async def generate_all_variants(topic: str) -> list[dict]:
    """Chạy SONG SONG tất cả variants bằng asyncio.gather().

    Đây là core của Parallelization pattern:
    Thay vì gọi tuần tự A → B → C, ta gọi A | B | C cùng lúc.

    Args:
        topic: Chủ đề bài viết.

    Returns:
        List[dict] — Kết quả từ tất cả variants.
    """
    console.print()
    console.print(Rule("⚡ PARALLEL GENERATION — 3 Variants đồng thời", style="bold yellow"))
    console.print()

    start_total = time.time()

    # ── asyncio.gather() = PARALLEL execution ─────────────────
    # Tất cả coroutines được schedule cùng lúc
    # gather() chờ TẤT CẢ hoàn tất rồi trả về list kết quả
    results = await asyncio.gather(
        generate_variant(topic, VARIANTS[0]),  # Variant A
        generate_variant(topic, VARIANTS[1]),  # Variant B
        generate_variant(topic, VARIANTS[2]),  # Variant C
    )

    total_elapsed = round(time.time() - start_total, 2)

    # ── Hiển thị kết quả ──────────────────────────────────────
    console.print()

    table = Table(
        title="📊 Kết quả Generation",
        border_style="yellow",
        show_lines=True,
    )
    table.add_column("Variant", style="bold", width=8)
    table.add_column("Style", style="dim", width=25)
    table.add_column("Tiêu đề", style="white", min_width=40)
    table.add_column("Thời gian", style="cyan", width=10)

    for r in results:
        table.add_row(
            f"[{r['name']}]",
            r["label"],
            r["headline"],
            f"{r['elapsed']}s",
        )

    console.print(table)
    console.print()

    # ── So sánh tuần tự vs song song ─────────────────────────
    sequential_time = sum(r["elapsed"] for r in results)
    speedup = round(sequential_time / total_elapsed, 1) if total_elapsed > 0 else 0

    console.print(f"  ⏱️  Thời gian song song:  [bold green]{total_elapsed}s[/bold green]")
    console.print(f"  ⏱️  Nếu chạy tuần tự:    [dim]{round(sequential_time, 2)}s[/dim]")
    console.print(f"  🚀 Speedup:              [bold cyan]{speedup}x nhanh hơn![/bold cyan]")

    return results


# ═══════════════════════════════════════════════════════════════
# Evaluator — So sánh và chọn best option
# ═══════════════════════════════════════════════════════════════

async def evaluate_options(topic: str, results: list[dict]) -> str:
    """Đánh giá tất cả variants và chọn tiêu đề tốt nhất.

    Evaluator LLM nhìn vào tất cả tiêu đề đã generate,
    đánh giá theo tiêu chí, và chọn winner.

    Args:
        topic: Chủ đề bài viết.
        results: List kết quả từ parallel generation.

    Returns:
        Evaluation report (markdown).
    """
    console.print()
    console.print(Rule("🏆 EVALUATOR — Đánh giá & Chọn Best Option", style="bold green"))
    console.print()

    start = time.time()

    # Fill evaluator prompt
    prompt_filled = EVALUATOR_PROMPT.format(
        topic=topic,
        headline_a=results[0]["headline"],
        headline_b=results[1]["headline"],
        headline_c=results[2]["headline"],
    )

    llm = create_llm(temperature=0)  # Evaluator dùng temp=0 cho nhất quán
    response = await llm.ainvoke([HumanMessage(content=prompt_filled)])

    elapsed = round(time.time() - start, 2)
    evaluation = response.content

    console.print(Panel(
        Markdown(evaluation),
        title="[bold green]📋 BÁO CÁO ĐÁNH GIÁ[/bold green]",
        border_style="green",
        padding=(1, 2),
    ))
    console.print(f"  ⏱️  Thời gian đánh giá: [dim]{elapsed}s[/dim]")

    return evaluation


# ═══════════════════════════════════════════════════════════════
# Full Pipeline: Parallel Generate → Evaluate → Select Best
# ═══════════════════════════════════════════════════════════════

async def run_ab_testing(topic: str) -> dict:
    """Chạy toàn bộ pipeline A/B Testing.

    Pipeline:
      1. Parallel Generate: 3 variants chạy đồng thời
      2. Evaluate: So sánh và chấm điểm
      3. Select: Chọn best option

    Args:
        topic: Chủ đề bài viết.

    Returns:
        Dict chứa kết quả toàn bộ pipeline.
    """
    console.print()
    console.print(Rule("🔄 PARALLELIZATION — A/B Testing Pipeline", style="bold cyan"))
    console.print()
    console.print(f"  📝 Chủ đề: [bold]{topic}[/bold]")

    pipeline_start = time.time()

    # ── STEP 1: Parallel Generation ──────────────────────────
    results = await generate_all_variants(topic)

    # ── STEP 2: Evaluation ────────────────────────────────────
    evaluation = await evaluate_options(topic, results)

    pipeline_elapsed = round(time.time() - pipeline_start, 2)

    # ── Summary ──────────────────────────────────────────────
    console.print()
    console.print(Rule("⏱️  Tổng kết Pipeline", style="cyan"))
    console.print(f"  Parallel Generation:  [yellow]{max(r['elapsed'] for r in results)}s[/yellow] (3 variants)")
    console.print(f"  Evaluation:           [green]{pipeline_elapsed - max(r['elapsed'] for r in results):.2f}s[/green]")
    console.print(f"  [bold]Tổng cộng:              {pipeline_elapsed}s[/bold]")
    console.print()

    return {
        "topic": topic,
        "variants": results,
        "evaluation": evaluation,
        "total_time": pipeline_elapsed,
    }
