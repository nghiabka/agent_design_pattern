"""
═══════════════════════════════════════════════════════════════════════
PROMPT TEMPLATES — Các prompt cho từng bước trong chuỗi
═══════════════════════════════════════════════════════════════════════

Prompt Chaining chia bài toán multimodal phức tạp thành 3 bước nhỏ:
  ● Prompt 1: Trích xuất text từ ảnh (OCR-like reasoning)
  ● Prompt 2: Liên kết text với labels trên ảnh
  ● Prompt 3: Tổng hợp thông tin thành bảng → đưa ra kết luận
"""

# ═══════════════════════════════════════════════════════════════
# PROMPT 1: Extract text from image
# ═══════════════════════════════════════════════════════════════
# Bước đầu tiên: LLM nhìn vào ảnh và trích xuất MỌI text có trong ảnh.
# Bao gồm: tiêu đề, labels, bảng dữ liệu, số liệu, etc.

PROMPT_1_EXTRACT_TEXT = """Bạn là một chuyên gia trích xuất thông tin từ hình ảnh.

Nhiệm vụ: Phân tích hình ảnh được cung cấp và trích xuất TẤT CẢ văn bản có trong ảnh.

Hãy trả về kết quả theo format sau:

## Tiêu đề / Header
(Liệt kê các tiêu đề, header tìm thấy trong ảnh)

## Labels / Nhãn
(Liệt kê tất cả các labels, annotations, nhãn gắn trên ảnh)

## Dữ liệu bảng (nếu có)
(Trích xuất nội dung bảng dạng markdown table)

## Văn bản khác
(Bất kỳ text nào khác tìm thấy trong ảnh)

LƯU Ý:
- Trích xuất chính xác, không bỏ sót text nào
- Giữ nguyên số liệu, đơn vị đo
- Nếu text không rõ, ghi chú "[không rõ]"
"""

# ═══════════════════════════════════════════════════════════════
# PROMPT 2: Link text with labels
# ═══════════════════════════════════════════════════════════════
# Bước thứ hai: Dựa trên text đã trích xuất ở bước 1,
# liên kết các text segment với labels tương ứng.
# Input: kết quả từ Prompt 1

PROMPT_2_LINK_LABELS = """Bạn là một chuyên gia phân tích mối quan hệ giữa text và labels trong hình ảnh.

Dưới đây là văn bản đã được trích xuất từ một hình ảnh:

--- BẮT ĐẦU TEXT TRÍCH XUẤT ---
{extracted_text}
--- KẾT THÚC TEXT TRÍCH XUẤT ---

Nhiệm vụ: Phân tích và liên kết các đoạn text với labels tương ứng.

Hãy trả về kết quả theo format:

## Mapping Label → Thông tin

Với mỗi label tìm được, hãy xác định:
1. **Tên label**: Label gốc trên ảnh
2. **Đối tượng tham chiếu**: Label này đang chỉ tới đối tượng / vùng nào
3. **Giá trị / Dữ liệu**: Thông số đi kèm label
4. **Liên kết với bảng**: Nếu label có dữ liệu tương ứng trong bảng, chỉ rõ hàng nào

## Mối quan hệ
Mô tả tổng quan về mối quan hệ giữa các labels và dữ liệu bảng.
Các labels có nhất quán với dữ liệu bảng không? Có sai lệch nào không?
"""

# ═══════════════════════════════════════════════════════════════
# PROMPT 3: Interpret with table and determine output
# ═══════════════════════════════════════════════════════════════
# Bước cuối: Tổng hợp toàn bộ thông tin từ bước 1 & 2,
# sử dụng bảng để đưa ra kết luận cuối cùng.

PROMPT_3_INTERPRET = """Bạn là một chuyên gia phân tích dữ liệu đa phương thức (multimodal).

Dưới đây là thông tin đã được trích xuất và phân tích từ một hình ảnh:

--- TEXT TRÍCH XUẤT (Bước 1) ---
{extracted_text}
--- KẾT THÚC TEXT ---

--- PHÂN TÍCH LIÊN KẾT LABEL (Bước 2) ---
{linked_labels}
--- KẾT THÚC PHÂN TÍCH ---

Nhiệm vụ: Tổng hợp tất cả thông tin và đưa ra BÁO CÁO CUỐI CÙNG.

Hãy trả về kết quả theo format:

## Tóm tắt hình ảnh
(Mô tả ngắn gọn hình ảnh đang thể hiện gì)

## Bảng tổng hợp dữ liệu

| STT | Đối tượng | Label trên ảnh | Giá trị | Trạng thái | Ghi chú |
|-----|-----------|----------------|---------|-------------|---------|
| ... | ...       | ...            | ...     | ...         | ...     |

## Phân tích & Nhận xét
- Tất cả các labels có khớp với dữ liệu bảng không?
- Có thông tin bất thường nào không?
- Đánh giá tổng quan về nội dung hình ảnh

## Kết luận
(Kết luận cuối cùng dựa trên phân tích đa bước)
"""
