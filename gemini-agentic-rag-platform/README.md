# 🏢 Gemini Enterprise Agent Platform — Agentic RAG Framework

> Source: Google Research & Google Cloud (June 5, 2026)
> Platform: Gemini Enterprise Agent Platform — Cross-Corpus Retrieval (Public Preview)
> Blog: [research.google](https://research.google/blog/agentic-rag-in-the-gemini-enterprise-agent-platform/)

---

## Chạy project

```bash
uv sync
uv run python run.py
uv run python run.py --chat
```

Qwen3 thinking mode mặc định được tắt để giảm latency cho các agent trả JSON.
Có thể bật lại khi cần:

```env
OPENAI_ENABLE_THINKING=true
```

### Langfuse tracing

Mỗi câu hỏi có một root trace, bên trong gồm các LangGraph node và LLM call.
Các câu hỏi trong cùng phiên `--chat` được gom chung bằng session ID.

```env
LANGFUSE_ENABLED=true
LANGFUSE_BASE_URL=http://localhost:3000
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_ENVIRONMENT=development
LANGFUSE_FLUSH_ON_RUN=true
```

Nếu tracing bị tắt hoặc thiếu key, workflow RAG vẫn chạy bình thường.

## Tổng quan

**Agentic RAG Framework** là kiến trúc multi-agent được tích hợp vào Gemini Enterprise Agent Platform, giải quyết hạn chế của RAG truyền thống khi xử lý các truy vấn phức tạp trong doanh nghiệp — nơi thông tin bị phân mảnh trên nhiều nguồn dữ liệu ("data islands").

### Vấn đề với RAG truyền thống

```text
User Query → Single Retrieval → Generate Answer
                  ↓
         ❌ Chỉ tìm 1 lần
         ❌ Không xử lý được multi-hop
         ❌ Không kiểm tra context đã đủ chưa
         ❌ Dễ hallucinate khi thiếu thông tin
```

**Ví dụ thực tế:** User hỏi *"Cấu hình server XYZ-001 là gì?"*
- RAG truyền thống: Tìm được tài liệu chứa ID `XYZ-001` nhưng không có specs → bịa câu trả lời
- Agentic RAG: Tìm ID `XYZ-001` → phát hiện cần thêm specs → tự động tìm tiếp trong database inventory → trả lời chính xác

---

## Kiến trúc 5-Agent

Framework hoạt động như một **"phòng nghiên cứu có tổ chức"** thay vì một công cụ tìm kiếm đơn lẻ:

```text
                        User Query
                            │
                            ▼
                ┌───────────────────────┐
                │   1. ORCHESTRATOR     │
                │      (Root Agent)     │
                │                       │
                │  Đánh giá độ phức tạp │
                │  Simple → trả lời    │
                │  Complex → delegate   │
                └───────────┬───────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │   2. PLANNING AGENT   │
                │                       │
                │  Phân tích query      │
                │  Chọn corpora phù hợp │
                │  Lập kế hoạch tìm kiếm│
                └───────────┬───────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │  3. QUERY REWRITER    │
                │                       │
                │  Tách query phức tạp  │
                │  → nhiều sub-queries  │
                │  tối ưu cho retrieval │
                └───────────┬───────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │  4. SEARCH FANOUT     │
                │     AGENT             │
                │                       │
                │  Thực thi queries     │
                │  trên nhiều corpora   │
                │  (cross-corpus)       │
                └───────────┬───────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │  5. SUFFICIENT        │
                │     CONTEXT AGENT     │◄──── Nếu INSUFFICIENT
                │                       │      → quay lại bước 2-4
                │  Đánh giá context     │      (iterative loop)
                │  sufficient / not     │
                │                       │
                │  ✅ Sufficient → Answer│
                │  ❌ Insufficient → Loop│
                └───────────────────────┘
```

---

## Chi tiết từng Agent

### 1. Orchestrator (Root Agent)

**Vai trò:** Điều phối tổng thể — nhận query, phân loại, delegate.

```text
Query → Orchestrator
         ├── Simple query   → Trả lời trực tiếp (single-step)
         └── Complex query  → Delegate cho Planning Agent (multi-step)
```

- Đánh giá query có cần multi-hop hay không
- Quyết định workflow phù hợp
- Tổng hợp kết quả cuối cùng

### 2. Planning Agent

**Vai trò:** Lập kế hoạch retrieval — chọn corpora và chiến lược tìm kiếm.

| Chức năng | Chi tiết |
|-----------|---------|
| Phân tích query | Hiểu intent và thông tin cần thiết |
| Chọn corpora | Dựa trên **corpus descriptions** để route chính xác |
| Lập kế hoạch | Xác định thứ tự và cách tìm kiếm |

> ⚠️ **Quan trọng:** Corpus descriptions phải chất lượng cao vì đây là cơ sở để Planning Agent route queries. Descriptions **không thể sửa** sau khi tạo corpus.

### 3. Query Rewriter

**Vai trò:** Chuyển đổi query phức tạp thành nhiều sub-queries tối ưu.

```text
Input:  "Tìm cấu hình và chi phí vận hành của tất cả server
         ở data center Hà Nội mua trong Q1 2025"

Output: [
  "server list data center Hanoi purchased Q1 2025",
  "server configuration specs {server_ids}",
  "server operating cost monthly {server_ids}"
]
```

- Tách câu hỏi mơ hồ/dài thành các queries ngắn, cụ thể
- Tối ưu cho retrieval engine
- Xử lý dependency giữa các sub-queries (sequential retrieval)

### 4. Search Fanout Agent

**Vai trò:** Thực thi queries trên nhiều nguồn dữ liệu song song.

```text
Sub-queries
  ├── Query 1 → Corpus A (HR Database)
  ├── Query 2 → Corpus B (Inventory System)
  └── Query 3 → Corpus C (Finance Records)
                    │
                    ▼
           Aggregated Results
```

- **Cross-corpus retrieval**: Tìm kiếm đồng thời trên nhiều RAG corpora
- Kết nối các "data islands" — thông tin phân tán ở nhiều hệ thống
- Hỗ trợ multi-hop: kết quả từ corpus A làm input cho search trên corpus B

### 5. Sufficient Context Agent ⭐

**Vai trò:** Quality gate — đánh giá context đã đủ để trả lời chưa.

Đây là **innovation quan trọng nhất** của framework, dựa trên nghiên cứu [Sufficient Context (ICLR 2025)](https://arxiv.org/abs/2411.06037).

```text
Retrieved Context
      │
      ▼
┌─────────────────────────────────┐
│  Sufficient Context Agent       │
│                                 │
│  1. Context có đủ info không?   │
│  2. Có missing pieces nào?      │
│  3. Confidence assessment       │
│                                 │
│  → SUFFICIENT: Generate answer  │
│  → INSUFFICIENT:                │
│     - Log lý do thiếu           │
│     - Rewrite queries           │
│     - Trigger retrieval loop    │
└─────────────────────────────────┘
```

**Quy trình khi insufficient:**
1. Kiểm tra snippets retrieved → phát hiện thiếu thông tin cụ thể
2. Thực hiện **"missing pieces" analysis** — ghi lại chính xác thiếu gì
3. Gửi signal quay lại Planning/Query Rewriter để tìm thêm
4. Lặp lại cho đến khi sufficient hoặc hết budget

---

## Cross-Corpus Retrieval — Multi-Hop trong thực tế

### Ví dụ: Truy vấn multi-hop

```text
User: "Ai phụ trách server có incident nhiều nhất tháng trước?"

Hop 1: Search Incident Corpus
  → Tìm server "SRV-042" có nhiều incident nhất

Hop 2: Search Inventory Corpus (dùng kết quả hop 1)
  → Tìm thông tin "SRV-042" → thuộc team Infrastructure

Hop 3: Search HR Corpus (dùng kết quả hop 2)
  → Tìm team lead Infrastructure → "Nguyễn Văn A"

Final Answer: "Nguyễn Văn A, Team Lead Infrastructure,
              phụ trách server SRV-042 với 12 incidents."
```

### So sánh Single-Corpus vs Cross-Corpus

| | Single-Corpus | Cross-Corpus (Agentic RAG) |
|---|---|---|
| Nguồn dữ liệu | 1 corpus | Nhiều corpora |
| Multi-hop | ❌ Không hỗ trợ | ✅ Tự động follow-up |
| Data islands | Bỏ sót thông tin | Kết nối liền mạch |
| Accuracy | Baseline | **+34% trên factuality datasets** |
| Latency | Baseline | **< 3% overhead** so với single-corpus |

---

## Kết quả đánh giá

### Benchmark: FramesQA Dataset

| Metric | Giá trị |
|--------|---------|
| Dataset | 824 queries, 2,676 PDF documents |
| Số corpora | 4 corpora riêng biệt |
| Accuracy | **90.1%** correct answers |
| So với RAG truyền thống | **+34%** trên factuality datasets |
| Latency overhead | **< 3%** so với single-corpus |

### So sánh tổng thể

| Khía cạnh | RAG truyền thống | Agentic RAG (Gemini) |
|-----------|-----------------|---------------------|
| Workflow | Linear: Retrieve → Generate | Iterative multi-agent loop |
| Multi-hop | ❌ Dừng sau 1 lần retrieve | ✅ Planning + sequential hops |
| Context check | ❌ Không có | ✅ Sufficient Context Agent |
| Cross-corpus | ❌ Single source | ✅ Nhiều corpora đồng thời |
| Hallucination | Cao khi context thiếu | Giảm đáng kể nhờ guided abstention |
| Query handling | Dùng trực tiếp query gốc | Rewrite + decompose thành sub-queries |

---

## APIs

Platform cung cấp 2 API chính:

### 1. `AskContexts` (Synchronous)

End-to-end: nhận query → search cross-corpus → trả answer.

```text
POST /ask-contexts
{
  "query": "Cấu hình server XYZ-001?",
  "corpora": ["inventory", "specs", "maintenance"]
}

Response:
{
  "answer": "Server XYZ-001: Dell PowerEdge R750, 128GB RAM...",
  "sources": ["inventory/doc-42", "specs/server-configs"],
  "sufficient": true
}
```

### 2. `AsyncRetrieveContexts` (Asynchronous)

Long-running API cho các tác vụ retrieval phức tạp, time-intensive:

```text
POST /async-retrieve-contexts
{
  "query": "So sánh chi phí vận hành tất cả DC trong 12 tháng qua",
  "corpora": ["finance", "operations", "inventory"],
  "max_hops": 5
}

Response:
{
  "operation_id": "op-abc123",
  "status": "RUNNING"
}
```

---

## So sánh với các Agentic RAG pattern khác

| Pattern | Agents | Sufficient Context | Cross-Corpus | Multi-Hop | Production-Ready |
|---------|--------|-------------------|-------------|-----------|-----------------|
| **Gemini Enterprise** | 5 specialized agents | ✅ Dedicated agent | ✅ Native | ✅ Sequential hops | ✅ Managed service |
| **LangGraph Agentic RAG** | Configurable nodes | Retrieval Grader (tương tự) | Manual setup | ✅ Loop-based | ❌ Self-hosted |
| **CRAG** | Single pipeline | ❌ Relevance only | ❌ | ❌ | ❌ Research |
| **Self-RAG** | Single model | ❌ Self-reflection | ❌ | Partial | ❌ Research |
| **Adaptive RAG** | Router + retriever | ❌ | ❌ | Partial | ❌ Research |

---

## Kiến trúc tổng thể trong Gemini Enterprise Agent Platform

```text
┌──────────────────────────────────────────────────────────┐
│              Gemini Enterprise Agent Platform             │
│                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │ Agent        │  │ RAG Engine   │  │ Agent          │  │
│  │ Development  │  │              │  │ Evaluation     │  │
│  │ Kit (ADK)    │  │ • Ingestion  │  │ Service        │  │
│  │              │  │ • Indexing   │  │                │  │
│  │ • Tools      │  │ • Retrieval  │  │ • Multi-turn   │  │
│  │ • Workflows  │  │ • Ranking    │  │ • Task success │  │
│  │ • Sessions   │  │ • Agentic    │  │ • Quality      │  │
│  │              │  │   RAG ⭐     │  │   flywheel     │  │
│  └─────────────┘  └──────────────┘  └────────────────┘  │
│                                                          │
│  Security: VPC-SC + CMEK                                 │
│  Regions: us-central1 (Public Preview)                   │
└──────────────────────────────────────────────────────────┘
```

---

## Lessons Learned & Best Practices

### 1. Corpus Descriptions là critical

```text
❌ Bad:  "HR documents"
✅ Good: "Employee records including name, department, role,
          start date, salary band, and performance reviews
          for all full-time employees since 2020"
```

Planning Agent dùng descriptions để route queries → descriptions kém = routing sai = kết quả sai.

### 2. Sufficient Context > Relevance

Không chỉ tìm documents "liên quan" mà phải đảm bảo documents chứa **đủ thông tin** để trả lời. Đây là insight từ paper Sufficient Context (ICLR 2025).

### 3. Iterative > Single-pass

Multi-hop queries không thể giải quyết bằng 1 lần retrieval. Framework cho phép loop lại nhiều lần, mỗi lần refine query dựa trên kết quả trước.

### 4. Error Stratification

Phân tầng lỗi giúp biết chính xác cần fix ở đâu:

```text
Error Analysis
├── Context Insufficient → Cải thiện Retrieval / Corpus coverage
├── Context Sufficient nhưng sai → Cải thiện Model / Prompting
└── Routing sai corpus → Cải thiện Corpus descriptions
```

---

## Workflow áp dụng Agentic RAG

```text
Bước 1: Chuẩn bị Corpora
  → Tạo RAG corpora với descriptions chi tiết
  → Ingest documents vào từng corpus
  → Setup indexing (vector + keyword)

Bước 2: Cấu hình Agents
  → Orchestrator: define routing rules
  → Planning Agent: map corpus descriptions
  → Query Rewriter: configure decomposition strategy
  → Sufficient Context: set threshold + max loops

Bước 3: Test & Evaluate
  → Chạy Agent Evaluation Service
  → Multi-turn evaluation với simulated users
  → Phân tích failure clusters

Bước 4: Optimize (Quality Flywheel)
  → Analyze failures → Adjust prompts/tools → Re-test
  → Iterative improvement cycle
```

---

## Tóm tắt

| Khía cạnh | Chi tiết |
|-----------|---------|
| **Kiến trúc** | 5 specialized agents: Orchestrator → Planning → Query Rewriter → Search Fanout → Sufficient Context |
| **Innovation chính** | Sufficient Context Agent — quality gate kiểm tra context đủ chưa trước khi trả lời |
| **Cross-Corpus** | Tìm kiếm đồng thời trên nhiều nguồn dữ liệu, kết nối data islands |
| **Multi-Hop** | Kết quả từ hop trước làm input cho hop sau, tự động follow-up |
| **Accuracy** | +34% trên factuality datasets, 90.1% trên FramesQA (824 queries, 4 corpora) |
| **Latency** | < 3% overhead so với single-corpus |
| **APIs** | `AskContexts` (sync) + `AsyncRetrieveContexts` (async) |
| **Security** | VPC-SC + CMEK |
| **Status** | Public Preview trên Gemini Enterprise Agent Platform |

---

## Tài liệu tham khảo

- [Google Research Blog](https://research.google/blog/agentic-rag-in-the-gemini-enterprise-agent-platform/)
- [Sufficient Context Paper (ICLR 2025)](https://arxiv.org/abs/2411.06037)
- [Vertex AI RAG Engine Documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/rag-overview)
- [Gemini Enterprise Agent Platform](https://cloud.google.com/products/gemini/enterprise-agent-platform)
- [MarkTechPost Analysis](https://www.marktechpost.com/2026/06/05/google-introduces-agentic-rag-for-the-gemini-enterprise-agent-platform/)
