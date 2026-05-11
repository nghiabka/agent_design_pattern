"""
═══════════════════════════════════════════════════════════════════════
IMAGE GENERATOR — Simulated Image Generation Tool
═══════════════════════════════════════════════════════════════════════

Mô phỏng API tạo ảnh (như DALL-E, Stable Diffusion).
Tạo ảnh nghệ thuật placeholder với metadata từ prompt.

Trong production, đây sẽ gọi tới API thật:
  • OpenAI DALL-E
  • Stable Diffusion API
  • Midjourney API
"""

import os
import hashlib
import math
import random
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont
from langchain_core.tools import tool
from config import OUTPUT_DIR


def _create_art_image(prompt: str, style: str, filename: str) -> str:
    """Tạo ảnh nghệ thuật procedural dựa trên prompt.

    Sử dụng Pillow để vẽ ảnh với màu sắc và pattern
    được sinh từ hash của prompt — mỗi prompt cho 1 ảnh unique.
    """
    width, height = 1024, 1024
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    # Dùng hash prompt để tạo seed → ảnh deterministic theo prompt
    seed = int(hashlib.md5(prompt.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)

    # Palette màu dựa theo style
    palettes = {
        "impressionist": [(70, 130, 180), (255, 200, 100), (144, 238, 144), (255, 160, 122), (221, 160, 221)],
        "cyberpunk": [(0, 255, 255), (255, 0, 255), (0, 0, 40), (138, 43, 226), (255, 105, 180)],
        "watercolor": [(173, 216, 230), (255, 218, 185), (221, 160, 221), (152, 251, 152), (255, 250, 205)],
        "abstract": [(255, 87, 51), (255, 189, 51), (51, 255, 87), (51, 189, 255), (189, 51, 255)],
        "surrealist": [(255, 127, 80), (70, 130, 180), (255, 215, 0), (50, 50, 50), (220, 220, 220)],
        "default": [(100, 149, 237), (255, 182, 193), (144, 238, 144), (255, 218, 185), (230, 230, 250)],
    }
    colors = palettes.get(style.lower(), palettes["default"])

    # ── Background gradient ───────────────────────────────────
    c1 = rng.choice(colors)
    c2 = rng.choice(colors)
    for y in range(height):
        ratio = y / height
        r = int(c1[0] * (1 - ratio) + c2[0] * ratio)
        g = int(c1[1] * (1 - ratio) + c2[1] * ratio)
        b = int(c1[2] * (1 - ratio) + c2[2] * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # ── Geometric shapes (nghệ thuật trừu tượng) ─────────────
    for _ in range(rng.randint(15, 40)):
        shape_type = rng.choice(["circle", "rect", "line", "arc"])
        color = rng.choice(colors)
        alpha_color = color + (rng.randint(80, 200),)

        # Tạo overlay có alpha
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)

        x1 = rng.randint(0, width)
        y1 = rng.randint(0, height)
        size = rng.randint(30, 300)

        if shape_type == "circle":
            overlay_draw.ellipse([x1, y1, x1 + size, y1 + size], fill=alpha_color)
        elif shape_type == "rect":
            overlay_draw.rectangle([x1, y1, x1 + size, y1 + size // 2], fill=alpha_color)
        elif shape_type == "line":
            x2 = rng.randint(0, width)
            y2 = rng.randint(0, height)
            overlay_draw.line([(x1, y1), (x2, y2)], fill=color, width=rng.randint(2, 8))
        elif shape_type == "arc":
            overlay_draw.arc(
                [x1, y1, x1 + size, y1 + size],
                start=rng.randint(0, 180),
                end=rng.randint(180, 360),
                fill=color,
                width=rng.randint(2, 6),
            )

        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(img)

    # ── Thêm text metadata lên ảnh ────────────────────────────
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except OSError:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Banner ở dưới
    draw.rectangle([0, height - 80, width, height], fill=(0, 0, 0, 180))
    draw.text((20, height - 70), f"🎨 Style: {style}", fill="white", font=font_large)
    prompt_short = prompt[:80] + "..." if len(prompt) > 80 else prompt
    draw.text((20, height - 40), f"Prompt: {prompt_short}", fill=(200, 200, 200), font=font_small)

    # ── Lưu file ──────────────────────────────────────────────
    filepath = os.path.join(OUTPUT_DIR, filename)
    img.save(filepath, "PNG")

    return filepath


@tool
def generate_image(prompt: str, style: str = "default", filename: str = "") -> str:
    """Tạo ảnh nghệ thuật từ prompt mô tả.

    Đây là tool CHÍNH mà ImageGen Agent sử dụng.
    Mô phỏng API tạo ảnh (DALL-E / Stable Diffusion).

    Args:
        prompt: Mô tả chi tiết hình ảnh cần tạo (tiếng Anh hoặc tiếng Việt).
        style: Phong cách nghệ thuật — "impressionist", "cyberpunk",
               "watercolor", "abstract", "surrealist", hoặc "default".
        filename: Tên file output (tùy chọn, sẽ tự tạo nếu bỏ trống).

    Returns:
        Đường dẫn file ảnh đã tạo + metadata.
    """
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = hashlib.md5(prompt.encode()).hexdigest()[:8]
        filename = f"art_{safe_name}_{timestamp}.png"

    filepath = _create_art_image(prompt, style, filename)
    filesize = os.path.getsize(filepath)

    return (
        f"🎨 ẢNH ĐÃ ĐƯỢC TẠO THÀNH CÔNG!\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  📁 File: {filepath}\n"
        f"  📐 Kích thước: 1024×1024 px\n"
        f"  📦 Dung lượng: {filesize // 1024} KB\n"
        f"  🎭 Style: {style}\n"
        f"  📝 Prompt: {prompt[:100]}...\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  ✅ Ảnh đã sẵn sàng tại: {filepath}"
    )
