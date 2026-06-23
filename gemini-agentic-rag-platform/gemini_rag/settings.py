"""Application configuration — loads environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"
CORPORA_DIR = PROJECT_ROOT / "corpora"

load_dotenv(ENV_FILE)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "http://127.0.0.1:1234/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or "local-key"
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "local-model")
OPENAI_TIMEOUT_SECONDS = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "120"))
OPENAI_MAX_ATTEMPTS = max(1, int(os.getenv("OPENAI_MAX_ATTEMPTS", "3")))
OPENAI_ENABLE_THINKING = _env_bool("OPENAI_ENABLE_THINKING", False)
MAX_HOPS = int(os.getenv("MAX_HOPS", "3"))

LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_BASE_URL = (
    os.getenv("LANGFUSE_BASE_URL")
    or os.getenv("LANGFUSE_HOST")
    or "http://localhost:3000"
)
LANGFUSE_HOST = LANGFUSE_BASE_URL
LANGFUSE_ENABLED = _env_bool("LANGFUSE_ENABLED", False)
LANGFUSE_ENVIRONMENT = os.getenv("LANGFUSE_ENVIRONMENT", "development")
LANGFUSE_FLUSH_ON_RUN = _env_bool("LANGFUSE_FLUSH_ON_RUN", True)

if not OPENAI_API_BASE:
    print("⚠️  OPENAI_API_BASE chưa được set!")
