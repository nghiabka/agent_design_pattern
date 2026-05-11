# 🔀 Routing Pattern — Coordinator Agent Delegation

## Design Pattern: Routing

Routing là pattern trong đó một **Coordinator agent** nhận yêu cầu từ user,
**phân loại** nội dung, và **delegate** tới sub-agent chuyên biệt phù hợp.

Khác với Prompt Chaining (tuần tự), Routing **chọn 1 trong N nhánh** dựa trên nội dung yêu cầu.

## Architecture

```
                    ┌──────────────────┐
                    │   User Request   │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │   COORDINATOR    │
                    │  (Phân loại &    │
                    │   Delegate)      │
                    └──┬─────┬─────┬───┘
                       │     │     │
              ┌────────┘     │     └────────┐
              │              │              │
     ┌────────▼──────┐ ┌────▼───────┐ ┌────▼────────┐
     │   BOOKER      │ │   INFO     │ │   UNCLEAR   │
     │   Agent       │ │   Agent    │ │   Agent     │
     │               │ │            │ │  (fallback) │
     │ booking_handler│ │ info_handler│ │ unclear_   │
     │  (flight,     │ │ (weather,  │ │  handler    │
     │   hotel)      │ │  visa...)  │ │             │
     └───────────────┘ └────────────┘ └─────────────┘
```

## Thành phần

### Coordinator (coordinator.py)
- Nhận tin nhắn user → gọi LLM phân loại → trả route: `booker` / `info` / `unclear`
- Sử dụng LangGraph `StateGraph` với **conditional edges** để routing

### Booker Agent (agents.py)
- Xử lý đặt vé máy bay và phòng khách sạn
- Tool: `booking_handler` — simulate booking logic

### Info Agent (agents.py)
- Tra cứu thông tin: thời tiết, visa, điểm tham quan, tỷ giá
- Tool: `info_handler` — simulate info retrieval

### Unclear Agent (agents.py)
- Fallback cho yêu cầu không rõ ràng
- Tool: `unclear_handler` — hướng dẫn user mô tả rõ hơn

## Cấu trúc project

```
routing/
├── .env                 # Config kết nối LLM
├── pyproject.toml       # Dependencies
├── config.py            # Load environment variables
├── tools.py             # 3 handler functions (booking, info, unclear)
├── agents.py            # 3 sub-agents (Booker, Info, Unclear)
├── coordinator.py       # Coordinator graph + routing logic
├── run.py               # Entry point — demo với 5 requests mẫu
└── README.md
```

## Setup & Chạy

```bash
# 1. Cài dependencies
uv sync

# 2. Đảm bảo local model đang chạy
# Ví dụ: LM Studio tại http://127.0.0.1:1234

# 3. Chạy demo
uv run python run.py
```

## Demo Requests

| # | Yêu cầu | Expected Route |
|---|---------|----------------|
| 1 | "Đặt vé máy bay đi Tokyo ngày 15/06 cho 2 người" | ✈️ Booker |
| 2 | "Đặt phòng khách sạn ở Bangkok 3 đêm" | 🏨 Booker |
| 3 | "Thời tiết ở Singapore tuần này?" | 🌤️ Info |
| 4 | "Thông tin visa du lịch Nhật Bản" | 📋 Info |
| 5 | "Xin chào, bạn là ai?" | 🤔 Unclear |

## So sánh với Prompt Chaining

| Tiêu chí | Prompt Chaining | Routing |
|----------|-----------------|---------|
| Flow | Tuần tự: A → B → C | Phân nhánh: A → B₁ \| B₂ \| B₃ |
| Mục đích | Phân rã tác vụ phức tạp | Phân loại & delegate |
| Sub-agents | Không (chỉ prompts) | Có (mỗi nhánh 1 agent) |
| Gate validation | Giữa các bước | Tại routing decision |
| Use case | Xử lý tuần tự nhiều bước | Chọn handler phù hợp |
