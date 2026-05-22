"""Application configuration - loads environment variables."""

import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "http://127.0.0.1:1234/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "local-key")
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "local-model")
MAX_RETRIEVAL_ROUNDS = int(os.getenv("MAX_RETRIEVAL_ROUNDS", "3"))

BACKEND_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))
BACKEND_URL = os.getenv("BACKEND_URL", f"http://localhost:{BACKEND_PORT}")

# Langfuse tracing. Leave keys empty to disable tracing.
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
LANGFUSE_ENABLED = os.getenv("LANGFUSE_ENABLED", "true").lower() in {"1", "true", "yes", "on"}

if not OPENAI_API_BASE:
    print("⚠️  OPENAI_API_BASE chưa được set!")
