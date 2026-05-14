# ═══════════════════════════════════════════════════════════════
# Dockerfile — Memory Management Chatbot (Harden Environment)
# ═══════════════════════════════════════════════════════════════

FROM python:3.11-slim

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 1. Cấu hình môi trường ảo ở thư mục RIÊNG biệt (/opt/venv)
# Việc này giúp tránh bị ghi đè khi mount volume .:/app
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# 2. Copy file cấu hình trước
COPY pyproject.toml uv.lock ./

# 3. Cài đặt dependencies vào /opt/venv
RUN uv sync --no-dev --no-install-project

# 4. Copy mã nguồn (sau khi đã cài xong deps để tận dụng cache)
COPY . .

# 5. Cài đặt chính dự án này
RUN uv sync --no-dev

# Tạo thư mục DB
RUN mkdir -p /data/db

# Chạy ứng dụng
CMD ["python", "run.py"]
