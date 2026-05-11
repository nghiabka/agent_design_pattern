"""
═══════════════════════════════════════════════════════════════════════
SUB-AGENTS — Các agent chuyên biệt (Booker, Info, Unclear)
═══════════════════════════════════════════════════════════════════════

Mỗi sub-agent là một LangGraph ReAct agent với:
  • System prompt mô tả chuyên môn
  • Một hoặc nhiều tools riêng
  • LLM instance riêng

Sub-agents KHÔNG được gọi trực tiếp bởi user.
Chúng được Coordinator agent delegate tới thông qua routing logic.
"""

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from config import OPENAI_API_BASE, OPENAI_API_KEY, OPENAI_MODEL_NAME
from tools import booking_handler, info_handler,  unclear_handler


# ═══════════════════════════════════════════════════════════════
# LLM Factory
# ═══════════════════════════════════════════════════════════════

def create_llm() -> ChatOpenAI:
    """Tạo LLM instance kết nối tới local model."""
    return ChatOpenAI(
        model=OPENAI_MODEL_NAME,
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_API_BASE,
        temperature=0,
        extra_body={
            "chat_template_kwargs": {"enable_thinking": False},
        },
    )


# ═══════════════════════════════════════════════════════════════
# BOOKER AGENT — Chuyên xử lý đặt chỗ
# ═══════════════════════════════════════════════════════════════

BOOKER_SYSTEM_PROMPT = """Bạn là Booker — agent chuyên xử lý ĐẶT CHỖ cho khách hàng.

Nhiệm vụ của bạn:
  • Đặt vé máy bay (flight booking)
  • Đặt phòng khách sạn (hotel booking)

Khi nhận yêu cầu đặt chỗ:
  1. Xác định loại đặt chỗ (flight / hotel)
  2. Trích xuất thông tin: điểm đến, ngày, số hành khách/phòng
  3. Gọi tool booking_handler để thực hiện đặt chỗ
  4. Trả kết quả xác nhận cho khách hàng

Nếu thiếu thông tin, hãy sử dụng giá trị mặc định hợp lý:
  • Ngày: hôm nay hoặc ngày mai
  • Số hành khách: 1
  • Loại: dựa vào ngữ cảnh (bay = flight, ở = hotel)

Luôn trả lời bằng tiếng Việt, thân thiện và chuyên nghiệp.
"""


def create_booker_agent():
    """Tạo Booker agent với booking_handler tool."""
    llm = create_llm()
    return create_react_agent(
        llm,
        tools=[booking_handler],
        prompt=BOOKER_SYSTEM_PROMPT,
    )


# ═══════════════════════════════════════════════════════════════
# INFO AGENT — Chuyên tra cứu thông tin
# ═══════════════════════════════════════════════════════════════

INFO_SYSTEM_PROMPT = """Bạn là Info — agent chuyên TRA CỨU THÔNG TIN cho khách hàng.

Nhiệm vụ của bạn:
  • Tra cứu thời tiết (weather)
  • Thông tin visa (visa)
  • Điểm tham quan (attractions)
  • Tỷ giá ngoại tệ (currency)
  • Thông tin chung về du lịch

Khi nhận yêu cầu thông tin:
  1. Xác định loại thông tin cần tra cứu
  2. Xác định địa điểm liên quan
  3. Gọi tool info_handler để truy xuất
  4. Trả kết quả cho khách hàng

Luôn trả lời bằng tiếng Việt, thân thiện và hữu ích.
"""


def create_info_agent():
    """Tạo Info agent với info_handler tool."""
    llm = create_llm()
    return create_react_agent(
        llm,
        tools=[info_handler],
        prompt=INFO_SYSTEM_PROMPT,
    )


# ═══════════════════════════════════════════════════════════════
# UNCLEAR AGENT — Fallback cho yêu cầu không rõ ràng
# ═══════════════════════════════════════════════════════════════

UNCLEAR_SYSTEM_PROMPT = """Bạn là Unclear Handler — agent xử lý các yêu cầu KHÔNG RÕ RÀNG.

Khi một yêu cầu không thuộc về đặt chỗ (booking) hay tra cứu thông tin (info),
bạn sẽ được delegate tới.

Nhiệm vụ của bạn:
  1. Gọi unclear_handler tool với tin nhắn gốc
  2. Giải thích cho khách hàng các dịch vụ có sẵn
  3. Hướng dẫn họ mô tả rõ hơn yêu cầu

Luôn trả lời bằng tiếng Việt, kiên nhẫn và thân thiện.
"""


def create_unclear_agent():
    """Tạo Unclear agent với unclear_handler tool."""
    llm = create_llm()
    return create_react_agent(
        llm,
        tools=[unclear_handler],
        prompt=UNCLEAR_SYSTEM_PROMPT,
    )
