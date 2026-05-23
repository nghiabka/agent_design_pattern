# 🤖 Agentic RAG Pattern — Self-correcting Retrieval Agent

## Design Pattern: Agentic RAG

RAG thường chỉ **retrieve một lần** rồi đưa context vào LLM để trả lời.
Agentic RAG biến retrieval thành một vòng điều khiển có kiểm tra:

1. **INPUT GUARD**: chặn prompt-injection cơ bản và che PII trước khi truy vấn
2. **INTENT ROUTER**: chit-chat trả lời ngay, ngoài phạm vi thì decline, policy mới chạy RAG
3. **REASONER CORE**: tạo action contract có schema, rewrite query và tách thành nhiều retrieval queries
4. **ACTION VALIDATOR**: validate contract trước khi graph route sang retrieve/clarify/fallback/finalize
5. **RETRIEVE**: chạy multi-query retrieval trên knowledge base
6. **RETRIEVAL GRADER**: chấm relevance, coverage, source quality theo hướng CRAG
7. **CONTEXT CONTROL + LOOP BUDGET**: giữ evidence tốt, lưu failure notes và retry có giới hạn
8. **ANSWER + OUTPUT GUARD**: tổng hợp có citation và kiểm tra citation phải nằm trong evidence

## Architecture

```text
Question
  → Input Guard
  → Intent Router
      ├─ chitchat      → Direct Answer → Output Guard
      ├─ out_of_scope  → Decline       → Output Guard
      └─ rag           → Reasoner Core
                            → Action Validator
                            → Multi-query Retrieve
                            → Retrieval Grader
                            → Context Control
                            → Loop Budget
                               ├─ enough evidence → Answer → Output Guard
                               ├─ retryable       → Reasoner Core
                               └─ exhausted       → Fallback → Output Guard
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

## Chạy App

### 1. Chuẩn bị

Yêu cầu:

- Python 3.11+
- `uv`
- LLM endpoint OpenAI-compatible đang chạy, mặc định `http://127.0.0.1:1234/v1`
- Docker nếu muốn chạy Langfuse local

```bash
cd agent_design_pattern/agentic-rag
cp .env.example .env
uv sync
```

Mở `.env` và chỉnh nếu cần:

```bash
OPENAI_API_BASE=http://127.0.0.1:1234/v1
OPENAI_API_KEY=local-key
OPENAI_MODEL_NAME=local-model

BACKEND_URL=http://localhost:8000

LANGFUSE_ENABLED=true
LANGFUSE_HOST=http://localhost:3000
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
```

Nếu chưa có Langfuse key, để trống `LANGFUSE_PUBLIC_KEY` và `LANGFUSE_SECRET_KEY`; app vẫn chạy, chỉ tắt tracing.

### 2. Chạy Langfuse Local

Nếu bạn đã có Langfuse ở `http://localhost:3000`, bỏ qua bước này.

Repo hiện có compose mẫu ở `memory_management/langfuse-compose.yml`:

```bash
cd agent_design_pattern/memory_management
docker compose -f langfuse-compose.yml up -d
```

Mở Langfuse:

```text
http://localhost:3000
```

Tạo project/API keys trong Langfuse UI, sau đó copy `public_key` và `secret_key` vào `.env` của `agentic-rag`.

### 3. Chạy Backend

Terminal 1:

```bash
cd agent_design_pattern/agentic-rag
uv run uvicorn backend:app --host 0.0.0.0 --port 8000
```

Kiểm tra:

```bash
curl http://localhost:8000/health
```

Kết quả nên có:

```json
{
  "status": "ok",
  "documents": 7,
  "langfuse": {
    "enabled": true,
    "configured": true,
    "host": "http://localhost:3000"
  }
}
```

Nếu `configured=false`, nghĩa là thiếu `LANGFUSE_PUBLIC_KEY` hoặc `LANGFUSE_SECRET_KEY`.

### 4. Chạy Frontend

Terminal 2:

```bash
cd agent_design_pattern/agentic-rag
uv run streamlit run streamlit_app.py
```

Mở app:

