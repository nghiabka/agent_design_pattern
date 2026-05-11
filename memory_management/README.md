# 🧠 Memory Management — LangGraph + SQLite + Docker

## Design Pattern: Memory Management

Chatbot sử dụng **2 tầng bộ nhớ** để duy trì hội thoại mạch lạc
và cá nhân hóa trải nghiệm qua nhiều session.

**Stack**: LangChain + LangGraph + SQLite + Docker Compose

## Architecture

```
  ┌─────────────────── Docker Compose ───────────────────┐
  │                                                      │
  │  ┌─────────────── App Container ──────────────────┐  │
  │  │                                                │  │
  │  │  ┌─────────── LangGraph Flow ───────────────┐  │  │
  │  │  │                                          │  │  │
  │  │  │  load_memory → chat → extract → save     │  │  │
  │  │  │      │           │        │        │     │  │  │
  │  │  │      ▼           ▼        ▼        ▼     │  │  │
  │  │  │   SQLite       LLM      LLM     SQLite   │  │  │
  │  │  │   (read)      (chat)  (extract)  (write)  │  │  │
  │  │  └──────────────────────────────────────────┘  │  │
  │  └────────────────────────────────────────────────┘  │
  │                                                      │
  │  ┌──────────── SQLite Volume ─────────────────────┐  │
  │  │  /data/db/long_term_memory.db                  │  │
  │  │  (persistent qua container restart)            │  │
  │  └────────────────────────────────────────────────┘  │
  └──────────────────────────────────────────────────────┘
```

## LangGraph Flow

```
__start__ → load_memory → chat → extract_memory → save_memory → __end__
```

| Node | Mô tả |
|---|---|
| **load_memory** | Load long-term context từ SQLite |
| **chat** | Gọi LLM với system prompt + messages |
| **extract_memory** | LLM phân tích hội thoại → trích xuất facts |
| **save_memory** | Lưu facts vào SQLite |

## Hai loại Memory

| | Short-term | Long-term |
|---|---|---|
| **Lưu trữ** | LangGraph State (RAM) | SQLite database |
| **Lifecycle** | Mất khi kết thúc session | Persist trong Docker volume |
| **Nội dung** | Conversation messages | Profile, preferences, facts, issues |
| **Cơ chế** | Sliding window (N turns) | Memory Extractor (LangGraph node) |
| **Mục đích** | Duy trì mạch hội thoại | Cá nhân hóa qua sessions |

## Cấu trúc project

```
memory_management/
├── config.py            # Config + SQLITE_DB_PATH
├── memory.py            # ShortTermMemory + LongTermMemory (SQLite)
├── graph.py             # LangGraph StateGraph (4 nodes)
├── chatbot.py           # MemoryAwareChatbot (uses LangGraph)
├── run.py               # Demo + interactive chat
├── Dockerfile           # Python 3.11 + uv
├── docker-compose.yml   # App + SQLite volume
├── .env                 # Environment variables
└── README.md
```

## Setup & Chạy

### Docker Compose (khuyến nghị)

```bash
# Build & chạy demo
docker compose up --build

# Chat tương tác
docker compose run -it app python run.py --chat

# Xem memory status
docker compose run app python run.py --status

# Xóa memory
docker compose run app python run.py --reset

# Stop
docker compose down

# Stop + xóa data
docker compose down -v
```

### Local (không Docker)

```bash
uv sync

uv run python run.py              # Demo 2 sessions
uv run python run.py --chat       # Chat tương tác
uv run python run.py --status     # Xem memory
uv run python run.py --reset      # Xóa memory
```

## Environment Variables

| Variable | Default | Mô tả |
|---|---|---|
| `OPENAI_API_BASE` | `http://127.0.0.1:1234/v1` | LLM API endpoint |
| `OPENAI_API_KEY` | `local-key` | API key |
| `OPENAI_MODEL_NAME` | `local-model` | Model name |
| `SQLITE_DB_PATH` | `./memory_store/long_term_memory.db` | SQLite database path |

> **Note**: Trong Docker, `OPENAI_API_BASE` sử dụng `host.docker.internal`
> để truy cập local LLM trên host machine.
