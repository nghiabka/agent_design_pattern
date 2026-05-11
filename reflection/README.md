# 🔍 Reflection Pattern — Conversational Agent with Self-Review

## Design Pattern: Reflection

Sau mỗi lượt trả lời, agent **tự review** câu trả lời bằng một Reflector LLM.
Nếu không đạt chất lượng → **regenerate** và review lại (tối đa N vòng).

## Architecture

```
  ┌──────────┐     ┌──────────────┐     ┌──────────────┐
  │  User    │────▶│  GENERATOR   │────▶│  REFLECTOR   │
  │  Message │     │  (Tạo reply) │     │  (QA Review) │
  └──────────┘     └──────────────┘     └──────┬───────┘
                          ▲                    │
                          │              ┌─────▼─────┐
                          │              │ PASS/FAIL │
                          │              └─────┬─────┘
                          │                    │
                          │ FAIL          PASS │
                          │ (regenerate)       │
                          │                    ▼
                          └──────────   ┌──────────┐
                                        │  ACCEPT  │
                                        │  → User  │
                                        └──────────┘
```

## Use Case: Customer Support Chatbot

Chatbot hỗ trợ khách hàng **TechViet** (công ty công nghệ):
- SmartPhone Pro X, TechCloud, TechCare, TechRepair
- Reflector kiểm tra: mạch lạc, chính xác, giọng điệu, hiểu đúng ý

## Thành phần

| File | Vai trò |
|------|---------|
| `config.py` | Load env vars cho LLM |
| `prompts.py` | 3 prompts: Generator, Reflector, Regenerator |
| `reflection.py` | Core: LangGraph loop + ReflectiveConversation class |
| `run.py` | Demo (3 lượt mẫu) + Interactive chat mode |

## Reflector đánh giá 5 tiêu chí

1. **Coherence** — Mạch lạc với lịch sử hội thoại
2. **Accuracy** — Thông tin chính xác
3. **Resolution** — Giải quyết đúng câu hỏi
4. **Tone** — Giọng điệu phù hợp
5. **Misunderstanding** — Không hiểu sai ý

## Setup & Chạy

```bash
uv sync

# Demo với 3 lượt hội thoại mẫu
uv run python run.py

# Chat tương tác
uv run python run.py --chat
```

## So sánh với các Pattern khác

| Pattern | Mục đích | Flow |
|---------|----------|------|
| Prompt Chaining | Phân rã tác vụ | A → B → C (tuần tự) |
| Routing | Phân loại & delegate | A → B₁ \| B₂ \| B₃ |
| Parallelization | Tạo nhiều options | A₁ \| A₂ \| A₃ → Eval |
| **Reflection** | **Tự review & cải thiện** | **Generate ↔ Reflect (loop)** |
