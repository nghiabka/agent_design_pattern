# 🤝 Multi-Agent Pattern — Agent as a Tool

## Design Pattern: Multi-Agent (Agent as a Tool)

Một agent (Artist) **gọi agent khác (ImageGen)** giống hệt như gọi một tool.
Agent cấp dưới được **wrap thành `@tool`** để agent cấp trên sử dụng.

## Architecture

```
  ┌──────────────┐     ┌──────────────────┐     ┌──────────────────┐
  │  User Idea   │────▶│  ARTIST AGENT    │────▶│  IMAGEGEN AGENT  │
  │              │     │  (Sáng tạo)      │     │  (Wrapped @tool) │
  └──────────────┘     │                  │     │                  │
                       │  1. Nghĩ ý tưởng │     │  Nhận prompt     │
                       │  2. Viết prompt  │     │  → gọi API tạo   │
                       │  3. Chọn style   │     │    ảnh (Pillow)  │
                       │  4. GỌI ImageGen │     │  → trả file path │
                       └──────────────────┘     └──────────────────┘
                              │                         │
                       calls as tool               calls tool
                              │                         │
                       imagegen_agent_tool        generate_image
```

## Core Concept: Agent as a Tool

```python
# ImageGen Agent được wrap thành @tool
@tool
def imagegen_agent_tool(prompt, style) -> str:
    agent = create_imagegen_agent()     # Tạo agent
    result = agent.invoke(...)          # Agent chạy (gọi tools riêng)
    return result                       # Trả kết quả

# Artist Agent sử dụng imagegen_agent_tool như 1 tool bình thường
artist = create_react_agent(llm, tools=[imagegen_agent_tool])
```

## Cấu trúc project

```
mutil-agent/
├── config.py        # Config + output dir
├── image_gen.py     # Tool generate_image (Pillow procedural art)
├── agents.py        # Artist Agent + ImageGen Agent (Agent as Tool)
├── run.py           # Demo runner
├── output/          # Thư mục chứa ảnh đã tạo
└── README.md
```

## Setup & Chạy

```bash
uv sync

uv run python run.py
uv run python run.py "Phong cảnh núi lửa phun trào dưới bầu trời đêm đầy sao"
```

## So sánh với các Pattern khác

| Pattern | Mục đích |
|---------|----------|
| Prompt Chaining | Phân rã tuần tự |
| Routing | Phân loại & delegate |
| Parallelization | Song song + chọn best |
| Reflection | Tự review & cải thiện |
| Tool Call | LLM gọi function |
| Planning | Lập kế hoạch dynamic |
| **Multi-Agent** | **Agent gọi Agent như Tool** |