```text
http://localhost:8501
```

### 5. Test API Chat

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Hạn mức chuyển khoản mobile app cá nhân là bao nhiêu?",
    "session_id": "manual-test"
  }'
```

Response có dạng:

```json
{
  "answer": "... [KB-003]",
  "response_time_seconds": 12.345,
  "trace": {
    "elapsed": 12.345,
    "guardrail": {
      "status": "pass",
      "pii_masked": false
    },
    "intent_route": "rag",
    "intent": {
      "route": "rag",
      "intent": "transfer limit",
      "reason": "requires policy evidence"
    },
    "reasoner": {
      "action": "retrieve",
      "rewritten_query": "...",
      "retrieval_queries": ["...", "..."],
      "required_evidence": ["..."]
    },
    "required_evidence": ["..."],
    "rounds": 1,
    "retrieval_queries": ["...", "..."],
    "search_history": ["..."],
    "judge": {
      "sufficient": true,
      "coverage_score": 0.9,
      "accepted_source_ids": ["KB-003"]
    },
    "budget": {
      "rounds": 1,
      "max_rounds": 3,
      "next": "answer"
    },
    "output_guard": {
      "status": "pass",
      "citations": ["KB-003"]
    },
    "evidence": []
  }
}
```

Backend cũng gắn header `X-Process-Time-Seconds` cho mọi response HTTP.

## Luồng Backend / Frontend

Streamlit không chạy chatbot trực tiếp nữa. Luồng mới:

```text
Browser
  → Streamlit frontend (:8501)
  → FastAPI backend (:8000)
  → Input guard + intent router
  → LangGraph Agentic RAG reasoning loop
  → LLM endpoint + Langfuse tracing
```

Backend endpoints:

| Endpoint | Mô tả |
|----------|------|
| `GET /health` | Runtime config, số tài liệu, Langfuse status |
| `GET /sources` | Danh sách tài liệu trong knowledge base |
| `POST /chat` | Chạy chatbot và trả về `answer`, `response_time_seconds` + retrieval trace |

## CLI Demo

```bash
cd agent_design_pattern/agentic-rag

# Demo câu hỏi mẫu
uv run python run.py

# Hỏi một câu cụ thể
uv run python run.py "Khách muốn chuyển 300 triệu qua mobile app có được không?"

# Chat trong terminal
uv run python run.py --chat
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

Khi chạy backend hoặc CLI theo hướng dẫn ở trên, trace sẽ được gửi về Langfuse nếu keys hợp lệ.

## 9router Compose

Nếu bạn muốn chạy 9router bằng compose:

```bash
cd /data/learning/agent
docker compose -f 9router/docker-compose.yml up -d
```

Compose tương đương:

```bash
docker run -d \
  -p 20129:20128 \
  -v "$HOME/.9router:/app/data" \
  -e DATA_DIR=/app/data \
  --name 9router \
  decolua/9router:latest
```

Có thể override port bằng biến môi trường:

```bash
NINEROUTER_HOST_PORT=20130 docker compose -f 9router/docker-compose.yml up -d
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
| Query | Dùng trực tiếp câu hỏi user | Reasoner rewrite/decompose thành nhiều retrieval queries |
| Retrieve | Một lần | Multi-query, có thể nhiều vòng |
| Kiểm tra context | Không rõ ràng | `Retrieval Grader` chấm coverage/relevance/source quality |
| Khi thiếu evidence | Vẫn có thể trả lời | Lưu failure notes, retry theo budget hoặc fallback |
| Citation | Tùy prompt | Output guard kiểm tra citation phải nằm trong evidence |
| Scope | Hay retrieve cả chit-chat/out-of-scope | Intent router/direct answer/decline trước retrieval |

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
- Response time hiển thị ngay dưới mỗi câu trả lời
- Trace cho từng câu trả lời: input guard, intent route, reasoner contract,
  retrieval queries, retrieval judge, loop budget, output guard và retrieved evidence
- Citation dạng `[KB-xxx]` trong câu trả lời

Xem mục **Chạy App** để chạy backend và frontend theo đúng thứ tự.
