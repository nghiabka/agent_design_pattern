"""BM25 retriever supporting per-corpus and cross-corpus search."""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass

from gemini_rag.documents import ALL_CORPORA, Corpus, Document


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how",
    "in", "is", "it", "of", "on", "or", "that", "the", "to", "what", "when",
    "where", "who", "why", "with",
    "anh", "chị", "cho", "có", "của", "cần", "các", "cái", "gì", "hãy",
    "khách", "không", "là", "mình", "một", "nào", "nếu", "phải", "thì",
    "trong", "và", "về", "với", "được", "để", "ở", "bao", "nhiêu",
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


class CorpusRetriever:
    """BM25 retriever for a single corpus."""

    def __init__(self, corpus: Corpus):
        self.corpus = corpus
        self.documents = corpus.documents
        self._doc_tokens = {
            doc.id: tokenize(f"{doc.title}\n{doc.content}") for doc in self.documents
        }
        self._term_freq = {
            doc_id: Counter(tokens) for doc_id, tokens in self._doc_tokens.items()
        }
        self._doc_freq = self._build_doc_freq()
        self._avg_doc_len = (
            sum(len(tokens) for tokens in self._doc_tokens.values()) / max(len(self.documents), 1)
        )

    def _build_doc_freq(self) -> Counter:
        doc_freq: Counter = Counter()
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

            # Boost for literal phrases and important IDs/numbers.
            if normalize_text(query) in haystack:
                score += 2.0
            for term in query_term_set:
                if (term.isdigit() or term.startswith("srv") or term.startswith("proj")) and term in haystack_tokens:
                    score += 1.0

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


class CrossCorpusRetriever:
    """Search across multiple corpora."""

    def __init__(self, corpora: dict[str, Corpus]):
        self.retrievers: dict[str, CorpusRetriever] = {
            name: CorpusRetriever(corpus) for name, corpus in corpora.items()
        }

    def search(
        self,
        query: str,
        corpus_names: list[str] | None = None,
        top_k: int = 4,
    ) -> list[SearchResult]:
        """Search across specified corpora (or all if None)."""
        target_names = corpus_names or list(self.retrievers.keys())
        all_results: list[SearchResult] = []

        for name in target_names:
            retriever = self.retrievers.get(name)
            if retriever:
                all_results.extend(retriever.search(query, top_k=top_k))

        # Sort by score globally and deduplicate by document ID.
        all_results.sort(key=lambda r: r.score, reverse=True)
        seen: set[str] = set()
        deduped: list[SearchResult] = []
        for result in all_results:
            if result.document.id not in seen:
                seen.add(result.document.id)
                deduped.append(result)
            if len(deduped) >= top_k:
                break

        return deduped

    def search_corpus(self, query: str, corpus_name: str, top_k: int = 4) -> list[SearchResult]:
        """Search a single corpus by name."""
        return self.search(query, corpus_names=[corpus_name], top_k=top_k)


# ── Module-level singleton ─────────────────────────────────────────────────

cross_corpus_retriever = CrossCorpusRetriever(ALL_CORPORA)
