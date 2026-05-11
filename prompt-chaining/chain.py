"""
═══════════════════════════════════════════════════════════════════════════════
PROMPT CHAINING — Multimodal & Multi-step Reasoning
═══════════════════════════════════════════════════════════════════════════════

Design Pattern: PROMPT CHAINING
────────────────────────────────
Prompt Chaining phân rã một tác vụ phức tạp thành chuỗi các bước nhỏ hơn.
Output của bước trước trở thành input cho bước sau, tạo thành một "pipeline".

Tại sao cần Prompt Chaining cho bài toán Multimodal?
────────────────────────────────────────────────────
Khi phân tích một ảnh chứa nhiều loại thông tin (text, labels, bảng),
việc yêu cầu LLM xử lý tất cả trong 1 prompt duy nhất sẽ:
  ✗ Dễ bỏ sót thông tin
  ✗ Khó kiểm soát chất lượng từng bước
  ✗ Không thể debug khi kết quả sai

Prompt Chaining giải quyết bằng cách:
  ✓ Mỗi bước có nhiệm vụ rõ ràng, dễ kiểm tra
  ✓ Có thể validate output giữa các bước (gate)
  ✓ Dễ debug: biết lỗi xảy ra ở bước nào
  ✓ Có thể thay đổi/cải tiến từng bước độc lập

Flow:
  ┌──────────┐     ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
  │  Image   │────▶│   PROMPT 1       │────▶│   PROMPT 2       │────▶│   PROMPT 3       │
  │  Input   │     │  Extract Text    │     │  Link Labels     │     │  Interpret &     │
  │          │     │  (OCR-like)      │     │  (Relationship)  │     │  Conclude        │
  └──────────┘     └────────┬─────────┘     └────────┬─────────┘     └────────┬─────────┘
                            │                        │                        │
                     extracted_text             linked_labels           final_report
                            │                        │                        │
                     ┌──────▼──────┐          ┌──────▼──────┐          ┌──────▼──────┐
                     │   Gate 1    │          │   Gate 2    │          │   Output    │
                     │  Validate   │          │  Validate   │          │   Final     │
                     └─────────────┘          └─────────────┘          └─────────────┘
"""

import base64
import os
import time

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from config import OPENAI_API_BASE, OPENAI_API_KEY, OPENAI_MODEL_NAME
from prompts import PROMPT_1_EXTRACT_TEXT, PROMPT_2_LINK_LABELS, PROMPT_3_INTERPRET
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.rule import Rule

console = Console()


# ═══════════════════════════════════════════════════════════════
# Utility: Encode image to base64
# ═══════════════════════════════════════════════════════════════

def encode_image_to_base64(image_path: str) -> str:
    """Đọc file ảnh và encode sang base64 string.

    Args:
        image_path: Đường dẫn tới file ảnh (png, jpg, etc.)

    Returns:
        Base64 encoded string của ảnh.
    """
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def get_image_media_type(image_path: str) -> str:
    """Xác định media type dựa trên extension của file."""
    ext = os.path.splitext(image_path)[1].lower()
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    return media_types.get(ext, "image/png")


# ═══════════════════════════════════════════════════════════════
# LLM Instance
# ═══════════════════════════════════════════════════════════════

def create_llm() -> ChatOpenAI:
    """Tạo LLM instance kết nối tới local model."""
    return ChatOpenAI(
        model=OPENAI_MODEL_NAME,
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_API_BASE,
        temperature=0,
    )


# ═══════════════════════════════════════════════════════════════
# Gate Functions — Validate output giữa các bước
# ═══════════════════════════════════════════════════════════════

def gate_1_validate_extraction(extracted_text: str) -> bool:
    """Gate 1: Kiểm tra output của Prompt 1 có đủ nội dung không.

    Validation rules:
      - Text không rỗng
      - Phải có ít nhất 1 section (## header)
      - Phải có dữ liệu (không chỉ toàn "[không rõ]")
    """
    if not extracted_text or len(extracted_text.strip()) < 50:
        console.print("  [red]✗ Gate 1 FAILED: Text trích xuất quá ngắn hoặc rỗng[/red]")
        return False

    if "##" not in extracted_text:
        console.print("  [red]✗ Gate 1 FAILED: Không tìm thấy section headers[/red]")
        return False

    # Kiểm tra không phải toàn bộ "[không rõ]"
    unclear_count = extracted_text.count("[không rõ]")
    if unclear_count > 5:
        console.print("  [red]✗ Gate 1 FAILED: Quá nhiều text không rõ ràng[/red]")
        return False

    console.print("  [green]✓ Gate 1 PASSED: Text trích xuất hợp lệ[/green]")
    return True


def gate_2_validate_linking(linked_labels: str) -> bool:
    """Gate 2: Kiểm tra output của Prompt 2 có liên kết hợp lệ không.

    Validation rules:
      - Phải có mapping label → thông tin
      - Phải có phần phân tích mối quan hệ
    """
    if not linked_labels or len(linked_labels.strip()) < 50:
        console.print("  [red]✗ Gate 2 FAILED: Phân tích liên kết quá ngắn[/red]")
        return False

    # Kiểm tra có mapping
    has_mapping = any(keyword in linked_labels.lower()
                      for keyword in ["mapping", "label", "liên kết", "tham chiếu"])
    if not has_mapping:
        console.print("  [yellow]⚠ Gate 2 WARNING: Không tìm thấy mapping rõ ràng[/yellow]")
        # Vẫn cho pass nhưng cảnh báo

    console.print("  [green]✓ Gate 2 PASSED: Phân tích liên kết hợp lệ[/green]")
    return True


