"""
Prompt templates for Deep Research with reflection.

Flow:
  generate_query -> web_research -> reflection -> web_research | finalize_answer
"""

from datetime import datetime


def get_current_date() -> str:
    return datetime.now().strftime("%B %d, %Y")


QUERY_WRITER_PROMPT = """Bạn là chuyên gia tạo truy vấn cho một hệ thống Deep Research tự động.

Nhiệm vụ: chuyển câu hỏi nghiên cứu thành các truy vấn web cụ thể, đa dạng và có khả năng tìm được nguồn đáng tin.

Ngày hiện tại: {current_date}
Câu hỏi nghiên cứu:
{research_topic}

Yêu cầu:
  1. Tạo tối đa {number_queries} truy vấn.
  2. Mỗi truy vấn tập trung vào một khía cạnh rõ ràng của câu hỏi.
  3. Ưu tiên truy vấn có khả năng lấy thông tin mới, kiểm chứng được.
  4. Không tạo nhiều truy vấn gần như giống nhau.

Trả về JSON đúng format:
{{
  "rationale": "Lý do chọn các truy vấn này",
  "queries": ["query 1", "query 2"]
}}
"""


WEB_RESEARCH_PROMPT = """Bạn là research analyst. Hãy đọc kết quả tìm kiếm dưới đây và tạo ghi chú nghiên cứu ngắn gọn, có dẫn nguồn.

Câu hỏi gốc:
{research_topic}

Truy vấn đã chạy:
{search_query}

Kết quả tìm kiếm:
{search_results}

Yêu cầu:
  1. Chỉ dùng thông tin có trong kết quả tìm kiếm.
  2. Tóm tắt các dữ kiện quan trọng để trả lời câu hỏi gốc.
  3. Khi nêu một dữ kiện, gắn citation dạng [S1], [S2] tương ứng với source id.
  4. Nếu kết quả yếu hoặc thiếu, nói rõ phần nào chưa đủ.
  5. Trả lời bằng tiếng Việt.
"""


REFLECTION_PROMPT = """Bạn là nút phản tư (reflection) trong một agent Deep Research.

Nhiệm vụ: đánh giá xem các ghi chú nghiên cứu hiện tại đã đủ để trả lời câu hỏi gốc chưa. Nếu chưa đủ, xác định knowledge gap và sinh truy vấn follow-up.

Ngày hiện tại: {current_date}
Câu hỏi gốc:
{research_topic}

Các ghi chú đã thu thập:
{research_notes}

Yêu cầu đánh giá:
  1. Câu trả lời cuối có đủ dữ kiện chính không?
  2. Có nguồn/citation cho các kết luận quan trọng không?
  3. Có điểm mâu thuẫn hoặc thiếu ngữ cảnh cần tìm thêm không?
  4. Nếu chưa đủ, tạo 1-3 truy vấn follow-up tự chứa ngữ cảnh.

Trả về JSON đúng format:
{{
  "is_sufficient": true,
  "knowledge_gap": "",
  "follow_up_queries": []
}}

Nếu chưa đủ:
{{
  "is_sufficient": false,
  "knowledge_gap": "Mô tả thông tin còn thiếu",
  "follow_up_queries": ["follow-up query 1"]
}}
"""


ANSWER_PROMPT = """Bạn là bước tổng hợp cuối của một quy trình Deep Research.

Ngày hiện tại: {current_date}
Câu hỏi gốc:
{research_topic}

Ghi chú nghiên cứu:
{research_notes}

Nguồn đã thu thập:
{sources}

Nhiệm vụ:
  1. Viết câu trả lời cuối bằng tiếng Việt, rõ ràng và có cấu trúc.
  2. Dựa trên ghi chú nghiên cứu, không bịa thêm thông tin ngoài nguồn.
  3. Gắn citation dạng [S1], [S2] cho các luận điểm chính.
  4. Nếu vẫn còn thiếu dữ liệu, nói rõ giới hạn thay vì đoán.
"""
