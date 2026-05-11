"""
═══════════════════════════════════════════════════════════════════════
GRAPH — LangGraph Conversation Flow với Memory Management
═══════════════════════════════════════════════════════════════════════

LangGraph StateGraph quản lý flow hội thoại. Tách làm 2 luồng:

1. Chat Graph (Real-time):
   __start__ → load_memory → chat → __end__

2. Extraction Graph (Background):
   __start__ → extract_memory → save_memory → __end__
"""

from typing import TypedDict

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from langgraph.graph import StateGraph, START, END

from config import OPENAI_API_BASE, OPENAI_API_KEY, OPENAI_MODEL_NAME
from memory import LongTermMemory

from rich.console import Console

console = Console()


# ═══════════════════════════════════════════════════════════════
# STATE
# ═══════════════════════════════════════════════════════════════

class ChatState(TypedDict):
    """State của LangGraph flow."""
    user_id: str
    messages: list[BaseMessage]        # short-term: conversation history
    user_message: str                  # input message hiện tại
    long_term_context: str             # context từ SQLite
    ai_response: str                   # response từ LLM
    extracted_memory: dict             # facts trích xuất được


# ═══════════════════════════════════════════════════════════════
# PROMPTS
# ═══════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """Bạn là trợ lý ảo AI thân thiện. Bạn đang trò chuyện trực tiếp với người dùng.

THÔNG TIN VỀ NGƯỜI DÙNG:
{long_term_context}

QUY TẮC BẮT BUỘC (BẠN PHẢI TUÂN THỦ CHÍNH XÁC ĐỊNH DẠNG XML SAU):

<thought>
(Quá trình phân tích, suy nghĩ nội bộ của bạn - có thể bằng tiếng Anh hoặc Việt)
</thought>
<response>
(Câu trả lời chính thức hiển thị cho người dùng: RẤT NGẮN GỌN 1-2 câu, bằng tiếng Việt, thân thiện, và xưng hô theo đúng thông tin bộ nhớ)
</response>

KHÔNG ĐƯỢC sinh ra bất kỳ văn bản nào nằm ngoài 2 thẻ này. KHÔNG tự biên diễn thêm lời của User.
"""

MEMORY_EXTRACTOR_PROMPT = """Phân tích đoạn hội thoại sau và trích xuất THÔNG TIN QUAN TRỌNG cần nhớ lâu dài.

--- HỘI THOẠI ---
User: {user_msg}
Assistant: {ai_msg}
--- KẾT THÚC ---

Hãy trả về CHÍNH XÁC theo format sau. Nếu không có thông tin mới, BẮT BUỘC ghi "none" trên dòng đó, KHÔNG được copy lại ví dụ.

PROFILE_UPDATE: key=value (nếu user tiết lộ tên, tuổi, nghề nghiệp. Nếu không có ghi: none)
PREFERENCE: key=value (nếu user tiết lộ sở thích. Nếu không có ghi: none)
KEY_FACT: một câu ngắn (nếu user tiết lộ sự kiện quan trọng. Nếu không có ghi: none)
ISSUE: vấn đề ngắn gọn (nếu user phàn nàn/gặp lỗi. Nếu không có ghi: none)

