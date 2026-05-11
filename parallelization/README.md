# ⚡ Parallelization Pattern — A/B Testing & Multiple Options Generation

## Design Pattern: Parallelization

Parallelization tạo **nhiều phiên bản output đồng thời** (song song),
sau đó so sánh và chọn kết quả tốt nhất.

## Architecture

```
                         ┌──────────────────┐
                         │   User Input     │
                         │  (Topic/Article) │
                         └────────┬─────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │      ← asyncio.gather()
           ┌───────▼──────┐ ┌────▼───────┐ ┌───▼────────┐
           │  VARIANT A   │ │ VARIANT B  │ │ VARIANT C  │
           │  Creative /  │ │ Professional│ │ Storytelling│
           │  Curious     │ │ / Authorit.│ │ / Emotional│
           │  temp=0.9    │ │ temp=0.3   │ │ temp=0.7   │
           └───────┬──────┘ └────┬───────┘ └───┬────────┘
                    │             │             │
                    └─────────────┼─────────────┘
                                  │
                         ┌────────▼─────────┐
                         │   EVALUATOR      │
                         │  (Compare &      │
                         │   Select Best)   │
                         └────────┬─────────┘
                                  │
                         ┌────────▼─────────┐
                         │  🏆 Best Option  │
                         └──────────────────┘
```

## Thành phần

### 3 Variants (prompts.py)
| Variant | Style | Temperature | Đặc điểm |
|---------|-------|-------------|-----------|
| A | Sáng tạo / Tò mò | 0.9 | Gây shock, câu hỏi, số liệu |
| B | Chuyên nghiệp / Uy tín | 0.3 | Ngắn gọn, đáng tin cậy |
| C | Storytelling / Cảm xúc | 0.7 | Ẩn dụ, nhân văn, gần gũi |

### Evaluator (prompts.py)
- Chấm điểm 5 tiêu chí (1-10): Thu hút, Rõ ràng, Cảm xúc, SEO, Độ dài
- Tổng điểm /50 → chọn winner

### Parallel Runner (parallel.py)
- `asyncio.gather()` chạy 3 variants đồng thời
- Tổng thời gian ≈ `max(variant_times)` thay vì `sum(variant_times)`

## Cấu trúc project

```
parallelization/
├── .env                 # Config kết nối LLM
├── pyproject.toml       # Dependencies
├── config.py            # Load environment variables
├── prompts.py           # 3 variant prompts + evaluator prompt
├── parallel.py          # Core: asyncio.gather() + evaluation
├── run.py               # Entry point
└── README.md
```

## Setup & Chạy

```bash
# 1. Cài dependencies
uv sync

# 2. Chạy demo với topic mặc định
uv run python run.py

# 3. Hoặc chạy với topic tùy chọn
uv run python run.py "Xu hướng AI trong y tế năm 2025"
```

## So sánh hiệu suất

```
Tuần tự:  A(5s) → B(5s) → C(5s) = 15s
Song song: A(5s) | B(5s) | C(5s) =  5s  → 3x nhanh hơn!
```

## So sánh với các Pattern khác

| Pattern | Flow | Mục đích |
|---------|------|----------|
| Prompt Chaining | A → B → C (tuần tự) | Phân rã tác vụ phức tạp |
| Routing | A → B₁ \| B₂ \| B₃ (chọn 1) | Phân loại & delegate |
| **Parallelization** | **A₁ \| A₂ \| A₃ → Eval (đồng thời)** | **Tạo nhiều options → chọn best** |
