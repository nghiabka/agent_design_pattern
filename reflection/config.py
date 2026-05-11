"""Application configuration — loads environment variables."""

import os
from dotenv import load_dotenv

# Load .env file từ thư mục project root
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "http://127.0.0.1:1234/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "local-key")
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "local-model")

if not OPENAI_API_BASE:
    print("⚠️  OPENAI_API_BASE chưa được set!")
