"""Application configuration — loads environment variables."""

import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "http://127.0.0.1:1234/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "local-key")
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "local-model")

# Thư mục lưu ảnh output
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)
