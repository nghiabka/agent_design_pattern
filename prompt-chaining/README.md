# 🔗 Prompt Chaining — Multimodal & Multi-step Reasoning

## Design Pattern: Prompt Chaining

Prompt Chaining là pattern phân rã một tác vụ phức tạp thành **chuỗi các bước nhỏ hơn**.
Output của bước trước trở thành input cho bước sau, tạo thành pipeline xử lý tuần tự.

## Bài toán

Phân tích ảnh chứa nhiều loại thông tin (multimodal):
- 📝 **Text nhúng trong ảnh** (tiêu đề, chú thích)
- 🏷️ **Labels** chỉ tới các vùng cụ thể trên ảnh
- 📊 **Bảng dữ liệu** giải thích từng label

## Pipeline

```
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
```

### Prompt 1: Extract Text
- **Input**: Ảnh gốc (base64)
- **Output**: Tất cả text trích xuất từ ảnh (tiêu đề, labels, bảng, text khác)
- **Gate 1**: Kiểm tra text trích xuất có đủ nội dung không

### Prompt 2: Link Labels
- **Input**: Text trích xuất từ Prompt 1
- **Output**: Mapping giữa labels và thông tin tương ứng
- **Gate 2**: Kiểm tra liên kết có hợp lệ không

### Prompt 3: Interpret & Conclude
- **Input**: Text trích xuất (Prompt 1) + Phân tích liên kết (Prompt 2)
- **Output**: Báo cáo cuối cùng với bảng tổng hợp và kết luận

## Cấu trúc project

```
prompt-chaining/
├── .env                 # Config kết nối LLM
├── pyproject.toml       # Dependencies
├── config.py            # Load environment variables
├── prompts.py           # 3 prompt templates
├── chain.py             # Core pipeline logic + gate validation
├── run.py               # Entry point
├── sample_images/       # Ảnh mẫu để test
│   └── patient_report.png
└── README.md
```

## Setup & Chạy

```bash
# 1. Cài dependencies
uv sync

# 2. Đảm bảo local model đang chạy (hỗ trợ vision/multimodal)
# Ví dụ: LM Studio tại http://127.0.0.1:1234

# 3. Chạy với ảnh mẫu
uv run python run.py

# 4. Hoặc chạy với ảnh tùy chọn
uv run python run.py path/to/your/image.png
```

## Yêu cầu

- Python >= 3.11
- Local model hỗ trợ **vision/multimodal** (qua OpenAI-compatible API)
- Ảnh đầu vào chứa text + labels + bảng dữ liệu

## Tại sao Prompt Chaining?

| Tiêu chí | Single Prompt | Prompt Chaining |
|----------|---------------|-----------------|
| Kiểm soát chất lượng | ✗ Khó | ✓ Gate validation giữa các bước |
| Debug | ✗ Không biết lỗi ở đâu | ✓ Biết chính xác bước nào lỗi |
| Cải tiến | ✗ Sửa 1 prompt ảnh hưởng tất cả | ✓ Cải tiến từng bước độc lập |
| Token efficiency | ✓ Ít API calls | ✗ Nhiều API calls hơn |
| Độ chính xác | ✗ LLM dễ bỏ sót | ✓ Mỗi bước tập trung 1 nhiệm vụ |
