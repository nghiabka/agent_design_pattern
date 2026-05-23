"""Load markdown files from the local knowledge base."""

from dataclasses import dataclass
from pathlib import Path

from agentic_rag.settings import KB_DIR


@dataclass(frozen=True)
class Document:
    id: str
    title: str
    source: str
    content: str


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Parse a tiny YAML-like frontmatter block without adding dependencies."""
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


def load_documents(kb_dir: Path = KB_DIR) -> list[Document]:
    """Load all markdown documents in the knowledge base directory."""
    documents: list[Document] = []

    for path in sorted(kb_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(text)
        doc_id = meta.get("id", path.stem.upper())
        title = meta.get("title", _first_heading(body, path.stem.replace("_", " ").title()))

        documents.append(
            Document(
                id=doc_id,
                title=title,
                source=path.name,
                content=body,
            )
        )

    if not documents:
        raise RuntimeError(f"Không tìm thấy tài liệu markdown trong {kb_dir}")

    return documents


DOCUMENTS = load_documents()
