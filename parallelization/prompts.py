"""
═══════════════════════════════════════════════════════════════════════
PROMPT TEMPLATES — Các prompt biến thể cho parallel generation
═══════════════════════════════════════════════════════════════════════

Mỗi variant sử dụng một style/approach khác nhau để tạo ra
output đa dạng. Đây là core của A/B Testing:
  → Cùng 1 input, nhưng prompts khác nhau → outputs khác nhau → chọn best.
"""

# ═══════════════════════════════════════════════════════════════
# VARIANT A: Phong cách sáng tạo, gây tò mò
# ═══════════════════════════════════════════════════════════════

VARIANT_A_PROMPT = """Bạn là một copywriter sáng tạo chuyên viết tiêu đề gây TÒ MÒ.

Phong cách của bạn:
  • Sử dụng câu hỏi hoặc mở đầu bất ngờ
  • Tạo sự tò mò, khiến người đọc MUỐN click
  • Dùng ngôn ngữ mạnh mẽ, gợi cảm xúc
  • Có thể dùng số liệu gây shock

Nhiệm vụ: Viết 1 tiêu đề cho bài viết về chủ đề sau.

Chủ đề: {topic}

Yêu cầu:
  - CHỈ trả về ĐÚNG 1 tiêu đề (không giải thích)
  - Tối đa 15 từ
  - Tiếng Việt
"""

# ═══════════════════════════════════════════════════════════════
# VARIANT B: Phong cách chuyên nghiệp, uy tín
# ═══════════════════════════════════════════════════════════════

VARIANT_B_PROMPT = """Bạn là một biên tập viên chuyên nghiệp viết tiêu đề UY TÍN.

Phong cách của bạn:
  • Ngắn gọn, súc tích, đi thẳng vào trọng tâm
  • Thể hiện sự chuyên nghiệp và đáng tin cậy
  • Sử dụng từ ngữ chính xác, tránh giật tít
  • Phù hợp với báo chí chính thống

Nhiệm vụ: Viết 1 tiêu đề cho bài viết về chủ đề sau.

Chủ đề: {topic}

Yêu cầu:
  - CHỈ trả về ĐÚNG 1 tiêu đề (không giải thích)
  - Tối đa 15 từ
  - Tiếng Việt
"""

# ═══════════════════════════════════════════════════════════════
# VARIANT C: Phong cách storytelling, cảm xúc
# ═══════════════════════════════════════════════════════════════

VARIANT_C_PROMPT = """Bạn là một nhà văn chuyên viết tiêu đề theo kiểu STORYTELLING.

Phong cách của bạn:
  • Kể một câu chuyện ngắn trong tiêu đề
  • Gợi cảm xúc, tạo kết nối với người đọc
  • Sử dụng hình ảnh ẩn dụ, so sánh sáng tạo
  • Mang tính nhân văn, gần gũi

Nhiệm vụ: Viết 1 tiêu đề cho bài viết về chủ đề sau.

Chủ đề: {topic}

Yêu cầu:
  - CHỈ trả về ĐÚNG 1 tiêu đề (không giải thích)
  - Tối đa 15 từ
  - Tiếng Việt
"""

# ═══════════════════════════════════════════════════════════════
# EVALUATOR PROMPT — Đánh giá và chọn best option
# ═══════════════════════════════════════════════════════════════

EVALUATOR_PROMPT = """Bạn là một chuyên gia đánh giá nội dung marketing.

Dưới đây là 3 tiêu đề được tạo cho cùng một chủ đề:

Chủ đề: {topic}

--- CÁC TIÊU ĐỀ ---
[A] {headline_a}
[B] {headline_b}
[C] {headline_c}
--- KẾT THÚC ---

Nhiệm vụ: Đánh giá và CHỌN tiêu đề tốt nhất.

Tiêu chí đánh giá (thang điểm 1-10):
  1. Thu hút (Attention): Mức độ gây chú ý, muốn đọc tiếp
  2. Rõ ràng (Clarity): Người đọc hiểu ngay chủ đề
  3. Cảm xúc (Emotion): Kích thích cảm xúc, tạo kết nối
  4. SEO-friendly: Chứa từ khóa quan trọng
  5. Độ dài (Length): Ngắn gọn, phù hợp hiển thị

Trả về kết quả theo format:

## Đánh giá chi tiết

### [A] — {headline_a}
| Tiêu chí | Điểm |
|----------|------|
| Thu hút  | ?/10 |
| Rõ ràng  | ?/10 |
| Cảm xúc  | ?/10 |
| SEO      | ?/10 |
| Độ dài   | ?/10 |
| **Tổng** | ?/50 |

### [B] — {headline_b}
(tương tự)

### [C] — {headline_c}
(tương tự)

## 🏆 Kết quả

**Tiêu đề tốt nhất**: [?] — (tiêu đề)
**Lý do**: (giải thích ngắn gọn tại sao chọn tiêu đề này)
"""

# ═══════════════════════════════════════════════════════════════
# Danh sách variants để dễ iterate
# ═══════════════════════════════════════════════════════════════

VARIANTS = [
    {"name": "A", "label": "Sáng tạo / Tò mò", "prompt": VARIANT_A_PROMPT, "temperature": 0.9},
    {"name": "B", "label": "Chuyên nghiệp / Uy tín", "prompt": VARIANT_B_PROMPT, "temperature": 0.3},
    {"name": "C", "label": "Storytelling / Cảm xúc", "prompt": VARIANT_C_PROMPT, "temperature": 0.7},
]
