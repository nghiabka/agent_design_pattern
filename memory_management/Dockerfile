# ═══════════════════════════════════════════════════════════════
# Dockerfile — Memory Management Chatbot (LangGraph + SQLite)
# ═══════════════════════════════════════════════════════════════

FROM python:3.11-slim

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files first (better Docker cache)
COPY pyproject.toml ./

# Install dependencies
RUN uv sync --no-dev

# Activate venv by adding it to PATH
# This ensures `python` can find all installed packages
# even when CMD is overridden (e.g. docker compose run)
ENV PATH="/app/.venv/bin:$PATH"

# Copy source code
COPY . .

# Create db directory (will be mounted as volume)
RUN mkdir -p /data/db

# Default: run demo mode
CMD ["python", "run.py"]
