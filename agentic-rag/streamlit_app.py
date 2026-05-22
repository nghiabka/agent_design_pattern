"""Streamlit frontend for the Agentic RAG backend.

Run backend first:
    uv run uvicorn backend:app --host 0.0.0.0 --port 8000

Run frontend:
    uv run streamlit run streamlit_app.py
"""

from __future__ import annotations

import re
import uuid
import os
from pathlib import Path
from typing import Any

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

DEFAULT_BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


SAMPLE_QUESTIONS = [
    "Khách hàng cá nhân muốn chuyển 300 triệu qua mobile app trong cùng một ngày thì có được không?",
    "Khách báo có giao dịch thẻ lạ từ 2 ngày trước. Nhân viên phải xử lý theo các bước nào?",
    "Một startup mới mở tài khoản doanh nghiệp cần chuẩn bị giấy tờ gì và khi nào phải chuyển tuyến kiểm duyệt?",
]


def init_session() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "pending_question" not in st.session_state:
        st.session_state.pending_question = None
    if "session_id" not in st.session_state:
        st.session_state.session_id = f"streamlit-{uuid.uuid4().hex[:12]}"
    if "backend_url" not in st.session_state:
        st.session_state.backend_url = DEFAULT_BACKEND_URL.rstrip("/")


def backend_url() -> str:
    return st.session_state.backend_url.rstrip("/")


def extract_citations(answer: str) -> list[str]:
    citations = re.findall(r"\[(KB-\d{3})\]", answer)
    return sorted(set(citations))


def backend_get(path: str, timeout: int = 10) -> dict[str, Any] | None:
    try:
        response = requests.get(f"{backend_url()}{path}", timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def backend_chat(question: str) -> dict[str, Any]:
    response = requests.post(
        f"{backend_url()}/chat",
        json={
            "question": question,
            "session_id": st.session_state.session_id,
        },
        timeout=300,
    )
    response.raise_for_status()
    return response.json()


def render_trace(trace: dict[str, Any], max_rounds: int | None = None) -> None:
    max_rounds_text = f" · max rounds {max_rounds}" if max_rounds else ""
    st.caption(
        f"{trace.get('rounds', 0)} retrieval round(s) · "
        f"{trace.get('elapsed', 0):.2f}s"
        f"{max_rounds_text}"
    )

    search_history = trace.get("search_history") or []
    if search_history:
        st.markdown("**Search history**")
        for idx, query in enumerate(search_history, 1):
            st.code(f"{idx}. {query}", language="text")

    judge = trace.get("judge") or {}
    if judge:
        st.markdown("**Retrieval judge**")
        st.json(judge, expanded=False)

    evidence = trace.get("evidence") or []
    if evidence:
        st.markdown("**Retrieved evidence**")
        for item in evidence:
            label = (
                f"{item['source_id']} · {item['title']} "
                f"(score {item['score']})"
            )
            with st.expander(label):
                st.caption(item["source"])
                st.markdown(item["snippet"])
                st.divider()
                st.markdown(item["content"])


def render_message(message: dict[str, Any], max_rounds: int | None = None) -> None:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        if message["role"] == "assistant":
            citations = extract_citations(message["content"])
            if citations:
                st.caption("Citations: " + " ".join(f"`{source}`" for source in citations))

            trace = message.get("trace")
            if trace:
                with st.expander("Trace: retrieval, judge, sources"):
                    render_trace(trace, max_rounds=max_rounds)


def render_backend_status(health: dict[str, Any] | None) -> None:
    st.markdown("**Backend**")
    st.text_input("Backend URL", key="backend_url")

    if not health:
        st.error("Backend chưa sẵn sàng. Hãy chạy FastAPI backend trước.")
        st.code(
            "uv run uvicorn backend:app --host 0.0.0.0 --port 8000",
            language="bash",
        )
        return

    st.success("Backend connected")
    st.code(
        f"model={health['model']}\n"
        f"base_url={health['openai_api_base']}\n"
        f"max_rounds={health['max_retrieval_rounds']}\n"
        f"documents={health['documents']}",
        language="text",
    )

    langfuse = health.get("langfuse", {})
    st.markdown("**Langfuse**")
    if langfuse.get("configured"):
        st.success(f"Tracing enabled · {langfuse.get('host')}")
    elif langfuse.get("enabled"):
        st.warning("Tracing disabled: missing public/secret key")
    else:
        st.info("Tracing disabled by LANGFUSE_ENABLED=false")
    st.caption(f"session_id: `{st.session_state.session_id}`")


def render_sources() -> None:
    payload = backend_get("/sources")
    sources = payload.get("sources", []) if payload else []

    st.markdown("**Knowledge base**")
    if not sources:
        st.caption("Không lấy được sources từ backend.")
        return

    for doc in sources:
        with st.expander(f"{doc['id']} · {doc['title']}"):
            st.caption(doc["source"])
            st.markdown(doc["content"])


def render_sidebar(health: dict[str, Any] | None) -> None:
    with st.sidebar:
        st.title("Agentic RAG")
        st.caption("Streamlit frontend gọi FastAPI backend.")

        render_backend_status(health)

        st.divider()
        st.markdown("**Câu hỏi mẫu**")
        for question in SAMPLE_QUESTIONS:
            if st.button(question, use_container_width=True, disabled=not health):
                st.session_state.pending_question = question

        st.divider()
        render_sources()

        st.divider()
        if st.button("Xóa hội thoại", use_container_width=True):
            st.session_state.messages = []
            st.session_state.pending_question = None
            st.rerun()


def answer_question(question: str, max_rounds: int | None) -> None:
    st.session_state.messages.append({"role": "user", "content": question})

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        with st.spinner("Backend đang chạy Agentic RAG..."):
            try:
                payload = backend_chat(question)
                answer = payload["answer"]
                trace = payload.get("trace")
            except requests.RequestException as exc:
                answer = (
                    "Không gọi được backend Agentic RAG.\n\n"
                    f"Chi tiết lỗi: `{type(exc).__name__}: {exc}`\n\n"
                    "Kiểm tra backend FastAPI, `.env`, LLM endpoint và Langfuse nếu đang bật tracing."
                )
                trace = None

        placeholder.markdown(answer)
        citations = extract_citations(answer)
        if citations:
            st.caption("Citations: " + " ".join(f"`{source}`" for source in citations))
        if trace:
            with st.expander("Trace: retrieval, judge, sources"):
                render_trace(trace, max_rounds=max_rounds)

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "trace": trace,
    })


def main() -> None:
    st.set_page_config(
        page_title="Agentic RAG Chat",
        page_icon="🤖",
        layout="wide",
    )
    init_session()

    health = backend_get("/health")
    max_rounds = health.get("max_retrieval_rounds") if health else None
    render_sidebar(health)

    st.title("Agentic RAG Chat")
    st.caption("Frontend Streamlit → Backend FastAPI → LangGraph Agentic RAG → Langfuse tracing.")

    for message in st.session_state.messages:
        render_message(message, max_rounds=max_rounds)

    typed_question = st.chat_input("Nhập câu hỏi...", disabled=not health)
    pending_question = st.session_state.pending_question
    st.session_state.pending_question = None

    question = typed_question or pending_question
    if question:
        answer_question(question, max_rounds=max_rounds)


if __name__ == "__main__":
    main()
