import json
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from chatbot import MemoryAwareChatbot
from run import DEFAULT_USER_ID

app = FastAPI(title="Memory Management AI Chat")

# Khởi tạo chatbot toàn cục cho demo
bot = MemoryAwareChatbot(user_id=DEFAULT_USER_ID, max_turns=10)

# Mount thư mục static chứa giao diện
app.mount("/static", StaticFiles(directory="static"), name="static")

class ChatRequest(BaseModel):
    message: str

@app.get("/", response_class=HTMLResponse)
async def get_root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    """Sử dụng Server-Sent Events (SSE) để stream từng token về giao diện."""
    async def event_generator():
        # Lặp qua từng chunk (token) sinh ra từ LangGraph
        for chunk in bot.stream_chat_generator(req.message):
            # Format dữ liệu chuẩn SSE
            yield f"data: {json.dumps({'content': chunk})}\n\n"
            # Thêm nhịp thở nhỏ để asyncio có thể yield context
            await asyncio.sleep(0.005)
            
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/memory_status")
async def get_memory_status():
    """Lấy toàn bộ trạng thái bộ nhớ để hiển thị bên UI."""
    profile, prefs, fact_count, issue_count, summary_count, stats = bot.ltm.get_raw_data()
    
    return {
        "short_term": {
            "message_count": len(bot.messages),
            "turn_count": bot.turn_count,
            "max_turns": bot.max_turns
        },
        "long_term": {
            "profile": profile,
            "preferences": prefs,
            "stats": {
                "facts": fact_count,
                "issues": issue_count,
                "summaries": summary_count,
                "interactions": stats.get("interaction_count", 0),
                "first_seen": stats.get("first_seen", "—"),
                "last_seen": stats.get("last_seen", "—"),
            }
        }
    }
