# 🤖 Agentic RAG Pattern — Self-correcting Retrieval Agent

## Design Pattern: Agentic RAG

RAG thường chỉ **retrieve một lần** rồi đưa context vào LLM để trả lời.
Agentic RAG biến retrieval thành một vòng điều khiển có kiểm tra:

1. **PLAN QUERY**: biến câu hỏi user thành truy vấn tìm kiếm tốt hơn
2. **RETRIEVE**: gọi tool tìm tài liệu trong knowledge base
3. **GRADE**: LLM đánh giá evidence đã đủ để trả lời chưa
4. **REWRITE**: nếu thiếu, agent tự viết lại query và retrieve tiếp
5. **ANSWER**: tổng hợp câu trả lời có citation, không bịa ngoài evidence

## Architecture

```text
  ┌──────────┐   ┌────────────┐   ┌──────────┐   ┌────────────┐
  │ Question │──▶│ Plan Query │──▶│ Retrieve │──▶│ Grade Docs │
  └──────────┘   └────────────┘   └──────────┘   └─────┬──────┘
                                                        │
                              enough evidence? ┌───────┴───────┐
                                                ▼               ▼
                                          ┌──────────┐   ┌──────────┐
                                          │  Answer  │◀──│ Rewrite  │
                                          └──────────┘   └──────────┘
```

## Use Case: Internal Banking Policy QA

Knowledge base mô phỏng chính sách nội bộ của **FinFlow Bank**:

| Source | Nội dung |
|--------|----------|
| `KB-001` | Mở tài khoản cá nhân/doanh nghiệp |
| `KB-002` | Gói tài khoản và phí |
| `KB-003` | Hạn mức chuyển khoản |
| `KB-004` | Bảo mật thẻ và khóa thẻ |
| `KB-005` | Khiếu nại giao dịch thẻ |
| `KB-006` | Sản phẩm tín dụng |
| `KB-007` | Quy tắc chuyển tuyến kiểm duyệt |

## Cấu trúc project

```text
agentic-rag/
├── agentic_rag/         # Package chính
│   ├── api.py           # FastAPI routes
│   ├── api_client.py    # HTTP client cho Streamlit
│   ├── documents.py     # Load markdown documents
│   ├── frontend.py      # Streamlit UI
│   ├── graph.py         # LangGraph Agentic RAG workflow
│   ├── observability.py # Langfuse callback + metadata config
│   ├── retriever.py     # Local BM25-style retriever
│   ├── schemas.py       # TypedDict + Pydantic schemas
│   ├── service.py       # Application service layer
│   ├── settings.py      # Env + path settings
│   └── tools.py         # search_knowledge_base, read_source
├── kb/                  # Markdown knowledge base
├── backend.py           # Thin FastAPI entrypoint wrapper
├── streamlit_app.py     # Thin Streamlit entrypoint wrapper
├── run.py               # Demo + interactive CLI
├── pyproject.toml
└── README.md
```

Các file `agent.py`, `config.py`, `documents.py`, `retriever.py`, `tools.py`, `tracing.py`
ở root chỉ là wrapper tương thích ngược. Code chính nằm trong package `agentic_rag/`.

## Setup & Chạy

```bash
cd agent_design_pattern/agentic-rag
cp .env.example .env
uv sync

# Demo 3 câu hỏi mẫu
uv run python run.py

# Hỏi một câu cụ thể
uv run python run.py "Khách muốn chuyển 300 triệu qua mobile app có được không?"

# Chat tương tác
uv run python run.py --chat

# Backend API
uv run uvicorn backend:app --host 0.0.0.0 --port 8000

# Frontend Streamlit UI
uv run streamlit run streamlit_app.py
```

## Backend / Frontend

Streamlit không chạy chatbot trực tiếp nữa. Luồng mới:

```text
Browser
  → Streamlit frontend (:8501)
  → FastAPI backend (:8000)
  → LangGraph Agentic RAG
  → LLM endpoint + Langfuse tracing
```

Backend endpoints:

| Endpoint | Mô tả |
|----------|------|
| `GET /health` | Runtime config, số tài liệu, Langfuse status |
| `GET /sources` | Danh sách tài liệu trong knowledge base |
| `POST /chat` | Chạy chatbot và trả về `answer` + retrieval trace |

Chạy 2 terminal:

```bash
# Terminal 1: backend chatbot
cd agent_design_pattern/agentic-rag
uv run uvicorn backend:app --host 0.0.0.0 --port 8000

# Terminal 2: frontend
cd agent_design_pattern/agentic-rag
uv run streamlit run streamlit_app.py
```

## Langfuse Tracing

Project dùng `langfuse.langchain.CallbackHandler` để trace LangGraph run, các node,
LLM calls và metadata của câu hỏi. Tracing là optional: nếu thiếu key, chatbot vẫn chạy.

Thêm cấu hình vào `.env`:

```bash
LANGFUSE_ENABLED=true
LANGFUSE_HOST=http://localhost:3000
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
```

Nếu muốn dùng Langfuse Cloud, đổi host:

```bash
LANGFUSE_HOST=https://cloud.langfuse.com
```

Với local Langfuse, mở UI ở:

```text
http://localhost:3000
```

Tạo project/API keys trong Langfuse UI rồi copy `public_key` và `secret_key` vào `.env`.

Trace được gắn metadata:

| Metadata | Ý nghĩa |
|----------|---------|
| `app` | `agentic-rag-demo` |
| `model` | Model đang dùng |
| `question` | Câu hỏi user |
| `session_id` | Phiên chat Streamlit nếu chạy UI |
| `user_id` | Cùng giá trị với `session_id` trong Streamlit |

Chạy demo có tracing:

```bash
uv run python run.py "Khách muốn chuyển 300 triệu qua mobile app có được không?"
```

Chạy backend/frontend có tracing:

```bash
uv run uvicorn backend:app --host 0.0.0.0 --port 8000
uv run streamlit run streamlit_app.py
```

## Demo Questions

| # | Câu hỏi | Điểm agentic |
|---|---------|--------------|
| 1 | "Khách hàng cá nhân muốn chuyển 300 triệu qua mobile app..." | Tìm hạn mức mobile và kết luận theo phân khúc |
| 2 | "Khách báo giao dịch thẻ lạ từ 2 ngày trước..." | Kết hợp khóa thẻ + dispute |
| 3 | "Startup mới mở tài khoản doanh nghiệp..." | Kết hợp onboarding + escalation |

## So sánh với RAG thường

| | RAG thường | Agentic RAG |
|---|---|---|
| Query | Dùng trực tiếp câu hỏi user | LLM lập query tối ưu |
| Retrieve | Một lần | Có thể nhiều vòng |
| Kiểm tra context | Không rõ ràng | Có node `GRADE` |
| Khi thiếu evidence | Vẫn có thể trả lời | Rewrite query hoặc nói thiếu |
| Citation | Tùy prompt | Bắt buộc theo source id |

## Tools

| Tool | Chức năng |
|------|-----------|
| `search_knowledge_base(query, top_k)` | Tìm tài liệu liên quan |
| `read_source(source_id)` | Đọc đầy đủ một source |

## Streamlit Chat UI

App Streamlit cung cấp giao diện chat để hỏi đáp với Agentic RAG:

- Chat history theo phiên làm việc
- Sidebar xem runtime config và toàn bộ knowledge base
- Câu hỏi mẫu để test nhanh
- Trace cho từng câu trả lời: search history, retrieval judge, retrieved evidence
- Citation dạng `[KB-xxx]` trong câu trả lời

Chạy app:

```bash
uv run streamlit run streamlit_app.py
```