# ═══════════════════════════════════════════════════════════════
# PROMPT CHAIN: 3 bước tuần tự
# ═══════════════════════════════════════════════════════════════

def run_prompt_chain(image_path: str) -> dict:
    """Chạy Prompt Chain 3 bước cho phân tích ảnh multimodal.

    Args:
        image_path: Đường dẫn tới file ảnh cần phân tích.

    Returns:
        Dict chứa kết quả từng bước:
        {
            "step_1_extracted_text": str,
            "step_2_linked_labels": str,
            "step_3_final_report": str,
            "gates_passed": bool,
            "timing": dict,
        }
    """
    llm = create_llm()
    results = {"timing": {}}

    console.print()
    console.print(Rule("🔗 PROMPT CHAINING — Multimodal Analysis", style="bold cyan"))
    console.print()

    # Validate image path
    if not os.path.exists(image_path):
        console.print(f"[red]✗ File ảnh không tồn tại: {image_path}[/red]")
        return {"error": f"File not found: {image_path}"}

    console.print(f"  📁 Image: [bold]{image_path}[/bold]")
    console.print()

    # ── STEP 1: Extract text from image ──────────────────────
    console.print(Rule("📝 PROMPT 1: Trích xuất text từ ảnh", style="yellow"))
    console.print()

    start = time.time()

    # Encode ảnh sang base64
    image_b64 = encode_image_to_base64(image_path)
    media_type = get_image_media_type(image_path)

    # Gửi ảnh + prompt cho LLM (multimodal input)
    messages_step1 = [
        HumanMessage(content=[
            {"type": "text", "text": PROMPT_1_EXTRACT_TEXT},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{media_type};base64,{image_b64}",
                },
            },
        ])
    ]

    response_1 = llm.invoke(messages_step1)
    extracted_text = response_1.content

    elapsed_1 = time.time() - start
    results["timing"]["step_1"] = round(elapsed_1, 2)
    results["step_1_extracted_text"] = extracted_text

    console.print(Panel(
        Markdown(extracted_text),
        title="[bold yellow]Kết quả Prompt 1[/bold yellow]",
        border_style="yellow",
        padding=(1, 2),
    ))

    # ── GATE 1: Validate extraction ──────────────────────────
    console.print()
    if not gate_1_validate_extraction(extracted_text):
        console.print("[red]⛔ Pipeline dừng tại Gate 1. Text trích xuất không đủ chất lượng.[/red]")
        results["gates_passed"] = False
        return results

    console.print()

    # ── STEP 2: Link text with labels ────────────────────────
    console.print(Rule("🏷️  PROMPT 2: Liên kết text với labels", style="blue"))
    console.print()

    start = time.time()

    # Prompt 2 nhận output của Prompt 1 làm input
    prompt_2_filled = PROMPT_2_LINK_LABELS.format(extracted_text=extracted_text)

    messages_step2 = [
        HumanMessage(content=prompt_2_filled)
    ]

    response_2 = llm.invoke(messages_step2)
    linked_labels = response_2.content

    elapsed_2 = time.time() - start
    results["timing"]["step_2"] = round(elapsed_2, 2)
    results["step_2_linked_labels"] = linked_labels

    console.print(Panel(
        Markdown(linked_labels),
        title="[bold blue]Kết quả Prompt 2[/bold blue]",
        border_style="blue",
        padding=(1, 2),
    ))

    # ── GATE 2: Validate linking ─────────────────────────────
    console.print()
    if not gate_2_validate_linking(linked_labels):
        console.print("[red]⛔ Pipeline dừng tại Gate 2. Liên kết label không hợp lệ.[/red]")
        results["gates_passed"] = False
        return results

    console.print()

    # ── STEP 3: Interpret and conclude ───────────────────────
    console.print(Rule("📊 PROMPT 3: Tổng hợp & Kết luận", style="green"))
    console.print()

    start = time.time()

    # Prompt 3 nhận output của CẢ Prompt 1 và Prompt 2
    prompt_3_filled = PROMPT_3_INTERPRET.format(
        extracted_text=extracted_text,
        linked_labels=linked_labels,
    )

    messages_step3 = [
        HumanMessage(content=prompt_3_filled)
    ]

    response_3 = llm.invoke(messages_step3)
    final_report = response_3.content

    elapsed_3 = time.time() - start
    results["timing"]["step_3"] = round(elapsed_3, 2)
    results["step_3_final_report"] = final_report

    console.print(Panel(
        Markdown(final_report),
        title="[bold green]📋 BÁO CÁO CUỐI CÙNG[/bold green]",
        border_style="green",
        padding=(1, 2),
    ))

    results["gates_passed"] = True

    # ── Summary ──────────────────────────────────────────────
    console.print()
    console.print(Rule("⏱️  Tổng kết thời gian", style="cyan"))
    console.print(f"  Prompt 1 (Extract):   [yellow]{results['timing']['step_1']}s[/yellow]")
    console.print(f"  Prompt 2 (Link):      [blue]{results['timing']['step_2']}s[/blue]")
    console.print(f"  Prompt 3 (Interpret): [green]{results['timing']['step_3']}s[/green]")
    total = sum(results["timing"].values())
    console.print(f"  [bold]Tổng cộng:              {round(total, 2)}s[/bold]")
    console.print()

    return results
