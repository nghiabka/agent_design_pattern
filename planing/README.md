# 📋 Planning Pattern — Dynamic Multi-step Planner

## Design Pattern: Planning

Agent **KHÔNG thực thi ngay**. Thay vào đó:
1. **PLANNER**: Phân tích yêu cầu → tạo plan (danh sách bước + tools)
2. **EXECUTOR**: Thực thi từng bước, gọi tools theo plan
3. **REPORTER**: Tổng hợp kết quả → báo cáo cuối cùng

## Architecture

```
  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────┐
  │  User Goal   │────▶│   PLANNER    │────▶│   EXECUTOR   │────▶│  REPORTER│
  │              │     │  (Tạo plan)  │     │  (Loop steps)│     │  (Tổng   │
  └──────────────┘     └──────────────┘     └──────────────┘     │   hợp)   │
                             │                     │              └──────────┘
                       ┌─────▼─────┐         ┌─────▼──────┐
                       │ Plan JSON │         │ Step 1 ✅  │
                       │ Step 1..N │         │ Step 2 ✅  │
                       │ (dynamic) │         │ Step N ✅  │
                       └───────────┘         └────────────┘
```

## Use Case: Travel Planner

5 tools mô phỏng API du lịch:

| Tool | Chức năng |
|------|-----------|
| `search_flights` | Tìm chuyến bay |
| `search_hotels` | Tìm khách sạn |
| `get_weather` | Tra thời tiết |
| `get_attractions` | Điểm tham quan |
| `estimate_budget` | Ước tính ngân sách |

## Khác biệt với Prompt Chaining

| | Prompt Chaining | Planning |
|---|---|---|
| Steps | **Hard-coded** (cố định) | **Dynamic** (LLM tạo tùy yêu cầu) |
| Tools | Không dùng tools | Mỗi step gọi 1 tool |
| Flexibility | Cùng steps cho mọi input | Khác steps tùy input |

## Setup & Chạy

```bash
uv sync
uv run python run.py
uv run python run.py "Du lịch Phú Quốc 5 ngày từ HCM, 4 người"
```
