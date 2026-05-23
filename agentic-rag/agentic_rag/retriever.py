"""Small local retriever for the Agentic RAG demo.

The goal here is educational: keep retrieval deterministic and inspectable
without requiring an external vector database.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass

from agentic_rag.documents import DOCUMENTS, Document


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how",
    "in", "is", "it", "of", "on", "or", "that", "the", "to", "what", "when",
    "where", "who", "why", "with",
    "anh", "chị", "cho", "có", "của", "cần", "các", "cái", "gì", "hãy",
    "khách", "không", "là", "mình", "một", "nào", "nếu", "phải", "thì",
    "trong", "và", "về", "với", "được", "để", "ở",
    "chi", "co", "cua", "can", "cac", "cai", "gi", "hay", "khach",
    "khong", "la", "minh", "mot", "nao", "neu", "phai", "thi", "va",
    "ve", "voi", "duoc", "de",
}


@dataclass(frozen=True)
class SearchResult:
    document: Document
    score: float
    matched_terms: list[str]
    snippet: str


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text.lower())
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[\w]+", normalize_text(text), flags=re.UNICODE)
    return [token for token in tokens if token not in STOPWORDS and len(token) > 1]


def make_snippet(content: str, query_terms: set[str], max_chars: int = 420) -> str:
    """Pick the most relevant sentences for a short citation snippet."""
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", content)
        if sentence.strip()
    ]

    if not sentences:
        return content[:max_chars]

    ranked = sorted(
        sentences,
        key=lambda sentence: sum(1 for term in query_terms if term in normalize_text(sentence)),
        reverse=True,
    )

    snippet = " ".join(ranked[:2])
    if len(snippet) > max_chars:
        return snippet[: max_chars - 3].rstrip() + "..."
    return snippet


class KnowledgeBaseRetriever:
    def __init__(self, documents: list[Document]):
        self.documents = documents
        self._doc_tokens = {doc.id: tokenize(f"{doc.title}\n{doc.content}") for doc in documents}
        self._term_freq = {doc_id: Counter(tokens) for doc_id, tokens in self._doc_tokens.items()}
        self._doc_freq = self._build_doc_freq()
        self._avg_doc_len = sum(len(tokens) for tokens in self._doc_tokens.values()) / len(documents)

    def _build_doc_freq(self) -> Counter[str]:
        doc_freq: Counter[str] = Counter()
        for tokens in self._doc_tokens.values():
            doc_freq.update(set(tokens))
        return doc_freq

    def _idf(self, term: str) -> float:
        total_docs = len(self.documents)
        containing_docs = self._doc_freq.get(term, 0)
        return math.log(1 + (total_docs - containing_docs + 0.5) / (containing_docs + 0.5))

    def _bm25_score(self, doc: Document, query_terms: list[str]) -> float:
        tokens = self._doc_tokens[doc.id]
        frequencies = self._term_freq[doc.id]
        doc_len = max(len(tokens), 1)
        k1 = 1.5
        b = 0.75

        score = 0.0
        for term in query_terms:
            tf = frequencies.get(term, 0)
            if tf == 0:
                continue
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * doc_len / self._avg_doc_len)
            score += self._idf(term) * numerator / denominator

        return score

    def search(self, query: str, top_k: int = 4) -> list[SearchResult]:
        query_terms = tokenize(query)
        if not query_terms:
            return []

        query_term_set = set(query_terms)
        results: list[SearchResult] = []

        for doc in self.documents:
            score = self._bm25_score(doc, query_terms)
            haystack = normalize_text(f"{doc.title}\n{doc.content}")
            haystack_tokens = set(self._doc_tokens[doc.id])

            # Small boost for literal phrases and important numeric values.
            if normalize_text(query) in haystack:
                score += 2.0
            for term in query_term_set:
                if term.isdigit() and term in haystack_tokens:
                    score += 0.8

            if score <= 0:
                continue

            matched_terms = sorted(term for term in query_term_set if term in haystack_tokens)
            results.append(
                SearchResult(
                    document=doc,
                    score=round(score, 3),
                    matched_terms=matched_terms,
                    snippet=make_snippet(doc.content, query_term_set),
                )
            )

        return sorted(results, key=lambda item: item.score, reverse=True)[:top_k]

    def read(self, source_id: str) -> Document | None:
        normalized = source_id.strip().lower()
        for doc in self.documents:
            if doc.id.lower() == normalized or doc.source.lower() == normalized:
                return doc
        return None


knowledge_base = KnowledgeBaseRetriever(DOCUMENTS)


def format_search_results(results: list[SearchResult]) -> str:
    if not results:
        return "Không tìm thấy tài liệu liên quan trong knowledge base."

    blocks: list[str] = []
    for idx, result in enumerate(results, 1):
        doc = result.document
        terms = ", ".join(result.matched_terms) if result.matched_terms else "không rõ"
        blocks.append(
            f"{idx}. [{doc.id}] {doc.title}\n"
            f"   Source: {doc.source}\n"
            f"   Score: {result.score} | Matched: {terms}\n"
            f"   Snippet: {result.snippet}"
        )
    return "\n\n".join(blocks)
