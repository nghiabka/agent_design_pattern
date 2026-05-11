# 🏠 Tool Call Pattern — Smart Home Agent

## Design Pattern: Tool Call (Function Calling)

LLM agent nhận yêu cầu bằng **ngôn ngữ tự nhiên**, hiểu ý định,
và **gọi đúng tool** với **đúng tham số** để thực thi hành động.

## Architecture

```
  ┌──────────────────┐     ┌────────────────┐     ┌────────────────┐
  │  "Tắt đèn        │────▶│   LLM Agent    │────▶│  Tool Call:    │
  │   phòng khách"   │     │  (ReAct Agent) │     │ control_light  │
  └──────────────────┘     │                │     │ room, action   │
                           │  hiểu ý định   │     └────────┬───────┘
                           │  chọn tool     │              │
                           │  fill params   │    result     │
                           │◀──────────────────────────────┘
                           │                │
                           └────────┬───────┘
                                    │
                           ┌────────▼───────┐
                           │ "Đã tắt đèn    │
                           │  phòng khách ✅" │
                           └────────────────┘
```

## Smart Home Devices

| Thiết bị | Phòng | Tool |
|----------|-------|------|
| 💡 Đèn | Phòng khách, Phòng ngủ, Bếp | `control_light` |
| 🌡️ Điều hòa | Phòng khách, Phòng ngủ | `control_ac` |
| 📺 TV | Phòng khách | `control_tv` |
| 🔒 Khóa cửa | Cửa chính, Garage | `control_lock` |
| 🎵 Loa | Phòng khách | `control_speaker` |

## Cấu trúc project

```
tool_call/
├── config.py            # Load env vars
├── smart_home.py        # IoT device simulator (9 thiết bị)
├── tools.py             # 6 tools wrap smart home API
├── agent.py             # ReAct agent + system prompt
├── run.py               # Demo + interactive chat
└── README.md
```

## Setup & Chạy

```bash
uv sync

# Demo 5 lệnh mẫu
uv run python run.py

# Chat tương tác
uv run python run.py --chat
```

## Demo Commands

| # | Lệnh | Tools gọi |
|---|-------|-----------|
| 1 | "Tắt đèn phòng khách" | `control_light` ×1 |
| 2 | "Xem trạng thái phòng khách" | `get_device_status` ×1 |
| 3 | "Bật điều hòa phòng ngủ 22 độ" | `control_ac` ×1 |
| 4 | "Tắt đèn bếp, tắt TV, khóa cửa" | `control_light` + `control_tv` + `control_lock` ×3 |
| 5 | "Phát nhạc Lofi vol 30%" | `control_speaker` ×1 |

## So sánh với các Pattern khác

| Pattern | Mục đích |
|---------|----------|
| Prompt Chaining | Phân rã tác vụ tuần tự |
| Routing | Phân loại & delegate |
| Parallelization | Tạo nhiều options song song |
| Reflection | Tự review & cải thiện |
| **Tool Call** | **LLM gọi API/function để thực thi hành động** |
