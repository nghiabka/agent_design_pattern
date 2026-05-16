"""Application configuration for the Deep Research demo."""

import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "http://127.0.0.1:1234/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "local-key")
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "local-model")

QUERY_MODEL_NAME = os.getenv("OPENAI_QUERY_MODEL_NAME", OPENAI_MODEL_NAME)
REFLECTION_MODEL_NAME = os.getenv("OPENAI_REFLECTION_MODEL_NAME", OPENAI_MODEL_NAME)
ANSWER_MODEL_NAME = os.getenv("OPENAI_ANSWER_MODEL_NAME", OPENAI_MODEL_NAME)
USE_STRUCTURED_OUTPUT = os.getenv("USE_STRUCTURED_OUTPUT", "false").lower() in {
    "1",
    "true",
    "yes",
}


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


INITIAL_SEARCH_QUERY_COUNT = _int_env("INITIAL_SEARCH_QUERY_COUNT", 3)
MAX_RESEARCH_LOOPS = _int_env("MAX_RESEARCH_LOOPS", 2)
SEARCH_MAX_RESULTS = _int_env("SEARCH_MAX_RESULTS", 3)

# Guardrails for local models with smaller context windows.
OPENAI_TIMEOUT_SECONDS = _int_env("OPENAI_TIMEOUT_SECONDS", 45)
OPENAI_MAX_COMPLETION_TOKENS = _int_env("OPENAI_MAX_COMPLETION_TOKENS", 1200)
SEARCH_SNIPPET_MAX_CHARS = _int_env("SEARCH_SNIPPET_MAX_CHARS", 500)
SEARCH_RESULTS_MAX_CHARS = _int_env("SEARCH_RESULTS_MAX_CHARS", 3500)
RESEARCH_NOTE_MAX_CHARS = _int_env("RESEARCH_NOTE_MAX_CHARS", 1800)
REFLECTION_NOTES_MAX_CHARS = _int_env("REFLECTION_NOTES_MAX_CHARS", 6000)
FINAL_NOTES_MAX_CHARS = _int_env("FINAL_NOTES_MAX_CHARS", 8000)
SOURCES_MAX_CHARS = _int_env("SOURCES_MAX_CHARS", 4000)
