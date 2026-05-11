"""Application configuration."""

import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "http://127.0.0.1:1234/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "local-key")
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "local-model")

# SQLite database path
# Docker: /data/db/long_term_memory.db (mounted volume)
# Local:  ./memory_store/long_term_memory.db
_default_db_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory_store")
os.makedirs(_default_db_dir, exist_ok=True)

SQLITE_DB_PATH = os.getenv(
    "SQLITE_DB_PATH",
    os.path.join(_default_db_dir, "long_term_memory.db"),
)
