"""Load markdown files from multiple corpora directories."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from gemini_rag.settings import CORPORA_DIR


# ── Corpus descriptions — used by Planning Agent to route queries ──────────

CORPUS_DESCRIPTIONS: dict[str, str] = {
    "hr": (
        "Hồ sơ nhân sự công ty TechVN: danh sách phòng ban, team lead, headcount, "
        "danh sách nhân viên chi tiết (tên, vai trò, server/dự án phụ trách), "
        "quy trình HR (nghỉ phép, onboarding, escalation)."
    ),
    "infra": (
        "Hạ tầng IT công ty TechVN: danh sách server (ID, hostname, CPU, RAM, storage, "
        "OS, vai trò, data center), incident log chi tiết (severity, downtime, người xử lý), "
        "network topology, VPN, firewall rules, backup & DR."
    ),
    "finance": (
        "Tài chính IT công ty TechVN: budget phân bổ theo quý (server, cloud, license, nhân sự), "
        "chi phí vận hành data center chi tiết (colocation, điện, bandwidth), "
        "quy trình mua sắm, danh sách vendor, mua sắm đang chờ phê duyệt."
    ),
    "projects": (
        "Dự án IT công ty TechVN: dự án đang hoạt động (Phoenix, Atlas, DataHub) — "
        "status, timeline, budget, team assignment, rủi ro; "
        "workload phân bổ theo nhân viên; milestones sắp tới và blockers."
    ),
}


@dataclass(frozen=True)
class Document:
    """A single document in the knowledge base."""
    id: str
    title: str
    source: str
    corpus_name: str
    content: str


@dataclass
class Corpus:
    """A named collection of documents with a description for routing."""
    name: str
    description: str
    documents: list[Document] = field(default_factory=list)


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Parse a tiny YAML-like frontmatter block."""
    if not text.startswith("---"):
        return {}, text.strip()

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text.strip()

    raw_meta = parts[1].strip()
    body = parts[2].strip()
    meta: dict[str, str] = {}

    for line in raw_meta.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip('"')

    return meta, body


def _first_heading(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line.removeprefix("# ").strip()
    return fallback


def load_corpus(corpus_dir: Path) -> Corpus:
    """Load a single corpus from a directory of markdown files."""
    corpus_name = corpus_dir.name
    description = CORPUS_DESCRIPTIONS.get(corpus_name, f"Corpus: {corpus_name}")
    documents: list[Document] = []

    for path in sorted(corpus_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(text)
        doc_id = meta.get("id", path.stem.upper())
        title = meta.get("title", _first_heading(body, path.stem.replace("_", " ").title()))

        documents.append(
            Document(
                id=doc_id,
                title=title,
                source=f"{corpus_name}/{path.name}",
                corpus_name=corpus_name,
                content=body,
            )
        )

    return Corpus(name=corpus_name, description=description, documents=documents)


def load_all_corpora(corpora_dir: Path = CORPORA_DIR) -> dict[str, Corpus]:
    """Load all corpora from subdirectories."""
    corpora: dict[str, Corpus] = {}

    for child in sorted(corpora_dir.iterdir()):
        if child.is_dir() and not child.name.startswith("."):
            corpus = load_corpus(child)
            if corpus.documents:
                corpora[corpus.name] = corpus

    if not corpora:
        raise RuntimeError(f"Không tìm thấy corpus nào trong {corpora_dir}")

    return corpora


# ── Module-level singletons ────────────────────────────────────────────────

ALL_CORPORA = load_all_corpora()
ALL_DOCUMENTS = [doc for corpus in ALL_CORPORA.values() for doc in corpus.documents]
