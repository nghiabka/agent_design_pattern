"""Tools exposed to the Agentic RAG workflow."""

from langchain_core.tools import tool

from agentic_rag.retriever import format_search_results, knowledge_base


@tool
def search_knowledge_base(query: str, top_k: int = 4) -> str:
    """Tìm kiếm chính sách nội bộ trong knowledge base.

    Args:
        query: Câu truy vấn ngắn, tập trung vào thông tin cần tìm.
        top_k: Số tài liệu liên quan nhất cần trả về.

    Returns:
        Danh sách tài liệu liên quan kèm source id, score và snippet.
    """
    results = knowledge_base.search(query, top_k=top_k)
    return format_search_results(results)


@tool
def read_source(source_id: str) -> str:
    """Đọc toàn bộ một tài liệu từ source id.

    Args:
        source_id: Mã tài liệu, ví dụ KB-003.

    Returns:
        Nội dung đầy đủ của tài liệu.
    """
    doc = knowledge_base.read(source_id)
    if not doc:
        return f"Không tìm thấy source_id={source_id}"

    return f"[{doc.id}] {doc.title}\nSource: {doc.source}\n\n{doc.content}"


ALL_TOOLS = [search_knowledge_base, read_source]