CHỈ trả về 4 dòng trên, KHÔNG giải thích. KHÔNG ghi thêm bất cứ chữ nào khác.
"""


# ═══════════════════════════════════════════════════════════════
# LLM FACTORY
# ═══════════════════════════════════════════════════════════════

def create_llm(temperature: float = 0.3, streaming: bool = False) -> ChatOpenAI:
    return ChatOpenAI(
        model=OPENAI_MODEL_NAME,
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_API_BASE,
        temperature=temperature,
        max_tokens=500, # Giới hạn token để tránh lặp vô hạn
        streaming=streaming,
    )


# ═══════════════════════════════════════════════════════════════
# GRAPH NODES
# ═══════════════════════════════════════════════════════════════

# Cache LongTermMemory instances per user_id
_ltm_cache: dict[str, LongTermMemory] = {}


def _get_ltm(user_id: str) -> LongTermMemory:
    """Lấy hoặc tạo LongTermMemory instance."""
    if user_id not in _ltm_cache:
        _ltm_cache[user_id] = LongTermMemory(user_id=user_id)
    return _ltm_cache[user_id]


def load_memory(state: ChatState) -> dict:
    """Node 1: Load long-term context từ SQLite."""
    ltm = _get_ltm(state["user_id"])
    ltm.increment_interaction()
    context = ltm.get_context()

    return {"long_term_context": context}


def chat(state: ChatState) -> dict:
    """Node 2: Gọi LLM với system prompt + conversation history.
    Streaming được xử lý tự động bởi LangGraph stream_mode="messages".
    """
    llm = create_llm(temperature=0.3, streaming=True)

    system_prompt = SYSTEM_PROMPT.format(
        long_term_context=state["long_term_context"]
    )

    llm_messages = [
        SystemMessage(content=system_prompt),
    ] + state["messages"] + [
        HumanMessage(content=state["user_message"]),
    ]

    response = llm.invoke(llm_messages, stop=["User:", "Human:", "tôi là Minh Khoa"])
    ai_response = response.content

    # Clean up hallucinated suffix just in case
    if "User:" in ai_response:
        ai_response = ai_response.split("User:")[0].strip()
        response.content = ai_response

    # Update messages with new exchange
    updated_messages = list(state["messages"])
    updated_messages.append(HumanMessage(content=state["user_message"]))
    updated_messages.append(response)

    return {
        "ai_response": ai_response,
        "messages": updated_messages,
    }


def extract_memory(state: ChatState) -> dict:
    """Node 3 (Background): LLM phân tích hội thoại → trích xuất facts."""
    extractor_llm = create_llm(temperature=0, streaming=False)

    prompt = MEMORY_EXTRACTOR_PROMPT.format(
        user_msg=state["user_message"],
        ai_msg=state["ai_response"],
    )

    response = extractor_llm.invoke([HumanMessage(content=prompt)])
    extraction = response.content.strip()

    # Parse extraction → structured dict
    extracted = {
        "profile_updates": [],
        "preferences": [],
        "key_facts": [],
        "issues": [],
    }

    for line in extraction.split("\n"):
        line = line.strip()
        if line.startswith("PROFILE_UPDATE:"):
            value = line.replace("PROFILE_UPDATE:", "").strip()
            if value.lower() != "none" and "=" in value:
                for pair in value.split(","):
                    pair = pair.strip()
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        extracted["profile_updates"].append(
                            {"key": k.strip(), "value": v.strip()}
                        )
        elif line.startswith("PREFERENCE:"):
            value = line.replace("PREFERENCE:", "").strip()
            if value.lower() != "none" and "=" in value:
                for pair in value.split(","):
                    pair = pair.strip()
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        extracted["preferences"].append(
                            {"key": k.strip(), "value": v.strip()}
                        )
        elif line.startswith("KEY_FACT:"):
            value = line.replace("KEY_FACT:", "").strip()
            if value.lower() != "none" and len(value) > 3:
                extracted["key_facts"].append(value)
        elif line.startswith("ISSUE:"):
            value = line.replace("ISSUE:", "").strip()
            if value.lower() != "none" and len(value) > 3:
                extracted["issues"].append(value)

    return {"extracted_memory": extracted}


def save_memory(state: ChatState) -> dict:
    """Node 4 (Background): Lưu extracted facts vào SQLite."""
    ltm = _get_ltm(state["user_id"])
    extracted = state.get("extracted_memory", {})
    updates = []

    for item in extracted.get("profile_updates", []):
        ltm.update_profile(item["key"], item["value"])
        updates.append(f"👤 Profile: {item['key']}={item['value']}")

    for item in extracted.get("preferences", []):
        ltm.add_preference(item["key"], item["value"])
        updates.append(f"⭐ Preference: {item['key']}={item['value']}")

    for fact in extracted.get("key_facts", []):
        ltm.add_key_fact(fact)
        updates.append(f"📌 Fact: {fact[:60]}")

    for issue in extracted.get("issues", []):
        ltm.add_past_issue(issue)
        updates.append(f"⚠️ Issue: {issue[:60]}")

    # Log results (in mờ vì chạy ngầm)
    if updates:
        for u in updates:
            console.print(f"  [dim]🔄 [Bg] {u}[/dim]")
    
    return {}


# ═══════════════════════════════════════════════════════════════
# BUILD GRAPHS
# ═══════════════════════════════════════════════════════════════

def build_chat_graph() -> StateGraph:
    """Graph 1: Real-time chat (load_memory → chat)."""
    graph = StateGraph(ChatState)
    graph.add_node("load_memory", load_memory)
    graph.add_node("chat", chat)
    
    graph.add_edge(START, "load_memory")
    graph.add_edge("load_memory", "chat")
    graph.add_edge("chat", END)
    return graph.compile()


def build_extraction_graph() -> StateGraph:
    """Graph 2: Background memory extraction (extract_memory → save_memory)."""
    graph = StateGraph(ChatState)
    graph.add_node("extract_memory", extract_memory)
    graph.add_node("save_memory", save_memory)
    
    graph.add_edge(START, "extract_memory")
    graph.add_edge("extract_memory", "save_memory")
    graph.add_edge("save_memory", END)
    return graph.compile()
